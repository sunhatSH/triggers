# Trigger library

Official **optional** triggers — shipped with triggerctl but **not installed** on `init`
(only the locked `too-many-triggers-warning` guardrail is seeded automatically).

## List (remote)

```bash
triggerctl library list
triggerctl library list --source sunhatSH/triggers/library
```

## Install

```bash
# One trigger by name
triggerctl library install rest-reminder
triggerctl library install auto-commit-push --root user

# Several at once
triggerctl library install rest-reminder auto-commit-push

# Everything in the library
triggerctl library install --all
```

## Layout

| Directory | Kind | Handler |
|---|---|---|
| `session/` | semantic session (`when`) | Agent hook each turn |
| `poll/` | time / event / combo | `triggerctl poll` |

Index: [`manifest.yaml`](manifest.yaml) — names, paths, descriptions for `library list`.

## Legacy install path

Still works:

```bash
triggerctl add --from sunhatSH/triggers/library/session/rest-reminder.md --root user
triggerctl add --from ./library/session --list
```
