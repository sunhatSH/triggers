"""Hermes Agent integration (pre_llm_call shell hooks in ~/.hermes/config.yaml)."""
from __future__ import annotations

import shutil
import sys
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
    from triggerctl.paths import skill_source

    return skill_source()


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


# ── Hermes TUI status bar patch (triggerctl install --statusline) ──────

import ast as _ast  # lazy import guard; only used in statusline functions

_HERMES_CLI_PY = "cli.py"
_STATUS_BAR_METHOD_SENTINEL = "def _get_triggerctl_statusline(self)"


def _hermes_cli_path() -> Optional[Path]:
    """Locate Hermes ``cli.py`` for status bar patching."""
    # Try standard venv layout: hermes entry -> venv/bin/ -> project root/
    candidate = Path.home() / ".hermes" / "hermes-agent" / _HERMES_CLI_PY
    if candidate.is_file():
        return candidate
    # Fallback: walk from sys.executable
    exe = getattr(sys, "executable", None)
    if exe:
        p = Path(exe).parent.parent / _HERMES_CLI_PY
        if p.is_file():
            return p
    return None


def _status_bar_already_patched(content: str) -> bool:
    """Check if triggerctl status bar integration is already present."""
    return _STATUS_BAR_METHOD_SENTINEL in content


def _patch_import_tc_types(content: str) -> str:
    """Add Tuple and ClassVar to the typing import line if absent."""
    for line in content.splitlines(keepends=True):
        if line.startswith("from typing import") and "Tuple" not in line:
            return content.replace(line, line.rstrip() + ", Tuple, ClassVar\n", 1)
    return content


def _patch_insert_method(content: str) -> str:
    """Insert _get_triggerctl_statusline after _format_idle_since."""
    import re
    marker_pat = re.compile(r'return f"✓ \{format_duration_compact\(idle\)\}"\n')
    insertion = (
        '\n'
        '    _triggerctl_status_cache: ClassVar[Optional[Tuple[str, float]]] = None\n'
        '\n'
        '    def _get_triggerctl_statusline(self) -> str:\n'
        '        """Run triggerctl statusline and cache for 5 seconds."""\n'
        '        now = time.time()\n'
        '        cached = self.__class__._triggerctl_status_cache\n'
        '        if cached is not None and now - cached[1] < 5.0:\n'
        '            return cached[0]\n'
        '        try:\n'
        '            import subprocess\n'
        '            result = subprocess.run(\n'
        '                ["triggerctl", "statusline"],\n'
        '                capture_output=True, text=True, timeout=3,\n'
        '            )\n'
        '            line = result.stdout.strip()\n'
        '            self.__class__._triggerctl_status_cache = (line, now)\n'
        '            return line\n'
        '        except Exception:\n'
        '            self.__class__._triggerctl_status_cache = ("", now)\n'
        '            return ""\n'
    )
    m = marker_pat.search(content)
    if not m:
        return content
    marker = m.group(0)
    return content.replace(marker, marker + insertion, 1)


def _patch_render_calls(content: str) -> str:
    """Inject tc_line calls into the three width branches."""
    import re

    # 1. _build_status_bar_text: after parts.append("⚠ YOLO") before return
    def _replace_yolo_return(m):
        yolo_line, trail, ret_call = m.groups()
        return (
            f'{yolo_line}'
            f'{trail}tc_line = self._get_triggerctl_statusline()\n'
            f'{trail}if tc_line:\n'
            f'{trail}    parts.append(tc_line)\n'
            f'{trail}{ret_call}'
        )
    content = re.sub(
        r'(parts\.append\("⚠ YOLO"\)\s*\n)(\s+)(return self\._trim_status_bar_text\()',
        _replace_yolo_return, content,
    )

    # 2. _get_status_bar_fragments dot branch & pipe branch:
    # after yolo block before frags.append(("class:status-bar", …))
    def _replace_yolo_frags(m):
        yolo_block, indent, after = m.groups()
        return (
            f'{yolo_block}\n'
            f'{indent}tc_line = self._get_triggerctl_statusline()\n'
            f'{indent}if tc_line:\n'
            f'{indent}    frags.append(("class:status-bar-dim", " · "))\n'
            f'{indent}    frags.append(("class:status-bar-warn", tc_line))\n'
            f'{indent}{after}'
        )
    # Match yolo block ending with yolo frags.append, then the next frags.append
    content = re.sub(
        r'(if yolo_active:\n(?:[ \t]+.*\n)*?'
        r'[ \t]+frags\.append\(\(["\']class:status-bar-yolo["\'], ["\']⚠ YOLO["\']\)\))\n'
        r'([ \t]*)(frags\.append\(\("class:status-bar["\'])',
        _replace_yolo_frags, content,
    )

    # 3. Same for pipe-separator branch (│ instead of ·)
    def _replace_yolo_frags_pipe(m):
        yolo_block, indent, after = m.groups()
        return (
            f'{yolo_block}\n'
            f'{indent}tc_line = self._get_triggerctl_statusline()\n'
            f'{indent}if tc_line:\n'
            f'{indent}    frags.append(("class:status-bar-dim", " │ "))\n'
            f'{indent}    frags.append(("class:status-bar-warn", tc_line))\n'
            f'{indent}{after}'
        )
    # This catches the 76+ branch where separator is " │ "
    content = re.sub(
        r'(if yolo_active:\n(?:[ \t]+.*\n)*?'
        r'[ \t]+frags\.append\(\(["\']class:status-bar-yolo["\'], ["\']⚠ YOLO["\']\)\))\n'
        r'([ \t]*)(frags\.append\(\("class:status-bar["\'])',
        _replace_yolo_frags_pipe, content,
    )

    return content


def install_statusline_cli_py() -> Optional[Path]:
    """Patch Hermes ``cli.py`` to show ``triggerctl statusline`` in the TUI status bar.

    Idempotent: skips if already patched. Writes ``cli.py.triggerctl.bak``
    before modifying. Returns the patched path, or None if not applicable.
    """
    path = _hermes_cli_path()
    if path is None:
        return None

    original = path.read_text(encoding="utf-8")
    if _status_bar_already_patched(original):
        return None  # already done

    content = original
    content = _patch_import_tc_types(content)
    content = _patch_insert_method(content)
    content = _patch_render_calls(content)

    if content == original:
        return None

    # Backup
    bak = path.with_suffix(path.suffix + ".triggerctl.bak")
    bak.write_text(original, encoding="utf-8")

    path.write_text(content, encoding="utf-8")
    return path


def uninstall_statusline_cli_py() -> Optional[Path]:
    """Revert the triggerctl patch from ``cli.py`` using the backup.

    Returns the restored path, or None if no backup exists.
    """
    path = _hermes_cli_path()
    if path is None:
        return None
    bak = path.with_suffix(path.suffix + ".triggerctl.bak")
    if not bak.is_file():
        return None
    original_text = bak.read_text(encoding="utf-8")
    path.write_text(original_text, encoding="utf-8")
    bak.unlink()
    return path
