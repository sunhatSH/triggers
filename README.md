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
- **Optional library**: separate [trigger-library](https://github.com/sunhatSH/trigger-library) repo; synced to `~/.local/share/triggerctl/library`. `init` only seeds the locked guardrail.
- **>5 warning**: counts **hook-eligible** session triggers only (`in_context`), not time/event or `inject: false`.

## Project layout

```
triggerctl/              # engine only (GitHub: sunhatSH/triggers)
├── triggerctl/          # Python package + CLI
├── skill/               # agent skill
├── docs/ tests/ install.sh
└── library/README.md    # pointer → separate trigger-library repo

trigger-library/           # separate repo: sunhatSH/trigger-library
├── manifest.yaml
├── session/ poll/
```

## Install

**One line (curl + git):**

```bash
curl -fsSL https://raw.githubusercontent.com/sunhatSH/triggers/main/install-remote.sh | bash
```

Then sync the optional trigger library (not auto-installed into your registry):

```bash
triggerctl fetch
triggerctl list
triggerctl add rest-reminder auto-commit-push --store
```

Clones to `~/.local/share/triggerctl/repo` and runs `install.sh`. Options:

```bash
AGENT=claude curl -fsSL ... | bash
TRIGGERCTL_BRANCH=dev curl -fsSL ... | bash   # before main is updated
PYTHON=/path/to/python3 curl -fsSL ... | bash
```

**From a git clone:**

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
- [trigger-library](https://github.com/sunhatSH/trigger-library) — optional templates (separate repo)
- [skill/SKILL.md](skill/SKILL.md) — agent skill

## Commands

| Command | Purpose |
|---|---|
| `triggerctl fetch [--source SRC]` | Sync store → `~/.local/share/triggerctl/library` |
| `triggerctl list [--root all]` | List installed + store templates (状态: 未安装/已启用/已关闭) |
| `triggerctl add <name> --store` | Install from local store by name |
| `triggerctl init [--root user\|project]` | Initialize registry root |
| `triggerctl add <name> [--every \| --probe \| --when]` | Register trigger |
| `triggerctl add --from <SOURCE> [--list]` | Install from Git/local |
| `triggerctl update` | Update from lock file |
| `triggerctl doctor` | Health check |
| `triggerctl validate [--probe-test]` | Validate frontmatter |
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
