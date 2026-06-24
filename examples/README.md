# Moved → `catalog/`

示例与 bundled 模板已合并到 **[../catalog/](../catalog/)**：

| 旧路径 | 新路径 |
|---|---|
| `examples/time-daily-backup.md` | `catalog/poll/daily-backup.md` |
| `examples/event-on-done.md` | `catalog/poll/on-train-done.md` |
| `examples/combo-gated-nightly.md` | `catalog/poll/gated-nightly.md` |
| `examples/session-commit-on-feature.md` | `catalog/session/commit-on-feature.md` |
| `bundled/git-triggers/auto-commit-push.md` | `catalog/session/auto-commit-push.md` |
| `bundled/wellbeing-triggers/rest-reminder.md` | `catalog/session/rest-reminder.md` |

```bash
triggerctl add --from ./catalog/poll/daily-backup.md --root user
triggerctl add --from sunhatSH/triggers/catalog/poll --list
```

详见 [../catalog/README.md](../catalog/README.md)。
