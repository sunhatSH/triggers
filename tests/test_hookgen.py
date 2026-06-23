from triggerctl import commands, hookgen
from triggerctl.roots import Root


def _root(tmp_path):
    return Root("project", tmp_path / "triggers")


def test_empty_when_no_session(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    # only a time trigger -> not session -> no context block
    commands.cmd_add("daily", None, None, "day", "14:30", None, None,
                     None, None, None, False, False)
    assert hookgen.session_context([root]) == ""


def test_session_trigger_in_context(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("feat", None, None, None, None, None, None,
                     None, None, "完成一个特性时", False, False)
    block = hookgen.session_context([root])
    assert "feat" in block
    assert "完成一个特性时" in block
    assert "触发器系统" in block
    assert "当前时间" in block  # 注入了换算后的当前时间


def test_statusline_rest_window():
    from datetime import datetime
    line = hookgen.statusline({"model": {"display_name": "M"}, "cwd": "/a/proj"},
                              now=datetime(2026, 6, 23, 23, 5))
    assert "proj" in line and "23:05" in line and "🌙" in line


def test_statusline_daytime_no_rest():
    from datetime import datetime
    line = hookgen.statusline({"cwd": "/a/proj"}, now=datetime(2026, 6, 23, 15, 0))
    assert "🌙" not in line and "proj" in line


def test_disabled_session_excluded(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_add("feat", None, None, None, None, None, None,
                     None, None, "完成一个特性时", True, False)  # disabled
    assert hookgen.session_context([root]) == ""
