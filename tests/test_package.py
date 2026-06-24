"""Tests for install-from-source and lock file."""
from pathlib import Path

from triggerctl import commands, lockfile
from triggerctl.model import discover, find
from triggerctl.roots import Root


def _root(tmp_path):
    return Root("project", tmp_path / "triggers")


def test_install_local_example(tmp_path, monkeypatch):
    root = _root(tmp_path)
    from triggerctl import package

    monkeypatch.setattr(package, "primary", lambda sel: root)
    repo = Path(__file__).resolve().parents[1] / "examples" / "time-daily-backup.md"
    rc = commands.cmd_add_from(str(repo), None, None, False, False)
    assert rc == 0
    t = find([root], "daily-backup")
    assert t is not None and t.kind == "time"
    pkgs = lockfile.list_packages(root)
    assert len(pkgs) == 1
    assert pkgs[0]["triggers"]["daily-backup"]


def test_install_skip_without_force(tmp_path, monkeypatch):
    root = _root(tmp_path)
    from triggerctl import package

    monkeypatch.setattr(package, "primary", lambda sel: root)
    repo = Path(__file__).resolve().parents[1] / "examples" / "time-daily-backup.md"
    commands.cmd_add_from(str(repo), None, None, False, False)
    rc = commands.cmd_add_from(str(repo), None, None, False, False)
    assert rc == 0
    assert len(discover(root)) == 1


def test_list_from_local_dir(tmp_path):
    from triggerctl import package

    examples = Path(__file__).resolve().parents[1] / "examples"
    files = package.list_available(str(examples))
    names = {f.name for f in files}
    assert "daily-backup" in names
    assert "on-train-done" in names or "on-done" in names or len(names) >= 3
