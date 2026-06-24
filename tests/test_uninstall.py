"""Tests for triggerctl uninstall."""
import json
from pathlib import Path

import yaml

from triggerctl import commands, uninstall
from triggerctl.roots import Root


def _write_claude_settings(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "triggerctl hook"}]}
                    ]
                },
                "statusLine": {"type": "command", "command": "triggerctl statusline"},
                "env": {"TRIGGERCTL_HOOK_REPLACE": "1", "TRIGGERCTL_TZ_OFFSET": "8"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _seed_triggers(root: Root) -> None:
    system = root.path / "system-triggers" / "guard.md"
    system.parent.mkdir(parents=True, exist_ok=True)
    system.write_text("---\nname: guard\nenabled: true\nwhen: test\n---\n\nbody\n", encoding="utf-8")
    userish = root.path / "git-triggers" / "auto.md"
    userish.parent.mkdir(parents=True, exist_ok=True)
    userish.write_text("---\nname: auto\nenabled: true\nwhen: test\n---\n\nbody\n", encoding="utf-8")
    root.index_file.write_text("# TRIGGERS\n", encoding="utf-8")


def test_uninstall_requires_yes(tmp_path, monkeypatch, capsys):
    root = Root("project", tmp_path / "triggers")
    _seed_triggers(root)
    monkeypatch.setattr("triggerctl.commands.resolve", lambda sel: [root])
    rc = commands.cmd_uninstall(None, agents="all", yes=False, dry_run=False, keep_triggers=False, triggers_only=False)
    assert rc == 1
    assert root.path.exists()
    err = capsys.readouterr().err
    assert "system-triggers" in err


def test_uninstall_removes_all_trigger_roots(tmp_path, monkeypatch):
    user = Root("user", tmp_path / "home" / ".claude" / "triggers")
    project = Root("project", tmp_path / "proj" / "triggers")
    _seed_triggers(user)
    _seed_triggers(project)
    monkeypatch.setattr("triggerctl.commands.resolve", lambda sel: [user, project])

    rep = uninstall.run_uninstall(
        roots=[user, project],
        agents="all",
        remove_triggers=True,
        remove_integration=False,
        dry_run=False,
    )
    assert not user.path.exists()
    assert not project.path.exists()
    assert any("system-triggers" in line for line in rep.removed)


def test_uninstall_claude_settings(tmp_path, monkeypatch):
    settings = tmp_path / ".claude" / "settings.json"
    _write_claude_settings(settings)
    skill = tmp_path / ".claude" / "skills" / "triggerctl" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("skill", encoding="utf-8")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    rep = uninstall.UninstallReport()
    uninstall.uninstall_claude(rep)

    data = json.loads(settings.read_text(encoding="utf-8"))
    ups = data.get("hooks", {}).get("UserPromptSubmit", [])
    assert not any("triggerctl hook" in str(h.get("command", "")) for g in ups for h in g.get("hooks", []))
    assert "statusLine" not in data
    assert "TRIGGERCTL_HOOK_REPLACE" not in data.get("env", {})
    assert not skill.parent.exists()


def test_uninstall_hermes_config(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "hooks": {
                    "pre_llm_call": [
                        {"command": str(tmp_path / "triggerctl-pre-llm.sh"), "timeout": 30}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    wrapper = tmp_path / "agent-hooks" / "triggerctl-pre-llm.sh"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(uninstall.hermes, "config_path", lambda: cfg)
    monkeypatch.setattr(uninstall.hermes, "load_config", lambda path=None: (cfg, yaml.safe_load(cfg.read_text())))
    monkeypatch.setattr(uninstall.hermes, "agent_hooks_dir", lambda: tmp_path / "agent-hooks")
    monkeypatch.setattr(uninstall.hermes, "skill_path", lambda: tmp_path / "skills" / "triggerctl" / "SKILL.md")

    rep = uninstall.UninstallReport()
    uninstall.uninstall_hermes(rep)

    data = yaml.safe_load(cfg.read_text())
    assert "pre_llm_call" not in data.get("hooks", {})
    assert not wrapper.exists()


def test_uninstall_codex_hooks(tmp_path, monkeypatch):
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": str(tmp_path / "triggerctl-user-prompt-submit.sh"),
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    wrapper = tmp_path / "hooks" / "triggerctl-user-prompt-submit.sh"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(uninstall.codex, "hooks_json_path", lambda: hooks_path)
    monkeypatch.setattr(uninstall.codex, "load_hooks", lambda path=None: (hooks_path, json.loads(hooks_path.read_text())))
    monkeypatch.setattr(uninstall.codex, "hooks_dir", lambda: tmp_path / "hooks")
    monkeypatch.setattr(uninstall.codex, "skill_path", lambda: tmp_path / "skills" / "triggerctl" / "SKILL.md")

    rep = uninstall.UninstallReport()
    uninstall.uninstall_codex(rep)

    data = json.loads(hooks_path.read_text())
    assert "UserPromptSubmit" not in data.get("hooks", {})
    assert not wrapper.exists()


def test_uninstall_dry_run_keeps_files(tmp_path, monkeypatch):
    root = Root("user", tmp_path / "triggers")
    _seed_triggers(root)
    monkeypatch.setattr("triggerctl.commands.resolve", lambda sel: [root])
    rc = commands.cmd_uninstall(None, agents="claude", yes=False, dry_run=True, keep_triggers=False, triggers_only=False)
    assert rc == 0
    assert root.path.exists()
