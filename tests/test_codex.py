"""Tests for Codex CLI integration."""
import json

from triggerctl import codex, hook_runner


def test_codex_hook_json_output(capsys):
    hook_runner.run_codex_hook({"hook_event_name": "UserPromptSubmit", "cwd": "/tmp"})
    out = capsys.readouterr().out.strip()
    if not out:
        return
    data = json.loads(out)
    assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "additionalContext" in data["hookSpecificOutput"]


def test_install_user_prompt_hook_idempotent(tmp_path, monkeypatch):
    hooks_path = tmp_path / "hooks.json"
    monkeypatch.setattr(codex, "hooks_json_path", lambda: hooks_path)
    monkeypatch.setattr(codex, "hooks_dir", lambda: tmp_path / "hooks")

    path1 = codex.install_user_prompt_hook("/usr/bin/triggerctl")
    assert path1 == hooks_path
    _, data = codex.load_hooks(hooks_path)
    assert codex.hook_installed(data)
    assert len(codex._user_prompt_submit_groups(data)) == 1
    wrapper = tmp_path / "hooks" / "triggerctl-user-prompt-submit.sh"
    assert wrapper.is_file()

    path2 = codex.install_user_prompt_hook("/usr/bin/triggerctl")
    _, data2 = codex.load_hooks(hooks_path)
    assert len(codex._user_prompt_submit_groups(data2)) == 1
    assert path2 == hooks_path


def test_install_full_writes_skill(tmp_path, monkeypatch):
    hooks_path = tmp_path / "hooks.json"
    skill_src = tmp_path / "SKILL.md"
    skill_src.write_text("# triggerctl skill\n", encoding="utf-8")
    monkeypatch.setattr(codex, "hooks_json_path", lambda: hooks_path)
    monkeypatch.setattr(codex, "hooks_dir", lambda: tmp_path / "hooks")
    monkeypatch.setattr(codex, "skill_path", lambda: tmp_path / "skills" / "triggerctl" / "SKILL.md")

    result = codex.install_full("/usr/bin/triggerctl", skill_src)
    assert result["hooks"] == hooks_path
    assert (tmp_path / "skills" / "triggerctl" / "SKILL.md").read_text() == "# triggerctl skill\n"
