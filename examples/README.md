# 示例触发器

这些是各类型触发器的模板。两种用法：

1. **直接拷贝**到某个注册根（`~/.claude/triggers/<分组>/` 或 `<项目>/triggers/<分组>/`），改好正文里的路径/动作，然后 `triggerctl sync`。
2. **从本仓库安装**（推荐，会写入 `triggers-lock.json`）：
   ```bash
   triggerctl add --from ./examples/time-daily-backup.md --root user
   triggerctl add --from sunhatSH/triggers/examples --list   # 远程预览
   ```
3. **用 CLI 生成**再编辑正文，例如：
   ```bash
   triggerctl add daily-backup --root user --category ops --every day --at 02:00
   ```

类型一览：

| 文件 | 类型 | 说明 |
|---|---|---|
| `time-daily-backup.md` | time | 每天 02:00 触发（轮询评估） |
| `event-on-done.md` | event | 标志文件出现即触发（轮询评估，按 mtime 去重） |
| `combo-gated-nightly.md` | time+event | 每天 02:00 **且**条件成立才触发（AND） |
| `session-commit-on-feature.md` | session | 语义条件，由 Agent 会话内自判（轮询不评估） |

> `time`/`event` 要真正自动跑需先 `triggerctl install` 把轮询拉起来；`session` 型靠 Agent 会话内自检。
