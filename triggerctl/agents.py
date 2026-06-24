"""Agent runtime detection and headless execution (Claude Code / Hermes)."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

EXEC_TIMEOUT = 1800


@dataclass
class ExecResult:
    ok: bool
    output: str
    detail: str


def preferred_agent() -> str:
    """Which agent to use for poll execution: claude, hermes, or auto-detect."""
    v = os.environ.get("TRIGGERCTL_AGENT", "auto").strip().lower()
    if v in ("claude", "hermes"):
        return v
    if shutil.which("hermes") and not shutil.which("claude"):
        return "hermes"
    return "claude"


def find_claude() -> Optional[str]:
    env = os.environ.get("TRIGGERCTL_CLAUDE")
    if env:
        return env
    found = shutil.which("claude")
    if found:
        return found
    p = os.path.expanduser("~/.npm-global/bin/claude")
    return p if os.path.exists(p) else None


def find_hermes() -> Optional[str]:
    return os.environ.get("TRIGGERCTL_HERMES") or shutil.which("hermes")


def find_agent_bin(agent: Optional[str] = None) -> Optional[str]:
    agent = agent or preferred_agent()
    if agent == "hermes":
        return find_hermes()
    return find_claude()


def build_prompt(trigger_name: str, body: str) -> str:
    return (
        "The trigger system invoked you to run ONE trigger. Follow the body steps only; "
        "report results in one or two sentences.\n\n"
        f"# Trigger: {trigger_name}\n\n"
        f"{body.strip()}\n"
    )


def run_prompt(
    prompt: str,
    cwd: Path,
    agent: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    dry_run: bool = False,
    claude_bin: Optional[str] = None,
) -> ExecResult:
    agent = agent or preferred_agent()
    if dry_run:
        return ExecResult(True, "", "dry-run: model not invoked")

    if agent == "hermes":
        return _run_hermes(prompt, cwd, extra_args)
    return _run_claude(prompt, cwd, extra_args, claude_bin=claude_bin)


def _run_claude(
    prompt: str,
    cwd: Path,
    extra_args: Optional[List[str]],
    claude_bin: Optional[str] = None,
) -> ExecResult:
    claude_bin = claude_bin or find_claude()
    if not claude_bin:
        return ExecResult(False, "", "claude CLI not found (set TRIGGERCTL_CLAUDE or add to PATH)")
    cmd = [claude_bin, "-p", prompt, "--permission-mode", "bypassPermissions"]
    if extra_args:
        cmd[3:3] = extra_args
    label = "claude"
    return _run_subprocess(cmd, cwd, label)


def _run_hermes(prompt: str, cwd: Path, extra_args: Optional[List[str]]) -> ExecResult:
    hermes_bin = find_hermes()
    if not hermes_bin:
        return ExecResult(False, "", "hermes CLI not found (set TRIGGERCTL_HERMES or add to PATH)")
    cmd = [hermes_bin, "chat", "-q", prompt]
    if extra_args:
        cmd.extend(extra_args)
    return _run_subprocess(cmd, cwd, "hermes")


def _run_subprocess(cmd: List[str], cwd: Path, label: str) -> ExecResult:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT,
            env={**os.environ, "HERMES_ACCEPT_HOOKS": os.environ.get("HERMES_ACCEPT_HOOKS", "1")},
        )
    except subprocess.TimeoutExpired:
        return ExecResult(False, "", f"timeout (>{EXEC_TIMEOUT}s)")
    except Exception as e:  # noqa: BLE001
        return ExecResult(False, "", f"invoke failed: {e}")

    out = (p.stdout or "").strip()
    if p.returncode != 0:
        err = (p.stderr or "").strip()[:300]
        return ExecResult(False, out, f"{label} exit {p.returncode}: {err}")
    return ExecResult(True, out, "ok")
