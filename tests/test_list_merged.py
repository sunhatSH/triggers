"""Merged list: installed + store templates with status column."""
from triggerctl import commands


def test_list_merged_statuses(synced_library, tmp_path, monkeypatch, capsys):
    from triggerctl import package
    from triggerctl.roots import Root

    user = Root("user", tmp_path / ".claude" / "triggers")
    user.path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(commands, "resolve", lambda sel: [user])
    commands.cmd_init("user")

    commands.cmd_list(None)
    out = capsys.readouterr().out
    assert "未安装" in out
    assert "已启用" in out  # too-many-triggers-warning
    assert "rest-reminder" in out

    monkeypatch.setattr(package, "primary", lambda sel: user)
    commands.cmd_install_triggers(["rest-reminder"], None, False, False, None, False)
    commands.cmd_list(None)
    out2 = capsys.readouterr().out
    assert "rest-reminder      session  已启用" in out2
    assert "rest-reminder      session  未安装" not in out2
