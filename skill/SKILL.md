---
name: triggerctl
description: 用 triggerctl 注册/管理「触发器」——让命令或 prompt 在「到点」(定时) 或「条件成立」(探针) 时自动执行，支持两者组合(AND)、用户级/项目级两种注册根、run-log 幂等去重。触发关键词：建个触发器、注册触发器、定时执行/每天每小时定时跑某事、当xxx就yyy、某任务完成后自动做某事、settrigger、schedule a task、自动提交、夜里自动跑、轮询触发、列出/启用/停用/删除触发器、安装定时轮询。当用户想让某件事"自动地、按时间或按条件"发生时用本 skill。
---

# triggerctl

用 `triggerctl` 命令注册和管理触发器（`install.sh` 已把它装到 PATH）。这是给 Claude 自己在会话里"像 skills 一样注册触发器"的操作手册。引擎与完整说明见 triggerctl 仓库 README / USAGE。

> 若某环境 `triggerctl` 不在 PATH，用安装时记录的绝对路径调用；不要用 `python -m triggerctl`，除非确认那个 `python` 装了本包。

## 心智模型（先理解再操作）

- **类型由 frontmatter 推断**，不写 `type`：
  - 只有 `schedule` → 定时型（到点触发，轮询评估）
  - 只有 `probe` → 条件型（一条 shell 命令退出码 0 即成立，轮询评估）
  - `schedule` + `probe` → 组合型，**都满足才触发（AND）**
  - 有 `when` → **session 型**：`when` 是**语义条件**（如"完成一个特性时"），没有 shell 探针能判定，**轮询器不碰**；改由 **Agent 在会话内自检**（通过 CLAUDE.md/索引看到后，在干活过程中自己判断并执行正文）。
- **怎么选 probe 还是 when**：能用一条命令判真假 → 用 `--probe`（后台也能触发）；只能靠人/Agent 语义判断（如"开发完一个特性""讨论该收尾了"）→ 用 `--when`（仅会话内、由做这件事的 Agent 自己触发，本质是 push）。
- **两层执行**：便宜检测层（纯 Python，无模型）判 DUE；只有 DUE 才调一次 `claude -p` 执行触发器正文。
- **正文 = 写给模型的自然语言动作步骤**（不是 shell 脚本）。`add` 生成的正文是 TODO 占位，**必须编辑成真正要做的事**，否则触发时模型不知道干啥。
- **幂等**：`.state/run-log.jsonl` 按 `(name, key)` 去重。定时型 key=周期(日/时/周/月)，条件型 key=`dedup_cmd` 输出(默认 `once`)。
- **两个注册根**（类似 skills）：用户级 `~/.claude/triggers/`（`--root user`，全局）、项目级 `<project>/triggers/`（`--root project`）。
- **可关闭 / 不可关闭**：普通触发器可 `disable`（停用后不进上下文、不被轮询）。`locked: true`（建时加 `--locked`）的为**不可关闭**护栏，`disable`/`remove` 被拒绝，`list` 标 🔒。`too-many-triggers-warning` 是默认护栏（启用触发器 >20 时提醒精简），别去关它。

## 注册一个触发器（标准流程）

1. **选根**：跨项目通用 → `--root user`；只服务当前项目 → `--root project`。
2. **add**（会自动生成 .md 并重建 `TRIGGERS.md` 索引）：

   ```bash
   # 定时型：每天 14:30
   triggerctl add nightly-report --root user --category ops --every day --at 14:30
   # 条件型：标志文件出现就触发，用 mtime 当事件实例键（同一次只触发一次）
   triggerctl add on-train-done --root user --category watch \
     --probe 'test -f /data/done.flag' --dedup-cmd 'stat -c %Y /data/done.flag'
   # 组合型：每天 02:00 且条件成立才跑
   triggerctl add gated-backup --root user --every day --at 02:00 --probe 'test -f /data/ready'
   # session 型：语义条件由 Agent 会话内自己判断（轮询不评估）
   triggerctl add auto-commit-push --root user --category git \
     --when '完成一个特性时：小特性=仅提交，大特性=提交并推送'
   ```

   `--every day|hour|week|month`，`--at "HH:MM"|":MM"`，`--on 周一|1`（week 星期 / month 日号），`--dedup` 改去重粒度，`--disabled` 建为停用，`--category G` 放进 `G-triggers/` 子目录收纳。

3. **写正文**：打开 add 输出的 `.md` 路径，把 `# 标题` 下的 TODO 换成真正的动作步骤（清晰、可执行、写给模型）。
4. **确认**：`triggerctl list --root user` 看到它即注册成功。

## 其它管理命令

```bash
triggerctl list   [--root all|user|project]   # 列出（🔒=不可关闭）
triggerctl enable  <name> / disable <name>     # 启/停用（改 enabled，自动 sync）
triggerctl remove  <name>                      # 删除（自动 sync）
triggerctl detect [--root ..]                  # 便宜检测：现在哪些 DUE（不调模型，可放心多跑）
triggerctl poll   [--root ..] [--dry-run]      # 检测 + 仅对 DUE 调模型执行
triggerctl status [--root ..] -n 20            # 看 run-log
triggerctl sync   [--root ..]                  # 由触发器文件重建 TRIGGERS.md（一般无需手动）
```

## 让它在 Agent 不运行时也触发（关键）

注册只是登记。要"夜里也触发"，必须有定时轮询在跑：

```bash
triggerctl install --root user --loop --interval 60      # 无 cron：生成 run-loop.sh
nohup ~/.claude/triggers/run-loop.sh 60 >/dev/null 2>&1 & # 后台常驻（每60s便宜检测一次）
# 有 cron：triggerctl install --root user --cron  # 打印 crontab 行
```

询问用户是否需要现在拉起轮询；不要擅自常驻后台进程。

## 注意事项 / 坑

- **probe 必须只读、轻量、快**：每轮检测都会跑它，别在 probe 里做有副作用或耗时的事。
- **probe 观察外部足迹**而非改目标程序：用 `test -f 产出文件` / `pgrep` / 日志 `grep` / 退出码 / `nvidia-smi` 等；你能控制启动时优先"包一层" push（`prog && triggerctl poll`）。
- **不要手改 `TRIGGERS.md`**：它是 `sync` 生成的，改触发器 `.md` 后会被覆盖。
- 条件无法表达成 sharp 探针的"模糊语义事件"，shell 判不准——要么找一个可量化代理信号，要么靠会话内人工判断，别硬写不可靠的 probe。
- 涉及 git push / 删除等有风险动作的触发器，正文里要写明安全约束（禁止 force push、不碰密钥文件等）。
