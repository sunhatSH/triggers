# triggerctl

Triggers for Claude Code — 让命令/prompt 在「到点」或「条件成立」时自动执行，既能在会话中触发，也能在 Agent 不运行时（如夜里）由定时轮询拉起。设计参考 [vercel-labs/skills](https://github.com/vercel-labs/skills/tree/main/src) 的模块化思路（frontmatter 为源真相、索引可生成、多注册根）。

## 核心设计

- **两层架构**（同时压住延迟与成本）：
  - **检测层**（便宜，纯 Python，无模型）：评估 `schedule`（时间）+ `probe`（条件），按 run-log 去重。可高频跑（如每分钟）。
  - **执行层**（模型）：只对**真正 DUE** 的触发器调一次 `claude -p`。
- **类型由 frontmatter 推断**：只写 `schedule`=定时型；只写 `probe`=条件型；两者都写=组合（**AND，都满足才触发**）。
- **源真相 = 各触发器 `.md` 的 frontmatter**；`TRIGGERS.md`（扁平一级索引）由 `triggerctl sync` 生成，供模型会话内自查。
- **多注册根**（类似 skills）：用户级 `~/.claude/triggers/`、项目级 `<project>/triggers/`。
- **幂等**：`.state/run-log.jsonl` 按 `(name, key)` 去重；时间型 key=周期，条件型 key=事件实例。

## 安装

```bash
cd triggerctl && pip install -e .
# 之后可用 `triggerctl ...` 或 `python -m triggerctl ...`
```

## 触发器文件格式

```yaml
---
name: auto-commit-push
enabled: true
schedule:                 # 时间条件（可选）
  every: day              # day | hour | week | month
  at: "14:30"             # "HH:MM" | ":MM"
  # on: 周一 / 1          # week 的星期 / month 的日号
dedup: day                # 去重粒度，默认同 every
probe: "test -f /p/flag"  # 条件探针（可选）：退出码 0 = 成立
dedup_cmd: "stat -c %Y /p/flag"  # 事件实例键（可选），默认 "once"
---

# 正文：触发后交给模型执行的自然语言步骤
```

至少声明 `schedule` 或 `probe` 之一。

## 命令

| 命令 | 作用 |
|---|---|
| `triggerctl init [--root user\|project]` | 初始化注册根 |
| `triggerctl add <name> [--every.. \| --probe..] [--category G]` | 注册触发器（建文件 + 重生成索引） |
| `triggerctl list [--root all]` | 列出触发器 |
| `triggerctl enable/disable <name>` | 启/停用 |
| `triggerctl remove <name>` | 删除 |
| `triggerctl sync` | 由触发器文件重新生成 `TRIGGERS.md` |
| `triggerctl detect` | 便宜检测层：判定哪些 DUE（**不调模型**） |
| `triggerctl poll [--dry-run]` | 检测 + 仅对 DUE 调模型执行 |
| `triggerctl status [-n N]` | 看 run-log |
| `triggerctl install --loop --interval 60` | 生成后台循环脚本 |
| `triggerctl install --cron` | 打印 crontab 行 |

## 定时启动

```bash
# 无 cron：后台循环（每 60s 便宜检测一次，仅 DUE 时才调模型）
triggerctl install --root user --loop --interval 60
nohup ~/.claude/triggers/run-loop.sh 60 >/dev/null 2>&1 &

# 有 cron：
triggerctl install --root user --cron   # 打印 crontab 行后 crontab -e 粘进去
```

## 添加一个触发器（例）

```bash
# 定时型：每天 14:30
triggerctl add nightly-backup --root user --category ops --every day --at 14:30
# 条件型：标志文件出现就触发，用 mtime 做事件实例键
triggerctl add on-done --root user --category watch \
  --probe 'test -f /data/done.flag' --dedup-cmd 'stat -c %Y /data/done.flag'
# 组合型：每天 02:00 且条件成立才跑
triggerctl add gated --root user --every day --at 02:00 --probe 'test -f /data/ready'
# 然后编辑生成的 .md 正文，写清要做什么；改完会自动进索引（add/remove/toggle 都会 sync）
```

## 测试

```bash
cd triggerctl && PYTHONPATH=. python -m pytest -q
```

## 取舍 / 已知边界

- **延迟**：轮询固有，≈ 检测间隔；缩间隔几乎不涨成本（检测便宜），唯有「模糊语义条件」必须靠模型判断时才贵。
- **条件型**：探针应观察程序的**外部足迹**（marker / 退出码 / 产出文件 / 进程 / 日志），无需改目标程序；你能控制启动时优先「包一层」做 push。真正无外部痕迹且你不掌控启动的状态变化，是理论下界。
- `probe` 每轮都会跑，务必**只读、轻量、快**。
