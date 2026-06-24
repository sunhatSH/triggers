"""Cheap detection tier (pure Python, NO model).

Evaluate every declared condition (schedule AND probe). A trigger is DUE only when
all declared conditions hold and (name, key) is not already in the run-log.
This is what runs frequently; the expensive model is only invoked for DUE triggers.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, Tuple

from . import schedule as sched
from .model import Trigger
from .tz import effective_now

PROBE_TIMEOUT = 30


@dataclass
class Decision:
    trigger: Trigger
    due: bool
    key: str
    status: str   # "due" | "not-due" | "deduped" | "disabled" | "invalid" | "error"
    reason: str


def _run(cmd: str) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=PROBE_TIMEOUT
        )
        return p.returncode, (p.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return 124, ""
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def evaluate(
    trigger: Trigger,
    now: Optional[datetime] = None,
    done: Optional[Set[Tuple[str, str]]] = None,
) -> Decision:
    now = now or effective_now()
    done = done or set()

    if not trigger.enabled:
        return Decision(trigger, False, "", "disabled", "enabled:false")
    if trigger.is_session:
        return Decision(trigger, False, "", "session", "会话内 Agent 判断(when)，轮询不处理")
    if not trigger.valid:
        return Decision(trigger, False, "", "invalid", "缺少 name 或未声明 schedule/probe/when")

    parts = []

    # --- time condition (cheap first; short-circuit before running probe) ---
    if trigger.schedule:
        try:
            target, pkey = sched.target_and_key(trigger.schedule, trigger.dedup, now)
        except Exception as e:  # noqa: BLE001
            return Decision(trigger, False, "", "error", f"schedule 解析失败: {e}")
        if now < target:
            return Decision(trigger, False, "", "not-due", f"未到点(target {target:%Y-%m-%d %H:%M})")
        parts.append(pkey)

    # --- probe condition ---
    if trigger.probe:
        rc, _ = _run(trigger.probe)
        if rc != 0:
            return Decision(trigger, False, "", "not-due", f"probe 不成立(rc={rc})")
        if trigger.dedup_cmd:
            drc, dout = _run(trigger.dedup_cmd)
            subkey = dout if drc == 0 and dout else "once"
        else:
            subkey = "once"
        parts.append(subkey)

    key = "|".join(parts) if parts else "once"

    if (trigger.name, key) in done:
        return Decision(trigger, False, key, "deduped", f"本周期/实例已处理(key={key})")

    return Decision(trigger, True, key, "due", f"条件全满足(key={key})")
