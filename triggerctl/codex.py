"""OpenAI Codex CLI integration (UserPromptSubmit hook in ~/.codex/hooks.json)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CODEX_HOOK_MARKER = "triggerctl-user-prompt"
DEFAULT_TIMEOUT = 30
DEFAULT_TZ = "8"


def codex_dir() -> Path:
    return Path.home() / ".codex"


def hooks_json_path() -> Path:
    return codex_dir() / "hooks.json"


def hooks_dir() -> Path:
    return codex_dir() / "hooks"


def skill_path() -> Path:
    return Path.home() / ".agents" / "skills" / "triggerctl" / "SKILL.md"


def default_skill_source() -> Path:
    return Path(__file__).resolve().parent.parent / "skill" / "SKILL.md"


def load_hooks(path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
    path = path or hooks_json_path()
    if not path.is_file():
        return path, {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return path, {}
    return path, data if isinstance(data, dict) else {}


def _user_prompt_submit_groups(data: Dict[str, Any]) -> List[dict]:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []
    ups = hooks.get("UserPromptSubmit")
    if not isinstance(ups, list):
        return []
    return [g for g in ups if isinstance(g, dict)]


def hook_installed(data: Optional[Dict[str, Any]] = None) -> bool:
    if data is None:
        _, data = load_hooks()
    for group in _user_prompt_submit_groups(data):
        for hook in group.get("hooks") or []:
            if not isinstance(hook, dict):
                continue
            cmd = str(hook.get("command", ""))
            if CODEX_HOOK_MARKER in cmd or "triggerctl codex-hook" in cmd:
                return True
    return False


def skill_installed() -> bool:
    return skill_path().is_file()


def install_hook_wrapper(triggerctl_cmd: str) -> Path:
    d = hooks_dir()
    d.mkdir(parents=True, exist_ok=True)
    script = d / "triggerctl-user-prompt-submit.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'export TRIGGERCTL_TZ_OFFSET="${{TRIGGERCTL_TZ_OFFSET:-{DEFAULT_TZ}}}"\n'
        "export TRIGGERCTL_HOOK_JSON=1\n"
        f'exec {triggerctl_cmd} codex-hook\n',
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


def install_user_prompt_hook(triggerctl_cmd: Optional[str] = None) -> Path:
    """Register triggerctl on Codex UserPromptSubmit. Returns hooks.json path."""
    triggerctl_cmd = triggerctl_cmd or shutil.which("triggerctl") or "triggerctl"
    wrapper = install_hook_wrapper(triggerctl_cmd)
    command = str(wrapper)

    path, data = load_hooks()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        bak = path.with_suffix(".json.triggerctl.bak")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    if not hook_installed(data):
        hooks = data.setdefault("hooks", {})
        ups = hooks.setdefault("UserPromptSubmit", [])
        if not isinstance(ups, list):
            ups = []
            hooks["UserPromptSubmit"] = ups
        ups.append(
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": DEFAULT_TIMEOUT,
                        "statusMessage": "Loading triggers",
                    }
                ]
            }
        )

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def install_full(
    triggerctl_cmd: Optional[str] = None,
    skill_source: Optional[Path] = None,
) -> Dict[str, Path]:
    """Full Codex setup: UserPromptSubmit hook + triggerctl skill."""
    triggerctl_cmd = triggerctl_cmd or shutil.which("triggerctl") or "triggerctl"
    hooks_path = install_user_prompt_hook(triggerctl_cmd)
    skill = install_skill(skill_source)
    return {
        "hooks": hooks_path,
        "skill": skill,
        "wrapper": hooks_dir() / "triggerctl-user-prompt-submit.sh",
    }
