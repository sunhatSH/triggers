# Moved → `catalog/`

Templates previously under `bundled/` and `examples/` now live in **[../catalog/](../catalog/)**:

- Session: `catalog/session/`
- Time/event/combo: `catalog/poll/`

```bash
triggerctl add --from ./catalog/session/auto-commit-push.md --root user
triggerctl add --from ./catalog/poll/daily-backup.md --root user
```

See [../catalog/README.md](../catalog/README.md) for the full index.
