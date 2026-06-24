# Codex CLI integration

triggerctl gives [OpenAI Codex CLI](https://developers.openai.com/codex/) the same trigger
registry and semantics as Claude Code: shared `~/.claude/triggers/` + `<project>/triggers/`,
semantic session injection via hooks, and `triggerctl poll` for time/event triggers.

## One-command install

```bash
cd triggerctl && AGENT=codex bash install.sh
# or after pip install -e:
triggerctl init --root user
triggerctl install --codex
```

This:

1. Registers `UserPromptSubmit` in `~/.codex/hooks.json` (wrapper at `~/.codex/hooks/triggerctl-user-prompt-submit.sh`)
2. Installs the triggerctl skill to `~/.agents/skills/triggerctl/SKILL.md`

Verify:

```bash
triggerctl doctor
codex /hooks   # trust the hook if prompted
```

Start a **new Codex session** after install.

## How it maps to Claude Code

| Feature | Claude Code | Codex CLI |
|---|---|---|
| Session triggers (`when` only) | `UserPromptSubmit` → `triggerctl hook` | `UserPromptSubmit` → `triggerctl codex-hook` |
| Config | `~/.claude/settings.json` | `~/.codex/hooks.json` |
| Skill | `~/.claude/skills/triggerctl/` | `~/.agents/skills/triggerctl/` |
| Project triggers | hook stdin `cwd` | hook stdin `cwd` (same) |
| Time/event triggers | `triggerctl poll` | `triggerctl poll` (same registry) |
| Poll execution | `claude -p` (default) | `codex exec` when `TRIGGERCTL_AGENT=codex` or Codex-only PATH |
| Status bar hints | `triggerctl statusline` | not available — use `triggerctl doctor` |
| Hook trust | settings hook approval | trust via Codex `/hooks` UI |

## Manual test

```bash
echo '{"hook_event_name":"UserPromptSubmit","session_id":"test","cwd":"/path/to/your/project","prompt":"hi"}' \
  | triggerctl codex-hook
# → {"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"[Triggers·…] …"}}
```

Project-scoped session triggers appear only when `cwd` points at that project.

## Poll with Codex

```bash
export TRIGGERCTL_AGENT=codex
triggerctl poll --root all
```

Default exec flags: `--sandbox workspace-write --ask-for-approval never`. Override:

```bash
export TRIGGERCTL_CODEX_EXEC_ARGS="--sandbox read-only --ask-for-approval never"
```

Auto-detect: if only `codex` is on PATH (no `claude` or `hermes`), poll uses Codex automatically.

## Hook-only install

```bash
triggerctl install --codex-hook   # hook only, no skill copy
```

## Hook trust

Codex requires you to review and trust shell hooks before they run. After install, open `/hooks`
in the Codex TUI and trust `triggerctl-user-prompt-submit.sh`, or run once with
`--dangerously-bypass-hook-trust` for automation outside the TUI.
