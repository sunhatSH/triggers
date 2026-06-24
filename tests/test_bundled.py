"""Bundled optional triggers — not auto-installed on init."""
from triggerctl import package
from triggerctl.paths import catalog_dir


def test_list_catalog_session():
    files = package.list_available(str(catalog_dir() / "session"))
    names = {f.name for f in files}
    assert "auto-commit-push" in names
    assert "rest-reminder" in names


def test_list_catalog_poll():
    files = package.list_available(str(catalog_dir() / "poll"))
    names = {f.name for f in files}
    assert "daily-backup" in names
    assert "on-train-done" in names


def test_init_does_not_install_catalog(tmp_path, monkeypatch):
    from triggerctl import commands
    from triggerctl.model import discover
    from triggerctl.roots import Root

    root = Root("user", tmp_path / ".claude" / "triggers")
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_init("user")
    names = {t.name for t in discover(root)}
    assert commands.WARN_NAME in names
    assert "auto-commit-push" not in names
    assert "rest-reminder" not in names
    assert "daily-backup" not in names
