from datetime import datetime
from pathlib import Path

from triggerctl import detect
from triggerctl.model import Trigger
from triggerctl.roots import Root


def _t(**kw):
    base = dict(name="t", enabled=True, schedule=None, dedup=None, probe=None,
                dedup_cmd=None, when=None, locked=False, body="do x", path=Path("/tmp/t.md"),
                root=Root("user", Path("/tmp")), meta={})
    base.update(kw)
    return Trigger(**base)


def test_time_due_after_target():
    t = _t(schedule={"every": "day", "at": "14:30"})
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert d.due and d.key == "2026-06-23"


def test_time_not_due_before_target():
    t = _t(schedule={"every": "day", "at": "14:30"})
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 9, 0), done=set())
    assert not d.due and d.status == "not-due"


def test_dedup_blocks_second_run():
    t = _t(schedule={"every": "day", "at": "14:30"})
    now = datetime(2026, 6, 23, 15, 0)
    d = detect.evaluate(t, now=now, done={("t", "2026-06-23")})
    assert not d.due and d.status == "deduped"


def test_probe_true():
    t = _t(probe="true")
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert d.due and d.key == "once"


def test_probe_false():
    t = _t(probe="false")
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert not d.due


def test_combined_and_needs_both():
    # time ok but probe false -> not due
    t = _t(schedule={"every": "day", "at": "14:30"}, probe="false")
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert not d.due


def test_combined_key_has_both_parts():
    t = _t(schedule={"every": "day", "at": "14:30"}, probe="true",
           dedup_cmd="echo INST")
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert d.due and d.key == "2026-06-23|INST"


def test_disabled():
    t = _t(enabled=False, probe="true")
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert not d.due and d.status == "disabled"


def test_invalid_no_conditions():
    t = _t()
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert not d.due and d.status == "invalid"


def test_session_when_skipped():
    t = _t(when="完成一个特性时")
    d = detect.evaluate(t, now=datetime(2026, 6, 23, 15, 0), done=set())
    assert not d.due and d.status == "session"
    assert t.kind == "session"
