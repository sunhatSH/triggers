"""End-to-end on a temp root: add -> list/discover -> sync -> detect -> poll(dry)."""
from datetime import datetime

from triggerctl import commands, registry, runlog
from triggerctl.model import discover, find
from triggerctl.roots import Root
from triggerctl import poll as poll_mod


def _root(tmp_path):
    return Root("project", tmp_path / "triggers")


def test_add_creates_file_and_index(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    monkeypatch.setattr(commands, "resolve", lambda sel: [root])

    rc = commands.cmd_add("daily", None, "git", "day", "14:30", None, None,
                          None, None, None, False, False)
    assert rc == 0
    triggers = discover(root)
    assert len(triggers) == 1 and triggers[0].name == "daily"
    assert root.index_file.exists()
    assert "daily" in root.index_file.read_text()


def test_disable_toggles(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    monkeypatch.setattr(commands, "resolve", lambda sel: [root])
    commands.cmd_add("daily", None, None, "day", "14:30", None, None,
                     None, None, None, False, False)
    commands.cmd_toggle("daily", None, False)
    t = find([root], "daily")
    assert t.enabled is False


def test_poll_dry_run_marks_due(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("ev", None, None, None, None, None, None,
                     "true", None, None, False, False)  # pure event, probe true
    rep = poll_mod.poll([root], now=datetime(2026, 6, 23, 15, 0), do_execute=False)
    statuses = {o.name: o.status for o in rep.outcomes}
    assert statuses["ev"] == "due"


def test_session_trigger_skipped_by_poller(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("feat", None, None, None, None, None, None,
                     None, None, "完成一个特性时", False, False)  # when -> session
    t = find([root], "feat")
    assert t.kind == "session" and t.is_session
    rep = poll_mod.poll([root], now=datetime(2026, 6, 23, 15, 0), do_execute=True)
    statuses = {o.name: o.status for o in rep.outcomes}
    assert statuses["feat"] == "session"  # poller does not execute it


def test_locked_cannot_disable(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    monkeypatch.setattr(commands, "resolve", lambda sel: [root])
    commands.cmd_add("guard", None, None, None, None, None, None,
                     None, None, "总是", False, False, True)  # locked session trigger
    t = find([root], "guard")
    assert t.locked is True
    rc = commands.cmd_toggle("guard", None, False)  # try disable
    assert rc == 2
    assert find([root], "guard").enabled is True  # still enabled
    rc = commands.cmd_remove("guard", None)  # try remove
    assert rc == 2
    assert find([root], "guard") is not None  # still present


def test_init_seeds_locked_guardrail(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_init(None)
    t = find([root], commands.WARN_NAME)
    assert t is not None and t.locked and t.kind == "session"


def test_runlog_dedup(tmp_path):
    root = _root(tmp_path)
    root.state_dir.mkdir(parents=True, exist_ok=True)
    runlog.append(root, "x", "2026-06-23", "ok")
    entries = runlog.load(root)
    assert ("x", "2026-06-23") in runlog.done_keys(entries)
