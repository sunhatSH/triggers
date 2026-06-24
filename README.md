# triggerctl

Triggers for Claude Code, Hermes Agent, and Codex CLI — run commands or prompts on a schedule, when a probe
succeeds, or when a semantic session condition matches. Inspired by
[vercel-labs/skills](https://github.com/vercel-labs/skills) (frontmatter as source
of truth, generated index, multiple registry roots).

## Design

- **Two layers** (latency vs cost):
  - **Detection** (cheap Python, no model): evaluates `schedule` + `probe`, dedups via run-log.
  - **Execution** (model): calls `claude -p`, `hermes chat -q`, or `codex exec` only for DUE triggers.
- **Types inferred from frontmatter**: `schedule` only → time; `probe` only → event;
  both → AND combo; `when` only (no schedule/probe) → semantic session (hook).
- **Source of truth** = each trigger `.md` file; `TRIGGERS.md` is an **ops index**
  (not injected into agent context).
- **Registry roots**:
  - User: `~/.claude/triggers/`
  - Project: `<project>/triggers/`
- **Idempotency**: `.state/run-log.jsonl` keyed by `(name, key)`.
- **Optional templates**: `catalog/` (`session/` + `poll/`); `init` seeds only the locked guardrail.
- **>5 warning**: counts **hook-eligible** session triggers only (`in_context`), not time/event or `inject: false`.

## Project layout

```
triggerctl/              # repo root (GitHub: sunhatSH/triggers)
├── triggerctl/          # Python package + CLI
├── skill/               # agent skill (installed on setup)
├── catalog/             # optional templates
│   ├── session/         # semantic session (hook)
│   └── poll/            # time / event / combo
├── docs/                # design, integrations, proposals, admin
├── tests/               # pytest; tests/manual/ for harnesses
├── install.sh           # pip -e, init, hooks, skill
└── bundled/ examples/   # redirect READMEs → catalog/
```

## Install

```bash
git clone git@github.com:sunhatSH/triggers.git
cd triggers
bash install.sh
```

Installs `triggerctl` on PATH, initializes the user registry, and configures Claude Code,
Hermes Agent, and Codex CLI (default `AGENT=all`). **Start a new session** after install.

```bash
AGENT=claude bash install.sh   # Claude only
AGENT=hermes bash install.sh   # Hermes only
AGENT=codex bash install.sh    # Codex only
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

See [docs/integrations/hermes.md](docs/integrations/hermes.md).

### Codex CLI

```bash
triggerctl install --codex        # hook + skill
triggerctl install --codex-hook   # hook only
```

See [docs/integrations/codex.md](docs/integrations/codex.md).

## Context policy

| Kind | Handler | In agent context? |
|---|---|---|
| time (`schedule`) | `triggerctl poll` | **No** |
| event (`probe`) | `triggerctl poll` | **No** |
| combo | `triggerctl poll` | **No** |
| semantic session (`when` only) | UserPromptSubmit hook (Claude/Codex) / `pre_llm_call` (Hermes) | **Yes** |
| `inject: false` | doctor / statusLine | **No** (rest → 🌙; >5 **context** triggers → ⚠️ in status bar) |

## Docs

- [USAGE.md](USAGE.md) — usage and troubleshooting
- [docs/README.md](docs/README.md) — documentation index
- [docs/design.md](docs/design.md) — architecture
- [catalog/README.md](catalog/README.md) — optional templates
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
| `triggerctl install --codex` | Full Codex setup (hook + skill) |
| `triggerctl install --codex-hook` | Codex UserPromptSubmit hook only |
| `triggerctl hermes-hook` | Hermes hook entrypoint (JSON `context`) |
| `triggerctl codex-hook` | Codex hook entrypoint (JSON `additionalContext`) |
| `triggerctl install --statusline` | Status bar |
| `triggerctl install --loop` | Background poll loop |
| `triggerctl uninstall [--yes]` | Remove hooks/skills + user/project/system triggers |
| `bash uninstall.sh` | Same as `uninstall --root all --yes` |

## Tests

```bash
cd triggers && PYTHONPATH=. python -m pytest -q
python3 tests/manual/test_statusline.py        # statusLine: rest + >5 warning
python3 tests/manual/test_statusline.py --demo # example output lines
```

## Timezone

`export TRIGGERCTL_TZ_OFFSET=8` (default +8). Applies to schedule, poll, hook, statusLine.
