---
name: daily-backup
enabled: true
schedule:
  every: day        # day | hour | week | month
  at: "02:00"       # "HH:MM" 或 ":MM"
dedup: day          # 去重粒度，默认同 every
---

# daily-backup（示例：定时型）

每天 02:00 把 `<目标目录>` 备份到 `<备份位置>`。执行步骤：

1. 确认源目录存在；不存在则报告并跳过。
2. 执行备份（例：`rsync -a --delete <src>/ <dst>/` 或打 tar 包）。
3. 汇报：备份了多少、耗时、是否成功。

约束：只读源、写目标；空间不足或源缺失时停下报告，不要静默失败。
