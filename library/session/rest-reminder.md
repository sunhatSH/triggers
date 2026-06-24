---
name: rest-reminder
enabled: true
inject: false
when: Local time (TRIGGERCTL_TZ_OFFSET, default UTC+8) between 22:00 and 10:00
---

# rest-reminder

> **Not injected into agent context.** Night/morning rest hints come from
> `triggerctl install --statusline` (🌙 in the status bar). This file documents the
> policy; optional manual session use only.

If you ever evaluate this trigger in-session: during **22:00–10:00** local
(`TRIGGERCTL_TZ_OFFSET`), prepend one short line before your answer, e.g.

`[Trigger: rest-reminder] It's {time} — take care, don't stay up too late.`

Then continue the user's task normally. One gentle line per reply; do not refuse work.
