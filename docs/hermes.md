# Hermes Agent integration

triggerctl gives [Hermes Agent](https://hermes-agent.nousresearch.com/) the same trigger
registry and semantics as Claude Code: shared `~/.claude/triggers/` + `<project>/triggers/`,
semantic session injection via hooks, and `triggerctl poll` for time/event triggers.

## One-command install

```bash
cd triggerctl && AGENT=hermes bash install.sh
# or after pip install -e:
triggerctl init --root user
triggerctl install --hermes
```

This:

1. Registers `pre_llm_call` in `~/.hermes/config.yaml` (wrapper at `~/.hermes/agent-hooks/triggerctl-pre-llm.sh`)
2. Installs the triggerctl skill to `~/.hermes/skills/triggerctl/SKILL.md`
3. Sets `hooks_auto_accept: true` when not already configured

Verify:

```bash
hermes hooks doctor
triggerctl doctor
```

Start a **new Hermes session** after install.

## How it maps to Claude Code

| Feature | Claude Code | Hermes Agent |
|---|---|---|
| Session triggers (`when` only) | `UserPromptSubmit` → `triggerctl hook` | `pre_llm_call` → `triggerctl hermes-hook` |
| Config | `~/.claude/settings.json` | `~/.hermes/config.yaml` |
| Skill | `~/.claude/skills/triggerctl/` | `~/.hermes/skills/triggerctl/` |
| Project triggers | uses hook stdin `cwd` | uses hook stdin `cwd` (same) |
| Time/event triggers | `triggerctl poll` | `triggerctl poll` (same registry) |
| Poll execution | `claude -p` (default) | `hermes chat -q` when `TRIGGERCTL_AGENT=hermes` or Hermes-only PATH |
| Status bar hints (rest, >20) | `triggerctl statusline` | not available — use `triggerctl doctor` |
| Hook replace experiment | `TRIGGERCTL_HOOK_REPLACE` | N/A (Hermes prepends per turn) |

## Manual test

```bash
echo '{"hook_event_name":"pre_llm_call","session_id":"test","cwd":"/path/to/your/project"}' \
  | triggerctl hermes-hook
# → {"context": "[Triggers·UTC+8 …] …"}  or {}
```

Project-scoped session triggers appear only when `cwd` points at that project (same as Claude).

## Poll with Hermes

```bash
export TRIGGERCTL_AGENT=hermes   # force hermes chat -q for DUE triggers
triggerctl poll --root all
```

Auto-detect: if only `hermes` is on PATH (no `claude`), poll uses Hermes automatically.

## Hook-only install

```bash
triggerctl install --hermes-hook   # hook only, no skill copy
```
