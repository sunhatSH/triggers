"""Tests for Hermes Agent integration."""
import json
from pathlib import Path

from triggerctl import hermes, hook_runner
from triggerctl.roots import Root


def test_hermes_hook_json_output(capsys):
    hook_runner.run_pre_llm_call({"hook_event_name": "pre_llm_call"})
    out = capsys.readouterr().out.strip()
    data = json.loads(out or "{}")
    assert "context" in data or data == {}


def test_hermes_hook_uses_cwd_for_project_triggers(tmp_path, capsys, monkeypatch):
    home = tmp_path / "home"
    proj = tmp_path / "proj"
    triggers = proj / "triggers" / "demo-triggers"
    triggers.mkdir(parents=True)
    (triggers / "proj-only.md").write_text(
        "---\nname: proj-only\nenabled: true\nwhen: always match\n---\n\nbody\n",
        encoding="utf-8",
    )
    (home / ".claude" / "triggers").mkdir(parents=True)

    import triggerctl.roots as roots_mod

    monkeypatch.setattr(roots_mod, "user_root", lambda: Root("user", home / ".claude" / "triggers"))

    hook_runner.run_pre_llm_call({"cwd": str(proj), "hook_event_name": "pre_llm_call"})
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert "proj-only" in data.get("context", "")


def test_hook_cwd_from_workspace():
    p = hook_runner.hook_cwd({"workspace": {"current_dir": "/tmp/ws"}})
    assert p == Path("/tmp/ws")


def test_install_pre_llm_hook_idempotent(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    monkeypatch.setattr(hermes, "config_path", lambda: cfg)
    monkeypatch.setattr(hermes, "agent_hooks_dir", lambda: tmp_path / "agent-hooks")

    path1 = hermes.install_pre_llm_hook("/usr/bin/triggerctl")
    assert path1 == cfg
    assert cfg.exists()
    _, data = hermes.load_config(cfg)
    assert hermes.hook_installed(data)
    assert len(hermes._pre_llm_entries(data)) == 1
    wrapper = tmp_path / "agent-hooks" / "triggerctl-pre-llm.sh"
    assert wrapper.is_file()

    path2 = hermes.install_pre_llm_hook("/usr/bin/triggerctl")
    _, data2 = hermes.load_config(cfg)
    assert len(hermes._pre_llm_entries(data2)) == 1
    assert path2 == cfg


def test_install_full_writes_skill(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    skill_src = tmp_path / "SKILL.md"
    skill_src.write_text("# triggerctl skill\n", encoding="utf-8")
    monkeypatch.setattr(hermes, "config_path", lambda: cfg)
    monkeypatch.setattr(hermes, "agent_hooks_dir", lambda: tmp_path / "agent-hooks")
    monkeypatch.setattr(hermes, "skill_path", lambda: tmp_path / "skills" / "triggerctl" / "SKILL.md")

    result = hermes.install_full("/usr/bin/triggerctl", skill_src)
    assert result["config"] == cfg
    assert (tmp_path / "skills" / "triggerctl" / "SKILL.md").read_text() == "# triggerctl skill\n"
    _, data = hermes.load_config(cfg)
    assert data.get("hooks_auto_accept") is True


def test_build_hermes_output():
    raw = hook_runner.build_hermes_output("[Triggers·test]")
    assert json.loads(raw) == {"context": "[Triggers·test]"}
