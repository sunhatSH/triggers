# triggerctl

Triggers for Claude Code, Hermes Agent, and Codex CLI — run commands or prompts on a schedule, when a probe
succeeds, or when a semantic session condition matches. Inspired by
[vercel-labs/skills](https://github.com/vercel-labs/skills) (frontmatter as source
of truth, generated index, multiple registry roots).

## Quick start

**One line (curl + git):**

```bash
curl -fsSL https://raw.githubusercontent.com/sunhatSH/triggers/main/install-remote.sh | bash
```

Then install optional triggers from the library:

```bash
triggerctl list
triggerctl install rest-reminder auto-commit-push
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
triggerctl install --codex         # hook + skill
triggerctl install --codex-hook    # hook only
```

See [docs/integrations/codex.md](docs/integrations/codex.md).

## Docs

- [USAGE.md](USAGE.md) — command reference
- [docs/design.md](docs/design.md) — architecture
- [trigger-library](https://github.com/sunhatSH/trigger-library) — optional templates (separate repo)
- [skill/SKILL.md](skill/SKILL.md) — agent skill

## Commands

| Command | Purpose |
|---|---|
| `triggerctl install <name>` | Install trigger from template library (auto-syncs on first use) |
| `triggerctl install <name> --from PATH` | Install from GitHub / git URL / local path |
| `triggerctl install --all` | Install all from local default library (auto-syncs on first use) |
| `triggerctl install --all --from PATH` | Install all triggers under PATH |
| `triggerctl install --hook` / `--loop` / … | Agent integration (hooks, poll loop, statusLine) |
| `triggerctl list [--root all]` | List installed + store templates (状态: 未安装/已启用/已关闭) |
| `triggerctl add <name> [--when \| --probe \| --every]` | Create a new trigger |
| `triggerctl enable/disable <name>` | Toggle installed trigger |
| `triggerctl init [--root user\|project]` | Initialize registry root |
| `triggerctl update` | Update from lock file |
| `triggerctl doctor` | Health check |
| `triggerctl validate [--probe-test]` | Validate frontmatter |
| `triggerctl sync` | Regenerate TRIGGERS.md ops index |
| `triggerctl detect` / `poll` | Detection / execution |
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
