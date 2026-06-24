# Upstream submission: UserPromptSubmit replacement context

Use this document to open a PR or comment on Anthropic's Claude Code repository.

**Target issues:** [anthropics/claude-code#45849](https://github.com/anthropics/claude-code/issues/45849), [#40216](https://github.com/anthropics/claude-code/issues/40216)

**Full proposal:** [user-prompt-submit-replacement-context.md](./user-prompt-submit-replacement-context.md)

**Reference implementation:** [triggerctl](https://github.com/sunhatSH/triggers) — `transcript.py`, `hook_runner.py`, `hookgen.py`

## Suggested PR title

`feat(hooks): add replacesPrevious for UserPromptSubmit additionalContext`

## Suggested PR body

```markdown
## Summary

Add optional `replacesPrevious: true` on `UserPromptSubmit` hook output so dynamic
per-turn context replaces the hook's prior injection instead of accumulating in the
session transcript.

Fixes the context growth described in #45849 and #40216.

## Motivation

Hooks that inject trigger registries, memory snapshots, or timestamps on every user
turn currently append a new block each time. Long sessions retain dozens of stale
copies, wasting context and diluting attention on the latest state.

Operators expect **one canonical slot** updated each turn — not N historical copies.

## Proposed API

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "...",
    "replacesPrevious": true
  }
}
```

When `replacesPrevious` is true, remove the most recent prior injection from the
**same hook registration** before inserting the new block.

## Reference implementation

The [triggerctl](https://github.com/sunhatSH/triggers) project implements an
experimental workaround (transcript line filtering + proposed field). See
`docs/proposals/user-prompt-submit-replacement-context.md`.

## Test plan

- [ ] Hook with `replacesPrevious: true` — 3 turns → 1 block in model context
- [ ] Two hooks with replacement — each retains one slot
- [ ] `--resume` — at most one block per replacement hook
- [ ] Without flag — existing append behavior unchanged
```

## How to submit (when `gh` is available)

```bash
# Comment on the feature request
gh issue comment 45849 --repo anthropics/claude-code \
  --body-file docs/proposals/upstream-submission.md

# Or fork claude-code and open a PR with schema + handler changes
```

This environment did not have `gh` installed; paste the proposal manually or install `gh` and authenticate.
