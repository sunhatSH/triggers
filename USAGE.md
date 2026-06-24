# triggerctl usage

Embed **triggers** into Claude Code, Hermes Agent, and Codex CLI: run a prompt when a **schedule** fires,
a **shell probe** succeeds, or a **semantic session condition** matches.

## Install

```bash
git clone git@github.com:sunhatSH/triggers.git
cd triggers
bash install.sh
```

`install.sh` installs `triggerctl` on PATH, initializes the user registry (including the default
system guardrail trigger), installs the skill, and writes agent hooks. Default `AGENT=all`
configures Claude Code, Hermes, and Codex. Default `AGENT=all`.

```bash
AGENT=claude bash install.sh   # Claude only
AGENT=hermes bash install.sh   # Hermes only
AGENT=codex bash install.sh    # Codex only
```

**Start a new agent session** after install.

> Many hosts lack a bare `pip` command. Prefer `bash install.sh`, or:
> ```bash
> PYTHON=/opt/conda/bin/python3 bash install.sh
> ```

Hermes-only setup after a manual pip install:

```bash
triggerctl init --root user
triggerctl install --hermes
```

See [docs/integrations/hermes.md](docs/integrations/hermes.md) for Hermes details.

Codex-only setup after a manual pip install:

```bash
triggerctl init --root user
triggerctl install --codex
```

See [docs/integrations/codex.md](docs/integrations/codex.md) for Codex details.

## Trigger types

| Type | frontmatter | When it fires | Who evaluates |
|---|---|---|---|
| `time` | `schedule` (`every` / `at` / `on`) | On schedule | `triggerctl poll` (cheap detection layer) |
| `event` | `probe` (shell exits 0) | When probe succeeds | `triggerctl poll` |
| `session` | `when` (natural language) | Agent judges semantics | **In-session** (hook injects conditions each turn) |

- `schedule` + `probe` together = **combo** (AND).
- `locked: true` = cannot be disabled or removed with `disable` / `remove`.
- `inject: false` = registered but **not** injected into model context (e.g. rest reminder → statusLine only).
- **>5 warning** (statusLine / doctor) counts **hook-eligible** session triggers only — not time/event or `inject: false`.

## Registry roots

| Scope | Path | Notes |
|---|---|---|
| User | `~/.claude/triggers/` | Global, all projects |
| Project | `<project>/triggers/` | Committed with the repo |
| System | `~/.claude/triggers/system-triggers/` | Guardrails (e.g. `too-many-triggers-warning`; only this one is seeded on `init`) |
| Library | `~/.local/share/triggerctl/library` | Auto-synced on first `triggerctl install <name>` from [trigger-library](https://github.com/sunhatSH/trigger-library) |

`TRIGGERS.md` is an **ops index only** — not injected into agent context.

## Two ways to work

**A. Natural language** (the `triggerctl` skill lets the agent register for you):

> "Register a trigger that runs a backup every day at 14:30" / "Commit when I finish a feature" / "List or disable trigger X"

**B. CLI**:

```bash
triggerctl list [--root all|user|project]
triggerctl install <name> [name...] [--root user]   # from template library (enabled by default)
triggerctl install <name> --from <PATH>             # from GitHub / git URL / local path
triggerctl install --all [--root user]                  # all in local default library
triggerctl install --all --from <PATH> [--root user]    # all under PATH
triggerctl install --from <PATH> --list             # preview triggers at PATH
triggerctl add <name> --root user [options]         # create new trigger (see below)
triggerctl enable / disable <name>                  # toggle installed trigger
triggerctl remove <name>
triggerctl update [--root user] [--force]
triggerctl doctor
triggerctl validate [--probe-test]
triggerctl detect
triggerctl poll [--dry-run]
triggerctl status -n 20
triggerctl sync
triggerctl install --hook / --loop / --statusline   # agent integration (not triggers)
```

Install from the template library:

```bash
triggerctl list
triggerctl install rest-reminder auto-commit-push --root user
triggerctl install rest-reminder --from sunhatSH/trigger-library
triggerctl install --all --from sunhatSH/trigger-library --root user
triggerctl install --from /path/to/trigger-library/session/rest-reminder.md
triggerctl update --root user
```

`PATH`: `owner/repo[/path]`, git URL, local directory, or a single `.md`. Installs are recorded in `triggers-lock.json`.

Registration examples:

```bash
triggerctl add nightly  --root user --category ops   --every day --at 02:00
triggerctl add on-done  --root user --category watch \
  --probe 'test -f /data/done.flag' --dedup-cmd 'stat -c %Y /data/done.flag'
triggerctl add commit   --root user --category git   --when 'When I finish a feature: small=commit only, large=commit and push'
triggerctl add guard    --root user --when '...' --locked
```

After `add`, **edit the generated `.md` body** with clear action steps for the model.

## Making time/event triggers run automatically

Session triggers rely on the in-session hook. Time and event triggers need a background poll loop:

```bash
triggerctl install --root user --loop --interval 60
nohup ~/.claude/triggers/run-loop.sh 60 >/dev/null 2>&1 &
# or print a crontab line:
triggerctl install --root user --cron
```

Poll execution uses `claude -p` by default, `hermes chat -q` when `TRIGGERCTL_AGENT=hermes`,
or `codex exec` when `TRIGGERCTL_AGENT=codex` (or auto-detect when only that CLI is on PATH).

## How embedding works

| Kind | Mechanism | In model context? |
|---|---|---|
| time / event / combo | `triggerctl poll` | **No** |
| semantic session (`when` only) | Claude/Codex `UserPromptSubmit` / Hermes `pre_llm_call` | **Yes** |
| `inject: false` | `triggerctl doctor` / Claude statusLine | **No** |

Claude Code:

1. **`install --hook`** — injects session trigger conditions each user turn (uses hook stdin `cwd` for project triggers).
2. **`install --statusline`** — deterministic status bar (rest window 🌙, >5 context triggers ⚠️).
3. Optional **`TRIGGERCTL_HOOK_REPLACE=1`** — experimental latest-only injection (see [docs/proposals/user-prompt-submit-replacement-context.md](docs/proposals/user-prompt-submit-replacement-context.md)).

Hermes:

1. **`install --hermes`** — `pre_llm_call` hook + skill (same registry and session semantics as Claude).

Codex:

1. **`install --codex`** — `UserPromptSubmit` hook + skill (trust hook via Codex `/hooks` if prompted).

Changing hooks, skills, or agent config requires a **new agent session**. Editing trigger `.md` files is picked up on the **next message** (hook rescans disk).

## Troubleshooting

1. **Changes not taking effect?**
   - Hook/skill/settings changes → **new session**.
   - Trigger `.md` edits → next message in an existing session is enough.

2. **Not sure install is correct?** Run **`triggerctl doctor`**. After editing triggers, run **`triggerctl validate`**.

3. **Session trigger did not fire?**
   - Claude: run `triggerctl install --hook`, then start a new session.
   - Hermes: run `triggerctl install --hermes`, then start a new session.
   - Codex: run `triggerctl install --codex`, trust the hook via `/hooks`, then start a new session.
   - Session triggers are soft: the model may miss a match while focused elsewhere — expected; less reliable than poll-based triggers.

4. **Wrong time / timezone?** Containers often run UTC without tzdata. Use **`export TRIGGERCTL_TZ_OFFSET=8`** (default +8). Applies to `schedule --at`, `poll`/`detect`, hook, and statusLine.

5. **`python -m triggerctl` fails?** System Python may not have the package. Use the **`triggerctl`** command on PATH or **`/opt/conda/bin/python3 -m triggerctl`**. Install/upgrade with **`/opt/conda/bin/python3 -m pip install -e .`** — do not assume bare `pip` exists.

## Uninstall

Full uninstall (hooks, skills, and **all** trigger data — user, project, and `system-triggers/`):

```bash
triggerctl uninstall --dry-run    # preview
triggerctl uninstall --yes        # confirm deletion
bash uninstall.sh                 # same as uninstall --root all --yes
```

Partial uninstall:

```bash
triggerctl uninstall --keep-triggers              # hooks/skills only
triggerctl uninstall --triggers-only --yes        # trigger files only
triggerctl uninstall --root user --yes            # user scope only (includes system-triggers)
triggerctl uninstall --agent claude --yes         # Claude integration only
triggerctl uninstall --agent codex --yes          # Codex integration only
```

Uninstall does **not** remove the Python package. To remove it:

```bash
/opt/conda/bin/python3 -m pip uninstall triggerctl
rm /usr/local/bin/triggerctl    # or ~/.local/bin/triggerctl
```
