"""Agent runtime detection and headless execution."""
from unittest.mock import patch

from triggerctl.agents import build_prompt, preferred_agent, run_prompt


def test_preferred_agent_env(monkeypatch):
    monkeypatch.setenv("TRIGGERCTL_AGENT", "hermes")
    assert preferred_agent() == "hermes"
    monkeypatch.setenv("TRIGGERCTL_AGENT", "claude")
    assert preferred_agent() == "claude"
    monkeypatch.setenv("TRIGGERCTL_AGENT", "codex")
    assert preferred_agent() == "codex"


def test_run_prompt_dry_run():
    res = run_prompt("hi", __import__("pathlib").Path("/tmp"), dry_run=True)
    assert res.ok and "dry-run" in res.detail


def test_build_prompt_includes_name():
    p = build_prompt("my-trigger", "do the thing")
    assert "my-trigger" in p
    assert "do the thing" in p


def test_run_hermes_invocation(monkeypatch):
    from pathlib import Path

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs.get("cwd")))
        class R:
            returncode = 0
            stdout = "done"
            stderr = ""
        return R()

    monkeypatch.setenv("TRIGGERCTL_HERMES", "/usr/bin/hermes")
    monkeypatch.setattr("triggerctl.agents.subprocess.run", fake_run)
    res = run_prompt("test", Path("/proj"), agent="hermes")
    assert res.ok
    assert calls[0][0][:3] == ["/usr/bin/hermes", "chat", "-q"]
    assert calls[0][1] == "/proj"


def test_run_codex_invocation(monkeypatch):
    from pathlib import Path

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs.get("cwd")))
        class R:
            returncode = 0
            stdout = "done"
            stderr = ""
        return R()

    monkeypatch.setenv("TRIGGERCTL_CODEX", "/usr/bin/codex")
    monkeypatch.setattr("triggerctl.agents.subprocess.run", fake_run)
    res = run_prompt("test", Path("/proj"), agent="codex")
    assert res.ok
    assert calls[0][0][:2] == ["/usr/bin/codex", "exec"]
    assert "--sandbox" in calls[0][0]
    assert calls[0][1] == "/proj"
