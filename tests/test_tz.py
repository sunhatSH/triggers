from datetime import datetime, timezone

from triggerctl import schedule
from triggerctl.tz import effective_now, tz_offset, tz_label


def test_effective_now_default_offset(monkeypatch):
    monkeypatch.delenv("TRIGGERCTL_TZ_OFFSET", raising=False)
    assert tz_offset() == 8.0
    utc = datetime(2026, 6, 23, 6, 0, tzinfo=timezone.utc)
    assert effective_now(utc) == datetime(2026, 6, 23, 14, 0)


def test_effective_now_zero(monkeypatch):
    monkeypatch.setenv("TRIGGERCTL_TZ_OFFSET", "0")
    utc = datetime(2026, 6, 23, 14, 30, tzinfo=timezone.utc)
    assert effective_now(utc) == datetime(2026, 6, 23, 14, 30)


def test_schedule_at_interpreted_in_local_time(monkeypatch):
    monkeypatch.setenv("TRIGGERCTL_TZ_OFFSET", "8")
    utc_morning = datetime(2026, 6, 23, 6, 0, tzinfo=timezone.utc)
    local = effective_now(utc_morning)
    target, _ = schedule.target_and_key({"every": "day", "at": "14:30"}, None, local)
    assert local.hour == 14
    assert local < target
    utc_afternoon = datetime(2026, 6, 23, 6, 31, tzinfo=timezone.utc)
    local_due = effective_now(utc_afternoon)
    target2, _ = schedule.target_and_key({"every": "day", "at": "14:30"}, None, local_due)
    assert local_due >= target2


def test_tz_label():
    assert tz_label().startswith("UTC")
