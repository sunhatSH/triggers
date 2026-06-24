"""CLI: install triggers from library."""
from pathlib import Path

import pytest

from triggerctl import commands, library as lib

FIXTURE_LIB = Path(__file__).resolve().parents[2] / "trigger-library"


@pytest.fixture
def synced_library(tmp_path, monkeypatch):
    dest = tmp_path / "library"
    monkeypatch.setattr("triggerctl.paths.local_library_dir", lambda: dest)
    monkeypatch.setattr("triggerctl.library.local_library_dir", lambda: dest)
    lib.sync_library(str(FIXTURE_LIB))
    return dest


def test_install_by_name(synced_library, tmp_path, monkeypatch, capsys):
    from triggerctl import package
    from triggerctl.model import find
    from triggerctl.roots import Root

    root = Root("user", tmp_path / ".claude" / "triggers")
    monkeypatch.setattr(package, "primary", lambda sel: root)
    rc = commands.cmd_install_triggers(["rest-reminder"], "user", False, False, None, False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "✓ 已安装 rest-reminder，已启用" in out
    t = find([root], "rest-reminder")
    assert t is not None and t.enabled


def test_install_all_from_path(tmp_path, monkeypatch, capsys):
    from triggerctl import package
    from triggerctl.model import discover
    from triggerctl.roots import Root

    root = Root("user", tmp_path / ".claude" / "triggers")
    monkeypatch.setattr(package, "primary", lambda sel: root)
    rc = commands.cmd_install_triggers([], "user", False, True, str(FIXTURE_LIB), False)
    assert rc == 0
    assert len(discover(root)) >= 6
    assert "✓ 已安装" in capsys.readouterr().out


def test_install_from_dir_requires_all(tmp_path, monkeypatch, capsys):
    rc = commands.cmd_install_triggers([], "user", False, False, str(FIXTURE_LIB), False)
    assert rc == 2
    assert "--all" in capsys.readouterr().err


def test_install_from_single_file(tmp_path, monkeypatch, capsys):
    from triggerctl import package
    from triggerctl.roots import Root

    root = Root("user", tmp_path / ".claude" / "triggers")
    monkeypatch.setattr(package, "primary", lambda sel: root)
    src = FIXTURE_LIB / "poll" / "daily-backup.md"
    rc = commands.cmd_install_triggers([], "user", False, False, str(src), False)
    assert rc == 0
    assert "✓ 已安装 daily-backup，已启用" in capsys.readouterr().out
