# Trigger catalog

Optional templates you install on demand with `triggerctl add --from`. **`triggerctl init`**
only seeds the locked guardrail (`too-many-triggers-warning`); nothing here is auto-installed.

## Layout

| Directory | Kind | Handler | In hook context? |
|---|---|---|---|
| `session/` | Semantic session (`when` only) | Agent hook each turn | **Yes** (unless `inject: false`) |
| `poll/` | time / event / combo | `triggerctl poll` | **No** |

## Install

```bash
# One template
triggerctl add --from ./catalog/session/auto-commit-push.md --root user
triggerctl add --from ./catalog/poll/daily-backup.md --root user

# Preview a directory
triggerctl add --from ./catalog/session --list

# Install all session templates (explicit)
triggerctl add --from ./catalog/session --root user
```

Remote (GitHub):

```bash
triggerctl add --from sunhatSH/triggers/catalog/poll --list
```

## Session templates (`session/`)

| File | Notes |
|---|---|
| `auto-commit-push.md` | Commit/push when user asks (hook context) |
| `rest-reminder.md` | Rest window via statusLine only (`inject: false`) |
| `commit-on-feature.md` | Commit when feature work is done |

## Poll templates (`poll/`)

| File | Type |
|---|---|
| `daily-backup.md` | time — daily schedule |
| `on-train-done.md` | event — probe file exists |
| `gated-nightly.md` | combo — schedule AND probe |

Poll templates need `triggerctl install --loop` (or cron calling `triggerctl poll`).

The **>5 warning** counts **hook-eligible** session triggers only (`in_context`), not poll
templates or `inject: false` entries.
