"""Context block injected into every prompt (Claude Code UserPromptSubmit hook).

This is what actually *embeds* session triggers into the Agent: their conditions are
printed here and added to context each turn, instead of sitting in a TRIGGERS.md file
the model never opens. The model then self-checks and acts (soft for semantic `when`,
but now reliably surfaced).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .model import discover
from .roots import Root, all_roots


def _tz_offset() -> float:
    try:
        return float(os.environ.get("TRIGGERCTL_TZ_OFFSET", "8"))
    except ValueError:
        return 8.0


def local_now() -> datetime:
    """Current time converted to the user's timezone (machine clock is usually UTC)."""
    return datetime.now(timezone.utc) + timedelta(hours=_tz_offset())


def _now_line() -> str:
    """Authoritative current time, pre-converted — so the model never misreads UTC as local."""
    off = _tz_offset()
    now = local_now()
    sign = "+" if off >= 0 else "-"
    return (f"当前时间：UTC{sign}{abs(off):g} {now:%Y-%m-%d %H:%M}（已为你换算；"
            f"做任何时间判断都用这个值，**不要**用机器 `date`，那是 UTC）。")


def statusline(data: dict, now: Optional[datetime] = None) -> str:
    """Deterministic status-line text (shown by Claude Code, not model-mediated).

    Shows model · dir · local time, and a rest hint during 22:00–10:00.
    """
    now = now or local_now()
    data = data or {}
    model = (data.get("model") or {}).get("display_name") or ""
    ws = data.get("workspace") or {}
    cwd = ws.get("current_dir") or data.get("cwd") or ""
    base = os.path.basename(str(cwd).rstrip("/")) if cwd else ""
    parts = [p for p in (model, base, now.strftime("%H:%M")) if p]
    line = " · ".join(parts)
    h = now.hour
    if h >= 22 or h < 10:
        line += f"  🌙 该休息了（北京 {now:%H:%M}）"
    return line


def session_context(roots: Optional[List[Root]] = None) -> str:
    roots = roots if roots is not None else all_roots()
    items = []
    for root in roots:
        for t in discover(root):
            if t.enabled and t.is_session:
                items.append((t.name, (t.when or "").strip(), t.rel_path, root.kind))
    if not items:
        return ""

    lines = [
        f"[触发器系统 · 高优先级指令] {_now_line()}",
        "下列 session 触发器在本会话生效。**在回答用户问题之前**，先逐条判断其条件是否满足；",
        "凡满足的，**必须**在你本次回复的**最开头**先输出 `[触发器: <名称>] <对应动作/提醒>`，",
        "然后再正常回答用户——即使用户问的是别的事，也不得省略（除非用户明确要求只输出某内容）：",
    ]
    for name, when, rel, kind in items:
        lines.append(f"- {name} — 条件：{when}（{kind}:{rel}）")
    lines.append("（time/event 型由 `triggerctl poll` 后台处理，无需你在会话内管。）")
    return "\n".join(lines)
