"""Hermes Agent integration (pre_llm_call shell hooks in ~/.hermes/config.yaml)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

HERMES_HOOK_MARKER = "triggerctl-pre-llm"
DEFAULT_TIMEOUT = 30
DEFAULT_TZ = "8"


def config_path() -> Path:
    """Return existing Hermes config or the default path to create."""
    base = Path.home() / ".hermes"
    for name in ("config.yaml", "cli-config.yaml"):
        p = base / name
        if p.exists():
            return p
    return base / "config.yaml"


def agent_hooks_dir() -> Path:
    return Path.home() / ".hermes" / "agent-hooks"


def skill_path() -> Path:
    return Path.home() / ".hermes" / "skills" / "triggerctl" / "SKILL.md"


def default_skill_source() -> Path:
    return Path(__file__).resolve().parent.parent / "skill" / "SKILL.md"


def load_config(path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
    path = path or config_path()
    if not path.exists():
        return path, {}
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if text.strip() else {}
    return path, data if isinstance(data, dict) else {}


def _pre_llm_entries(data: Dict[str, Any]) -> List[dict]:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []
    pre = hooks.get("pre_llm_call")
    if not isinstance(pre, list):
        return []
    return [e for e in pre if isinstance(e, dict)]


def hook_installed(data: Optional[Dict[str, Any]] = None) -> bool:
    if data is None:
        _, data = load_config()
    for e in _pre_llm_entries(data):
        cmd = str(e.get("command", ""))
        if HERMES_HOOK_MARKER in cmd or "triggerctl hermes-hook" in cmd:
            return True
    return False


def skill_installed() -> bool:
    return skill_path().is_file()


def install_hook_wrapper(triggerctl_cmd: str) -> Path:
    """Write a wrapper script so Hermes hooks get TZ + HERMES_ACCEPT_HOOKS defaults."""
    d = agent_hooks_dir()
    d.mkdir(parents=True, exist_ok=True)
    script = d / "triggerctl-pre-llm.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'export TRIGGERCTL_TZ_OFFSET="${{TRIGGERCTL_TZ_OFFSET:-{DEFAULT_TZ}}}"\n'
        'export HERMES_ACCEPT_HOOKS="${HERMES_ACCEPT_HOOKS:-1}"\n'
        f'exec {triggerctl_cmd} hermes-hook\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def install_skill(source: Optional[Path] = None) -> Path:
    src = source or default_skill_source()
    if not src.is_file():
        raise FileNotFoundError(f"skill source not found: {src}")
    dest = skill_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def install_pre_llm_hook(triggerctl_cmd: Optional[str] = None) -> Path:
    """Register triggerctl on Hermes pre_llm_call. Returns config path."""
    triggerctl_cmd = triggerctl_cmd or shutil.which("triggerctl") or "triggerctl"
    wrapper = install_hook_wrapper(triggerctl_cmd)
    command = str(wrapper)

    path, data = load_config()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        bak = path.with_suffix(path.suffix + ".triggerctl.bak")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    if not hook_installed(data):
        hooks = data.setdefault("hooks", {})
        pre = hooks.setdefault("pre_llm_call", [])
        if not isinstance(pre, list):
            pre = []
            hooks["pre_llm_call"] = pre
        pre.append({"command": command, "timeout": DEFAULT_TIMEOUT})

    if not data.get("hooks_auto_accept"):
        data["hooks_auto_accept"] = True

    path.write_text(
        yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def install_full(
    triggerctl_cmd: Optional[str] = None,
    skill_source: Optional[Path] = None,
) -> Dict[str, Path]:
    """Full Hermes setup: pre_llm_call hook, triggerctl skill, hooks_auto_accept."""
    triggerctl_cmd = triggerctl_cmd or shutil.which("triggerctl") or "triggerctl"
    cfg = install_pre_llm_hook(triggerctl_cmd)
    skill = install_skill(skill_source)
    return {"config": cfg, "skill": skill, "wrapper": agent_hooks_dir() / "triggerctl-pre-llm.sh"}
