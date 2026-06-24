# Proposal: Replacement context for UserPromptSubmit hooks

**Status:** Draft for upstream (Claude Code)  
**Related issues:** [anthropics/claude-code#45849](https://github.com/anthropics/claude-code/issues/45849), [#40216](https://github.com/anthropics/claude-code/issues/40216)

## Problem

`UserPromptSubmit` hooks can inject dynamic context via plain stdout or JSON
`hookSpecificOutput.additionalContext`. Today, **each injection is appended to the
session transcript and kept for all future turns**.

For per-turn context layers (memory systems, trigger registries, project state
snapshots), this causes:

1. **Linear context growth** — a 50-turn session may retain 50 copies of similar
   hook output.
2. **Attention dilution** — stale copies compete with the latest block; the
   model should see **one canonical snapshot** adjacent to the current user turn.
3. **Stale values on resume** — timestamps and SHAs from old injections remain
   visible even after `--continue` / `--resume`.

## Desired behavior

Support **replacement mode**: the latest injection from a given hook **replaces**
its previous injection in the transcript/context assembly, rather than appending.

Semantics:

| Mode | Transcript history | Model context on turn N |
|---|---|---|
| Current (append) | N injection blocks | All N blocks visible |
| **Replacement** | 1 injection block (updated each turn) | **Only latest** visible |

This is **not** the same as “inject only on the first turn”. Replacement keeps
fresh per-turn values (time, git status, trigger conditions) while maintaining
a single slot in context.

## Proposed API

Extend `UserPromptSubmit` hook JSON output:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[Triggers·UTC+8 14:32] …",
    "replacesPrevious": true
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `additionalContext` | string | Context injected for the current turn (existing) |
| `replacesPrevious` | boolean | When `true`, remove the most recent prior injection from **this hook** (matched by hook command identity or a stable `hookInstanceId`) before inserting the new block |

Optional future extension:

```json
"ephemeral": true
```

When set, the block is visible to the model on the current turn only and is
**not** written to the persisted transcript at all. Replacement mode is
preferable when resume/replay should show the last injected snapshot.

### Matching prior injections

Replace prior blocks that were produced by the **same hook registration entry**
(same `settings.json` hook command string, or an explicit `hookInstanceId` the
host assigns). Do not remove injections from other hooks.

### Resume / compact

- On `--resume`, replacement hooks should **re-run** (like `SessionStart`) or
  replay the **last** stored injection only — not every historical copy.
- `PreCompact` / `PostCompact` should treat replacement injections as a single
  logical slot when summarizing.

## Reference implementation (triggerctl)

[triggerctl](https://github.com/sunhatSH/triggers) implements an **experimental
workaround** when `TRIGGERCTL_HOOK_REPLACE=1`:

1. Read `transcript_path` from hook stdin JSON.
2. Strip JSONL lines containing trigger injection markers (`[Triggers·…`).
3. Emit JSON `additionalContext` with `"replacesPrevious": true` (ignored by
   current Claude Code; documents intent).

See:

- `triggerctl/transcript.py` — transcript line filtering
- `triggerctl/hook_runner.py` — hook orchestration
- `triggerctl/hookgen.py` — injection payload

Enable in `~/.claude/settings.json`:

```json
{
  "env": {
    "TRIGGERCTL_HOOK_REPLACE": "1",
    "TRIGGERCTL_HOOK_JSON": "1"
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "triggerctl hook"
          }
        ]
      }
    ]
  }
}
```

**Limitations of the workaround:** races with concurrent writers, depends on
marker strings in JSONL, not officially supported. Native platform support is
required for a robust solution.

## Context policy (triggerctl)

To minimize unnecessary injection:

| Trigger kind | Mechanism | In hook / agent context? |
|---|---|---|
| `schedule` (time) | `triggerctl poll` | **No** |
| `probe` (event) | `triggerctl poll` | **No** |
| `schedule` + `probe` | `triggerctl poll` | **No** |
| `when` only (semantic session) | UserPromptSubmit hook | **Yes** (replacement) |
| `inject: false` | doctor / statusLine / manual | **No** |

`TRIGGERS.md` is an **ops index only** — not loaded into agent context.

## Test plan (upstream)

1. Register a UserPromptSubmit hook that returns `replacesPrevious: true` and a
   unique marker including the turn counter.
2. Submit 3 prompts in one session.
3. Assert the model transcript/context contains **one** marker block (latest
   counter), not three.
4. `--resume` the session; assert at most one marker (re-run hook or replay last).
5. Two different hooks with replacement enabled each retain **one** slot.

## Summary

Add `replacesPrevious` (and optionally `ephemeral`) to `UserPromptSubmit` hook
output so dynamic per-turn context can occupy a **single attention slot** —
matching how operators expect “current trigger state” to behave.
