"""Session-trigger context for Claude Code UserPromptSubmit hook.

Only semantic session triggers (``when`` without schedule/probe) are embedded.
Fixed schedule and rule/probe triggers are handled by ``triggerctl poll`` and
never appear here.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from .model import discover
from .roots import Root, all_roots
from .tz import effective_now, tz_offset

# Markers used in injected blocks (and transcript replacement).
TRIGGER_BLOCK_PREFIX = "[Triggers·"
TRIGGER_BLOCK_PREFIX_LEGACY = "[触发器·"
TRIGGER_MARKERS = (TRIGGER_BLOCK_PREFIX, TRIGGER_BLOCK_PREFIX_LEGACY)

# Guardrail: too-many-triggers-warning (statusLine + doctor, not hook).
TOO_MANY_THRESHOLD = 5


def enabled_trigger_count(roots: Optional[List[Root]] = None) -> int:
    """Count triggers eligible for hook context injection (semantic session, inject!=false)."""
    roots = roots if roots is not None else all_roots()
    total = 0
    for root in roots:
        if not root.path.is_dir():
            continue
        total += sum(1 for t in discover(root) if t.in_context)
    return total


def local_now() -> datetime:
    """Current time in the configured timezone (naive datetime)."""
    return effective_now()


def _now_line() -> str:
    """Authoritative local time so the model does not misread machine UTC."""
    off = tz_offset()
    now = local_now()
    sign = "+" if off >= 0 else "-"
    return (
        f"Current time: UTC{sign}{abs(off):g} {now:%Y-%m-%d %H:%M} "
        f"(pre-converted; use this for time checks, not shell `date` which may be UTC)."
    )


def statusline(
    data: dict,
    now: Optional[datetime] = None,
    roots: Optional[List[Root]] = None,
) -> str:
    """Deterministic status-line text (shown by Claude Code, not model-mediated)."""
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
        line += f"  🌙 rest window ({now:%H:%M})"
    n = enabled_trigger_count(roots)
    if n > TOO_MANY_THRESHOLD:
        line += f"  ⚠️ {n} context triggers (>{TOO_MANY_THRESHOLD})"
    return line


def session_context(roots: Optional[List[Root]] = None) -> str:
    """Build the per-turn trigger reminder block (semantic session triggers only)."""
    roots = roots if roots is not None else all_roots()
    items = []
    for root in roots:
        for t in discover(root):
            if t.in_context:
                items.append((t.name, (t.when or "").strip(), t.rel_path, root.kind))
    if not items:
        return ""

    now = local_now()
    off = tz_offset()
    sign = "+" if off >= 0 else "-"
    lines = [
        (
            f"{TRIGGER_BLOCK_PREFIX}UTC{sign}{abs(off):g} {now:%H:%M}] "
            "When a trigger matches, start the reply with `[Trigger: name] …`:"
        ),
        _now_line(),
    ]
    for name, when, rel, kind in items:
        scope = "project" if kind == "project" else "user"
        lines.append(f"- {name} ({scope}): {when} → `{rel}`")
    return "\n".join(lines)
