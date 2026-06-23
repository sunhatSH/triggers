"""Context block injected into every prompt (Claude Code UserPromptSubmit hook).

This is what actually *embeds* session triggers into the Agent: their conditions are
printed here and added to context each turn, instead of sitting in a TRIGGERS.md file
the model never opens. The model then self-checks and acts (soft for semantic `when`,
but now reliably surfaced).
"""
from __future__ import annotations

from typing import List, Optional

from .model import discover
from .roots import Root, all_roots


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
        "[触发器系统] 本会话生效的 session 触发器。处理本条消息时，**逐条自检下列条件**，",
        "凡满足的就执行该触发器对应文件里的动作，并在回复开头标注来源 `[触发器: <名称>]`：",
    ]
    for name, when, rel, kind in items:
        lines.append(f"- {name} — 条件：{when}（{kind}:{rel}）")
    lines.append("（time/event 型由 `triggerctl poll` 后台处理，无需你在会话内管。）")
    return "\n".join(lines)
