from datetime import datetime

from triggerctl import schedule


def test_daily_target_and_key():
    now = datetime(2026, 6, 23, 15, 0)
    target, key = schedule.target_and_key({"every": "day", "at": "14:30"}, None, now)
    assert target == datetime(2026, 6, 23, 14, 30)
    assert key == "2026-06-23"


def test_hour_minute_only():
    now = datetime(2026, 6, 23, 15, 45)
    target, key = schedule.target_and_key({"every": "hour", "at": ":30"}, None, now)
    assert target == datetime(2026, 6, 23, 15, 30)
    assert key == "2026-06-23 15"


def test_week_weekday_chinese():
    now = datetime(2026, 6, 23, 12, 0)  # Tuesday
    target, key = schedule.target_and_key({"every": "week", "on": "周一", "at": "09:00"}, None, now)
    assert target == datetime(2026, 6, 22, 9, 0)  # Monday of that week
    assert key.startswith("2026-W")


def test_month_dom_clamped():
    now = datetime(2026, 2, 15, 0, 0)
    target, _ = schedule.target_and_key({"every": "month", "on": 31}, None, now)
    assert target.day == 28  # Feb 2026 clamps to 28


def test_dedup_override_granularity():
    now = datetime(2026, 6, 23, 15, 45)
    _, key = schedule.target_and_key({"every": "hour", "at": ":30"}, "day", now)
    assert key == "2026-06-23"
