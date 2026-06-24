# Bundled triggers (optional)

These files ship with the repo for copy/install on demand. **`triggerctl init` only
seeds the first guardrail** (`too-many-triggers-warning` in `system-triggers/`).
Nothing else here is installed automatically.

## Install one

```bash
triggerctl add --from ./bundled/git-triggers/auto-commit-push.md --root user
triggerctl add --from ./bundled/wellbeing-triggers/rest-reminder.md --root user
```

## Install all bundled (explicit)

```bash
triggerctl add --from ./bundled --root user
```

## Bundled set

| Path | Type | In hook context? |
|---|---|---|
| _(init only)_ `system-triggers/too-many-triggers-warning` | session guardrail | **No** (`inject: false`) |
| `git-triggers/auto-commit-push.md` | session | **Yes** |
| `wellbeing-triggers/rest-reminder.md` | session doc + statusLine | **No** (`inject: false`; rest uses statusLine 🌙) |

For time/event templates see [../examples/](../examples/).

The **>5 warning** counts only **hook-eligible** session triggers (`in_context`), not
time/event triggers or `inject: false` entries.
