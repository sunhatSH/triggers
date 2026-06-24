"""Strict context policy tests."""
from triggerctl import commands, hookgen
from triggerctl.roots import Root


def _root(tmp_path):
    return Root("project", tmp_path / "triggers")


def test_triggers_index_session_only(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("daily", None, None, "day", "02:00", None, None,
                     None, None, None, False, False)
    commands.cmd_add("feat", None, None, None, None, None, None,
                     None, None, "完成特性", False, False)
    text = root.index_file.read_text()
    assert "feat" in text
    assert "daily" not in text
    assert "Not injected" in text or "ops index" in text


def test_inject_false_excluded(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    monkeypatch.setattr(commands, "resolve", lambda sel: [root])
    p = root.path / "x-triggers" / "meta.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        "---\nname: meta\nenabled: true\ninject: false\nwhen: 总是\n---\n\nbody\n",
        encoding="utf-8",
    )
    commands.cmd_sync(None)
    assert hookgen.session_context([root]) == ""
    assert "meta" not in root.index_file.read_text()
