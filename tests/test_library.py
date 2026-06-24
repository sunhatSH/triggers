"""Official trigger library list/install."""
from triggerctl import library as lib
from triggerctl.paths import library_dir


def test_list_local_library():
    entries = lib.list_entries(str(library_dir()))
    names = {e.name for e in entries}
    assert "rest-reminder" in names
    assert "auto-commit-push" in names
    assert "daily-backup" in names
    assert len(entries) >= 6


def test_manifest_fields():
    entries = lib.list_entries(str(library_dir()))
    rest = next(e for e in entries if e.name == "rest-reminder")
    assert rest.kind == "session"
    assert rest.inject is False
    assert rest.description


def test_install_single_local(tmp_path, monkeypatch):
    from triggerctl import package
    from triggerctl.roots import Root

    root = Root("user", tmp_path / ".claude" / "triggers")
    monkeypatch.setattr(package, "primary", lambda sel: root)
    result = lib.install_names(["rest-reminder"], "user", False, str(library_dir()))
    assert "rest-reminder" in result.installed
    assert (root.path / "wellbeing-triggers" / "rest-reminder.md").is_file()


def test_install_unknown_name():
    from triggerctl import package

    result = lib.install_names(["no-such-trigger"], "user", False, str(library_dir()))
    assert result.errors
    assert not result.installed


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
    assert "auto-commit-push" not in names
