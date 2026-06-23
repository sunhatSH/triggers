"""Turn a `schedule` block into (target datetime, period key) for the current period.

schedule:
  every: day | hour | week | month
  at:    "HH:MM" | ":MM" | "HH:MM"   (optional; default 00:00, hour-type uses current hour)
  on:    weekday (week) | day-of-month int (month)   (optional)
dedup:   optional granularity override for the period key (default == every)
"""
from __future__ import annotations

import calendar
from datetime import datetime
from typing import Optional, Tuple

EVERY = {"day", "hour", "week", "month"}

_WD = {
    # Monday = 0
    "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6, "周天": 6,
    "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期日": 6, "星期天": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}


def _weekday(on) -> int:
    if isinstance(on, int):
        return (on - 1) % 7  # 1=Mon .. 7=Sun
    s = str(on).strip().lower()
    if s in _WD:
        return _WD[s]
    if s.isdigit():
        return (int(s) - 1) % 7
    raise ValueError(f"无法解析 weekday: {on!r}")


def _parse_at(at) -> Tuple[Optional[int], int]:
    """Return (hour|None, minute)."""
    if at is None:
        return 0, 0
    s = str(at).strip()
    if s.startswith(":"):
        return None, int(s[1:] or 0)
    if ":" in s:
        h, m = s.split(":", 1)
        return int(h), int(m or 0)
    return int(s), 0


def target_and_key(schedule: dict, dedup: Optional[str], now: datetime) -> Tuple[datetime, str]:
    every = str(schedule.get("every", "")).lower()
    if every not in EVERY:
        raise ValueError(f"schedule.every 必须是 {sorted(EVERY)}，得到 {every!r}")
    h, m = _parse_at(schedule.get("at"))
    gran = (dedup or every).lower()

    if every == "day":
        target = now.replace(hour=h or 0, minute=m, second=0, microsecond=0)
    elif every == "hour":
        target = now.replace(minute=m, second=0, microsecond=0)
    elif every == "week":
        wd = _weekday(schedule.get("on", 1))
        monday = now - _days(now.weekday())
        target = monday.replace(hour=h or 0, minute=m, second=0, microsecond=0) + _days(wd)
    elif every == "month":
        dom = int(schedule.get("on", 1))
        last = calendar.monthrange(now.year, now.month)[1]
        dom = min(dom, last)
        target = now.replace(day=dom, hour=h or 0, minute=m, second=0, microsecond=0)
    else:  # unreachable
        raise ValueError(every)

    return target, _period_key(gran, now)


def _period_key(gran: str, now: datetime) -> str:
    if gran == "day":
        return now.strftime("%Y-%m-%d")
    if gran == "hour":
        return now.strftime("%Y-%m-%d %H")
    if gran == "week":
        return now.strftime("%G-W%V")
    if gran == "month":
        return now.strftime("%Y-%m")
    # fallback: treat unknown granularity as day
    return now.strftime("%Y-%m-%d")


def _days(n: int):
    from datetime import timedelta
    return timedelta(days=n)
