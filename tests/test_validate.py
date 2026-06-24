from triggerctl import commands, validate
from triggerctl.model import discover
from triggerctl.roots import Root


def _root(tmp_path):
    return Root("project", tmp_path / "triggers")


def test_validate_ok_trigger(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    monkeypatch.setattr(commands, "resolve", lambda sel: [root])
    commands.cmd_add("daily", None, None, "day", "14:30", None, None,
                     None, None, None, False, False)
    rep = validate.validate_roots([root])
    assert rep.ok
    assert not any(i.level == "error" for i in rep.issues)


def test_validate_invalid_schedule(tmp_path, monkeypatch):
    root = _root(tmp_path)
    root.path.mkdir(parents=True)
    (root.path / "bad.md").write_text(
        "---\nname: bad\nenabled: true\nschedule:\n  every: never\n---\n\nbody\n",
        encoding="utf-8",
    )
    rep = validate.validate_roots([root])
    assert not rep.ok
    assert any("schedule" in i.message for i in rep.issues)


def test_validate_duplicate_names(tmp_path, monkeypatch):
    root = _root(tmp_path)
    root.path.mkdir(parents=True)
    for n in ("a-triggers/x.md", "b-triggers/y.md"):
        p = root.path / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("---\nname: dup\nenabled: true\nprobe: 'true'\n---\n\nok\n", encoding="utf-8")
    rep = validate.validate_roots([root])
    assert not rep.ok
    assert any("重复" in i.message for i in rep.issues)


def test_validate_cmd(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path)
    monkeypatch.setattr(commands, "resolve", lambda sel: [root])
    monkeypatch.setattr(commands, "primary", lambda sel: root)
    commands.cmd_init(None)
    rc = commands.cmd_validate(None, False)
    out = capsys.readouterr().out
    assert "validate" in out
    assert rc in (0, 1)
