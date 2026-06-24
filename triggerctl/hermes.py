"""Hermes Agent integration (pre_llm_call shell hooks in ~/.hermes/config.yaml)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

HERMES_HOOK_MARKER = "triggerctl hermes-hook"
DEFAULT_TIMEOUT = 30


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
    return any(HERMES_HOOK_MARKER in str(e.get("command", "")) for e in _pre_llm_entries(data))


def install_pre_llm_hook(triggerctl_cmd: Optional[str] = None) -> Path:
    """Register triggerctl on Hermes pre_llm_call. Returns config path."""
    triggerctl_cmd = triggerctl_cmd or shutil.which("triggerctl") or "triggerctl"
    command = f"{triggerctl_cmd} hermes-hook"

    path, data = load_config()
    path.parent.mkdir(parents=True, exist_ok=True)
    agent_hooks_dir().mkdir(parents=True, exist_ok=True)

    if path.exists():
        bak = path.with_suffix(path.suffix + ".triggerctl.bak")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    if hook_installed(data):
        return path

    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("pre_llm_call", [])
    if not isinstance(pre, list):
        pre = []
        hooks["pre_llm_call"] = pre
    pre.append({"command": command, "timeout": DEFAULT_TIMEOUT})

    path.write_text(
        yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path
