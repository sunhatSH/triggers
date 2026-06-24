from triggerctl import commands, hookgen
from triggerctl.roots import Root


def _root(tmp_path):
    return Root("project", tmp_path / "triggers")


def test_empty_when_no_session(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("daily", None, None, "day", "14:30", None, None,
                     None, None, None, False, False)
    assert hookgen.session_context([root]) == ""


def test_session_trigger_in_context(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("feat", None, None, None, None, None, None,
                     None, None, "when a feature is done", False, False)
    block = hookgen.session_context([root])
    assert "feat" in block
    assert "when a feature is done" in block
    assert hookgen.TRIGGER_BLOCK_PREFIX in block


def test_combo_when_schedule_not_in_context(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    p = root.path / "x-triggers" / "combo.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        "---\nname: combo\nenabled: true\nwhen: always\nschedule:\n  every: day\n  at: '02:00'\n---\n\nbody\n",
        encoding="utf-8",
    )
    assert hookgen.session_context([root]) == ""
    from triggerctl import registry
    registry.sync(root)
    assert "combo" not in root.index_file.read_text()


def test_statusline_rest_window():
    from datetime import datetime
    line = hookgen.statusline({"model": {"display_name": "M"}, "cwd": "/a/proj"},
                              now=datetime(2026, 6, 23, 23, 5))
    assert "proj" in line and "23:05" in line and "🌙" in line


def test_statusline_daytime_no_rest():
    from datetime import datetime
    line = hookgen.statusline({"cwd": "/a/proj"}, now=datetime(2026, 6, 23, 15, 0))
    assert "🌙" not in line and "proj" in line


def test_statusline_too_many_triggers(tmp_path, monkeypatch):
    from datetime import datetime
    from triggerctl import frontmatter

    root = _root(tmp_path)
    monkeypatch.setattr(hookgen, "all_roots", lambda: [root])
    root.path.mkdir(parents=True, exist_ok=True)
    for i in range(21):
        p = root.path / f"t-{i}.md"
        frontmatter.write_file(
            p,
            {"name": f"t-{i}", "enabled": True, "when": "always"},
            f"# t-{i}\n",
        )
    line = hookgen.statusline({"cwd": "/a/proj"}, now=datetime(2026, 6, 23, 15, 0))
    assert "⚠️" in line and "21 triggers" in line and ">20" in line


def test_statusline_under_threshold_no_warn(tmp_path, monkeypatch):
    from datetime import datetime

    root = _root(tmp_path)
    monkeypatch.setattr(hookgen, "all_roots", lambda: [root])
    root.path.mkdir(parents=True, exist_ok=True)
    line = hookgen.statusline({"cwd": "/a/proj"}, now=datetime(2026, 6, 23, 15, 0))
    assert "⚠️" not in line


def test_disabled_session_excluded(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("feat", None, None, None, None, None, None,
                     None, None, "when done", True, False)
    assert hookgen.session_context([root]) == ""
