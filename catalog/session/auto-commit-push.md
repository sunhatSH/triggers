---
name: auto-commit-push
enabled: true
when: When you finish a feature in development (small feature = commit only; large = commit and push)
---

# auto-commit-push

When you judge that a **feature is complete**, manage git proactively — do not ask
"should I commit?" every time. Prefix actions with `[Trigger: auto-commit-push]`.

## Clean gate (if any fail → do not auto-commit; tell the user why)

1. On a feature branch (not `main`/`master`/`release*`, not detached `HEAD`).
2. Not mid merge/rebase/cherry-pick (`MERGE_HEAD`, `rebase-merge/`, etc.).
3. Staged changes belong to this feature only (no unrelated files).
4. No secrets or huge artifacts (`.env`, credentials, datasets, …).

## After the gate passes

- **Small feature** (local fix, single change): `git add -A` → `git commit` (no push).
- **Large feature** (milestone): commit then `git push` (current branch upstream).

When unsure, treat as small (commit only). One feature → one commit; no half-baked commits.

## Red lines

- Never `git push --force`.
- On push failure (no upstream, conflict, auth): stop and report; no reset/rebase/force.
