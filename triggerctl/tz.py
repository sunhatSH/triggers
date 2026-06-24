"""Timezone helpers — TRIGGERCTL_TZ_OFFSET applies to schedule, hook, and statusLine."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional


def tz_offset() -> float:
    """Hours east of UTC (default 8 = Beijing). Set TRIGGERCTL_TZ_OFFSET=0 for UTC."""
    raw = os.environ.get("TRIGGERCTL_TZ_OFFSET")
    if raw is None or raw == "":
        return 8.0
    try:
        return float(raw)
    except ValueError:
        return 8.0


def effective_now(utc: Optional[datetime] = None) -> datetime:
    """Naive datetime in the user's configured timezone.

    Machine clock is usually UTC; schedule `--at` is interpreted in this local time.
    """
    if utc is None:
        utc = datetime.now(timezone.utc)
    elif utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    local = utc + timedelta(hours=tz_offset())
    return local.replace(tzinfo=None)


def tz_label() -> str:
    off = tz_offset()
    sign = "+" if off >= 0 else "-"
    return f"UTC{sign}{abs(off):g}"
