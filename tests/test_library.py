"""Official trigger library — separate repo, fixed local sync dir."""
from pathlib import Path

import pytest

from triggerctl import library as lib
from triggerctl.paths import local_library_dir

FIXTURE_LIB = Path(__file__).resolve().parents[2] / "trigger-library"


@pytest.fixture
def synced_library(tmp_path, monkeypatch):
    dest = tmp_path / "library"
    monkeypatch.setattr("triggerctl.paths.local_library_dir", lambda: dest)
    monkeypatch.setattr("triggerctl.library.local_library_dir", lambda: dest)
    lib.sync_library(str(FIXTURE_LIB))
    return dest


def test_sync_local(synced_library):
    assert (synced_library / "manifest.yaml").is_file()
    assert (synced_library / "session" / "rest-reminder.md").is_file()


def test_list_default_local(synced_library):
    entries = lib.list_entries()
    names = {e.name for e in entries}
    assert "rest-reminder" in names
    assert len(entries) >= 6


def test_manifest_fields(synced_library):
    rest = next(e for e in lib.list_entries() if e.name == "rest-reminder")
    assert rest.kind == "session"
    assert rest.inject is False


def test_list_adhoc_source():
    entries = lib.list_entries(str(FIXTURE_LIB))
    assert any(e.name == "daily-backup" for e in entries)


def test_install_single(synced_library, tmp_path, monkeypatch):
    from triggerctl import package
    from triggerctl.roots import Root

    root = Root("user", tmp_path / ".claude" / "triggers")
    monkeypatch.setattr(package, "primary", lambda sel: root)
    result = lib.install_names(["rest-reminder"], "user", False)
    assert "rest-reminder" in result.installed


def test_install_unknown(synced_library):
    result = lib.install_names(["no-such"], "user", False)
    assert result.errors


def test_init_does_not_install_library(tmp_path, monkeypatch):
    from triggerctl import commands
    from triggerctl.model import discover
    from triggerctl.roots import Root

    root = Root("user", tmp_path / ".claude" / "triggers")
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_init("user")
    names = {t.name for t in discover(root)}
    assert commands.WARN_NAME in names
    assert "rest-reminder" not in names
