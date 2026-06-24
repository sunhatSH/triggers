"""Merged list: installed + store templates with status column."""
from pathlib import Path

import pytest

from triggerctl import commands
from triggerctl import library as lib

FIXTURE_LIB = Path(__file__).resolve().parents[2] / "trigger-library"


@pytest.fixture
def synced_library(tmp_path, monkeypatch):
    dest = tmp_path / "library"
    monkeypatch.setattr("triggerctl.paths.local_library_dir", lambda: dest)
    monkeypatch.setattr("triggerctl.library.local_library_dir", lambda: dest)
    lib.sync_library(str(FIXTURE_LIB))
    return dest


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
    from triggerctl import library as lib

    lib.install_names(["rest-reminder"], "user", False)
    commands.cmd_list(None)
    out2 = capsys.readouterr().out
    assert "rest-reminder      session  已启用" in out2
    assert "rest-reminder      session  未安装" not in out2
