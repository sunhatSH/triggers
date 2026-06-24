# triggerctl

Triggers for Claude Code and Hermes Agent — run commands or prompts on a schedule, when a probe
succeeds, or when a semantic session condition matches. Inspired by
[vercel-labs/skills](https://github.com/vercel-labs/skills) (frontmatter as source
of truth, generated index, multiple registry roots).

## Design

- **Two layers** (latency vs cost):
  - **Detection** (cheap Python, no model): evaluates `schedule` + `probe`, dedups via run-log.
  - **Execution** (model): calls `claude -p` or `hermes chat -q` only for DUE triggers.
- **Types inferred from frontmatter**: `schedule` only → time; `probe` only → event;
  both → AND combo; `when` only (no schedule/probe) → semantic session (hook).
- **Source of truth** = each trigger `.md` file; `TRIGGERS.md` is an **ops index**
  (not injected into agent context).
- **Registry roots**:
  - User: `~/.claude/triggers/`
  - Project: `<project>/triggers/`
- **Idempotency**: `.state/run-log.jsonl` keyed by `(name, key)`.

## Install

```bash
cd triggers && bash install.sh
```

Installs `triggerctl` on PATH, initializes the user registry, and configures Claude Code
and Hermes Agent (default `AGENT=all`). **Start a new session** after install.

```bash
AGENT=claude bash install.sh   # Claude only
AGENT=hermes bash install.sh   # Hermes only
```

If `pip` is missing, `install.sh` uses `/opt/conda/bin/python3 -m pip`.

### Experimental: latest-only hook injection

Add to `~/.claude/settings.json`:

```json
"env": {
  "TRIGGERCTL_HOOK_REPLACE": "1",
  "TRIGGERCTL_HOOK_JSON": "1"
}
```

Strips prior trigger blocks from the session transcript before each injection.
See [docs/proposals/user-prompt-submit-replacement-context.md](docs/proposals/user-prompt-submit-replacement-context.md).

### Hermes Agent

```bash
triggerctl install --hermes        # hook + skill + hooks_auto_accept
triggerctl install --hermes-hook   # hook only
```

See [docs/hermes.md](docs/hermes.md).

## Context policy

| Kind | Handler | In agent context? |
|---|---|---|
| time (`schedule`) | `triggerctl poll` | **No** |
| event (`probe`) | `triggerctl poll` | **No** |
| combo | `triggerctl poll` | **No** |
| semantic session (`when` only) | UserPromptSubmit hook (Claude) / `pre_llm_call` (Hermes) | **Yes** |
| `inject: false` | doctor / statusLine | **No** (rest → 🌙; >20 triggers → ⚠️ in status bar) |

## Docs

- [USAGE.md](USAGE.md) — usage and troubleshooting
- [docs/design.md](docs/design.md) — design notes
- [docs/proposals/user-prompt-submit-replacement-context.md](docs/proposals/user-prompt-submit-replacement-context.md) — upstream PR proposal
- [examples/](examples/) — templates
- [skill/SKILL.md](skill/SKILL.md) — agent skill

## Commands

| Command | Purpose |
|---|---|
| `triggerctl init [--root user\|project]` | Initialize registry root |
| `triggerctl add <name> [--every \| --probe \| --when]` | Register trigger |
| `triggerctl add --from <SOURCE> [--list]` | Install from Git/local |
| `triggerctl update` | Update from lock file |
| `triggerctl doctor` | Health check |
| `triggerctl validate [--probe-test]` | Validate frontmatter |
| `triggerctl list [--root all]` | List triggers |
| `triggerctl sync` | Regenerate TRIGGERS.md ops index |
| `triggerctl detect` / `poll` | Detection / execution |
| `triggerctl install --hook` | Claude Code UserPromptSubmit injection |
| `triggerctl install --hermes` | Full Hermes setup (hook + skill) |
| `triggerctl install --hermes-hook` | Hermes pre_llm_call hook only |
| `triggerctl hermes-hook` | Hermes hook entrypoint (JSON `context`) |
| `triggerctl install --statusline` | Status bar |
| `triggerctl install --loop` | Background poll loop |
| `triggerctl uninstall [--yes]` | Remove hooks/skills + user/project/system triggers |
| `bash uninstall.sh` | Same as `uninstall --root all --yes` |

## Tests

```bash
cd triggerctl && PYTHONPATH=. python -m pytest -q
python3 scripts/test-statusline.py        # statusLine: rest + >20 warning
python3 scripts/test-statusline.py --demo # example output lines
```

## Timezone

`export TRIGGERCTL_TZ_OFFSET=8` (default +8). Applies to schedule, poll, hook, statusLine.
