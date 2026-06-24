"""Tests for triggerctl doctor."""
from triggerctl import commands, doctor
from triggerctl.roots import Root


def _root(tmp_path):
    return Root("project", tmp_path / "triggers")


def test_doctor_on_fresh_root(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_init(None)
    rep = doctor.run(tmp_path)
    assert any(c.name == "triggerctl binary" for c in rep.checks)


def test_doctor_cmd(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_init(None)
    rc = commands.cmd_doctor(tmp_path)
    out = capsys.readouterr().out
    assert "triggerctl doctor" in out
    assert rc in (0, 1)
