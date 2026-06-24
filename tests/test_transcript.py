"""Tests for experimental transcript replacement."""
import json

from triggerctl import hook_runner, transcript
from triggerctl.hookgen import TRIGGER_BLOCK_PREFIX


def test_filter_transcript_lines():
    lines = [
        '{"type":"user","message":"hello"}\n',
        f'{{"type":"system","text":"{TRIGGER_BLOCK_PREFIX}UTC+8 12:00]"}}\n',
        '{"type":"assistant","message":"ok"}\n',
    ]
    kept, removed = transcript.filter_transcript_lines(lines)
    assert removed == 1
    assert len(kept) == 2
    assert TRIGGER_BLOCK_PREFIX not in "".join(kept)


def test_strip_prior_injections(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text(
        '{"turn":1,"content":"hello"}\n'
        f'{{"turn":2,"content":"{TRIGGER_BLOCK_PREFIX}UTC+8 10:00] old"}}\n'
        '{"turn":3,"content":"user prompt"}\n',
        encoding="utf-8",
    )
    removed = transcript.strip_prior_injections(path)
    assert removed == 1
    text = path.read_text(encoding="utf-8")
    assert TRIGGER_BLOCK_PREFIX not in text
    assert "hello" in text
    assert transcript.validate_jsonl(path)


def test_hook_runner_json_replace_mode(tmp_path, monkeypatch, capsys):
    from triggerctl import hookgen
    from triggerctl.roots import Root

    root = Root("project", tmp_path / "triggers")
    root.path.mkdir(parents=True)
    (root.path / "t.md").write_text(
        "---\nname: t\nenabled: true\nwhen: on request\n---\n\nbody\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(hookgen, "all_roots", lambda: [root])
    monkeypatch.setenv("TRIGGERCTL_HOOK_REPLACE", "1")
    monkeypatch.setenv("TRIGGERCTL_HOOK_JSON", "1")

    tpath = tmp_path / "session.jsonl"
    tpath.write_text(
        f'{{"x":"{TRIGGER_BLOCK_PREFIX}UTC+8 09:00] stale"}}\n',
        encoding="utf-8",
    )
    hook_runner.run_user_prompt_submit({"transcript_path": str(tpath)})
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["hookSpecificOutput"]["replacesPrevious"] is True
    assert "t" in data["hookSpecificOutput"]["additionalContext"]
    assert TRIGGER_BLOCK_PREFIX not in tpath.read_text(encoding="utf-8")
