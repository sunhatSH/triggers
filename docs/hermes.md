# Hermes Agent integration

triggerctl injects **semantic session triggers** into [Hermes Agent](https://hermes-agent.nousresearch.com/) via the `pre_llm_call` shell hook — the Hermes equivalent of Claude Code's `UserPromptSubmit`.

## Install

```bash
triggerctl init --root user
triggerctl install --hermes-hook
```

This appends to `~/.hermes/config.yaml`:

```yaml
hooks:
  pre_llm_call:
    - command: triggerctl hermes-hook
      timeout: 30
```

On first run Hermes prompts for hook consent. Non-interactive use:

```bash
export HERMES_ACCEPT_HOOKS=1
# or set hooks_auto_accept: true in config.yaml
```

Verify:

```bash
hermes hooks doctor
triggerctl doctor
```

## Manual test

```bash
echo '{"hook_event_name":"pre_llm_call","session_id":"test","cwd":"/tmp"}' | triggerctl hermes-hook
# → {"context": "[Triggers·UTC+8 …] …"}  or {}
```

## Claude Code vs Hermes

| | Claude Code | Hermes Agent |
|---|---|---|
| Event | `UserPromptSubmit` | `pre_llm_call` |
| Config | `~/.claude/settings.json` | `~/.hermes/config.yaml` |
| Command | `triggerctl hook` | `triggerctl hermes-hook` |
| Output | JSON `additionalContext` or plain text | JSON `{"context": "…"}` |
| Replace mode | `TRIGGERCTL_HOOK_REPLACE` (experimental) | not applicable (Hermes prepends per turn) |
| Status bar | `triggerctl statusline` | not supported (Claude Code only) |
| Poll (time/event) | `triggerctl poll` | same |

Both agents share the same trigger registry (`~/.claude/triggers/`, `<project>/triggers/`).
