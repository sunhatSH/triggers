# Architecture

Current design (English). For the original Chinese proposal with older CLAUDE.md injection
model, see [archive/design-v1-zh.md](archive/design-v1-zh.md).

## Layers

1. **Detection** (Python, no model): evaluates `schedule` + `probe`, dedups via run-log.
2. **Execution** (model): `claude -p`, `hermes chat -q`, or `codex exec` only for DUE triggers.

## Trigger kinds (inferred from frontmatter)

| Fields | Kind | Handler | In agent context? |
|---|---|---|---|
| `schedule` only | time | `triggerctl poll` | No |
| `probe` only | event | `triggerctl poll` | No |
| `schedule` + `probe` | combo (AND) | `triggerctl poll` | No |
| `when` only | semantic session | hook each user turn | Yes (if `inject: true`) |
| `inject: false` | guardrail / statusLine | doctor / statusLine | No |

## Registry

- **Source of truth**: each trigger `.md` file under a registry root.
- **Ops index**: `TRIGGERS.md` (generated; not injected into context).
- **Roots**: user `~/.claude/triggers/`, project `<repo>/triggers/`.
- **Idempotency**: `.state/run-log.jsonl` keyed by `(name, key)`.

## Repo layout

```
triggerctl/          # Python package + CLI
skill/               # Agent skill (installed to ~/.claude/skills/triggerctl/)
library/             # Optional trigger library (manifest.yaml; not auto-installed)
docs/                # This tree
tests/               # pytest + tests/manual/
install.sh           # pip -e, init, hooks, skill copy
```

## Agents

| Agent | Session hook | Poll execution |
|---|---|---|
| Claude Code | `UserPromptSubmit` → `triggerctl hook` | `claude -p` |
| Hermes | `pre_llm_call` → `triggerctl hermes-hook` | `hermes chat -q` |
| Codex | `UserPromptSubmit` → `triggerctl codex-hook` | `codex exec` |

See [integrations/hermes.md](integrations/hermes.md) and [integrations/codex.md](integrations/codex.md).
