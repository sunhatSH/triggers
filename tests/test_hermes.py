"""Tests for Hermes Agent integration."""
import json

from triggerctl import hermes, hook_runner


def test_hermes_hook_json_output(capsys):
    hook_runner.run_pre_llm_call({"hook_event_name": "pre_llm_call"})
    out = capsys.readouterr().out.strip()
    # empty or object with context key
    data = json.loads(out or "{}")
    assert "context" in data or data == {}


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

    path2 = hermes.install_pre_llm_hook("/usr/bin/triggerctl")
    _, data2 = hermes.load_config(cfg)
    assert len(hermes._pre_llm_entries(data2)) == 1
    assert path2 == cfg


def test_build_hermes_output():
    raw = hook_runner.build_hermes_output("[Triggers·test]")
    assert json.loads(raw) == {"context": "[Triggers·test]"}
