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


def _now_line() -> str:
    """Authoritative current time, pre-converted to the user's timezone.

    机器时钟通常是 UTC 且常缺 tzdata，模型容易把 UTC 当本地时间。这里直接把换算好的
    本地时间喂进去，模型做时间判断时不必（也不应）自己换算。偏移用 TRIGGERCTL_TZ_OFFSET（小时，默认 8=北京）。
    """
    try:
        off = float(os.environ.get("TRIGGERCTL_TZ_OFFSET", "8"))
    except ValueError:
        off = 8.0
    now = datetime.now(timezone.utc) + timedelta(hours=off)
    sign = "+" if off >= 0 else "-"
    return (f"当前时间：UTC{sign}{abs(off):g} {now:%Y-%m-%d %H:%M}（已为你换算；"
            f"做任何时间判断都用这个值，**不要**用机器 `date`，那是 UTC）。")


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
