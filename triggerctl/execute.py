"""Model execution tier — invoke `claude -p` to run a DUE trigger's body.

Only ever called for triggers the cheap tier already decided are DUE, so the
expensive model runs at most once per actual trigger firing.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from .model import Trigger

EXEC_TIMEOUT = 1800  # 30 min hard cap per trigger


@dataclass
class ExecResult:
    ok: bool
    output: str
    detail: str


def find_claude() -> Optional[str]:
    return (
        os.environ.get("TRIGGERCTL_CLAUDE")
        or shutil.which("claude")
        or _known_path()
    )


def _known_path() -> Optional[str]:
    p = os.path.expanduser("~/.npm-global/bin/claude")
    return p if os.path.exists(p) else None


def build_prompt(trigger: Trigger) -> str:
    return (
        "你被触发器系统拉起来执行下面这个触发器的动作。只做这一件事，"
        "按正文步骤执行，做完用一两句话汇报结果。\n\n"
        f"# 触发器: {trigger.name}\n\n"
        f"{trigger.body.strip()}\n"
    )


def execute(
    trigger: Trigger,
    claude_bin: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    dry_run: bool = False,
) -> ExecResult:
    claude_bin = claude_bin or find_claude()
    if not claude_bin:
        return ExecResult(False, "", "找不到 claude CLI（设 TRIGGERCTL_CLAUDE 或装进 PATH）")

    prompt = build_prompt(trigger)
    if dry_run:
        return ExecResult(True, "", "dry-run: 未真正调用模型")

    cmd = [claude_bin, "-p", prompt, "--permission-mode", "bypassPermissions"]
    if extra_args:
        cmd[3:3] = extra_args
    try:
        p = subprocess.run(
            cmd,
            cwd=str(trigger.root.base),
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return ExecResult(False, "", f"执行超时(>{EXEC_TIMEOUT}s)")
    except Exception as e:  # noqa: BLE001
        return ExecResult(False, "", f"调用失败: {e}")

    out = (p.stdout or "").strip()
    if p.returncode != 0:
        return ExecResult(False, out, f"claude 退出码 {p.returncode}: {(p.stderr or '').strip()[:300]}")
    return ExecResult(True, out, "ok")
