"""Bundled optional triggers — not auto-installed on init."""
from pathlib import Path

from triggerctl import package


def test_list_bundled():
    repo = Path(__file__).resolve().parents[1]
    files = package.list_available(str(repo / "bundled"))
    names = {f.name for f in files}
    assert "auto-commit-push" in names
    assert "rest-reminder" in names


def test_init_does_not_install_bundled(tmp_path, monkeypatch):
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
