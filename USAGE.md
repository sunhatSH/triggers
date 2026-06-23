# triggerctl 使用说明

把"触发器"作为能力嵌入 Claude Code Agent：让命令/prompt 在**到点**、**条件成立**或 **Agent 判断某语义条件成立**时执行。

## 安装

```bash
git clone git@github.com:sunhatSH/triggers.git
cd triggers
bash install.sh
```

`install.sh` 会：安装 `triggerctl` 到 PATH → 初始化用户级触发器根（含护栏）→ 安装 `triggerctl` skill → 写入会话注入 hook。**装完务必新开一个 `claude` 会话**才生效（hook/skill/触发器都在会话启动时加载）。

## 三类触发器

| 类型 | frontmatter | 何时触发 | 谁评估 |
|---|---|---|---|
| `time` | `schedule`(every/at/on) | 到点 | `triggerctl poll`（后台轮询，便宜检测层） |
| `event` | `probe`(shell 退出码 0) | 条件成立 | `triggerctl poll` |
| `session` | `when`(自然语言) | Agent 自判语义条件 | **会话内**（由注入 hook 把条件喂进上下文，模型自检） |

- `time`+`probe` 同写 = 组合（AND）。
- 任意类型加 `locked: true` = 不可关闭（`disable`/`remove` 被拒）。

## 两种使用方式

**A. 对 Claude 说人话**（`triggerctl` skill 会让它替你注册）：
> "注册一个每天 14:30 自动备份的触发器" / "完成一个特性就提交" / "列出/停用 xxx"

**B. 终端命令**：

```bash
triggerctl list [--root all|user|project]      # 列出（🔒=不可关闭，停用的不在生成索引里）
triggerctl add <name> --root user [条件参数]    # 注册（见下），自动刷新索引
triggerctl enable/disable/remove <name>        # 开/关/删
triggerctl detect                              # 便宜检测：现在哪些 DUE（不调模型）
triggerctl poll [--dry-run]                    # 检测 + 仅对 DUE 调模型执行
triggerctl status -n 20                        # run-log
triggerctl sync                                # 由触发器文件重建 TRIGGERS.md
triggerctl hook                                # 输出 session 条件块（hook 内部用）
```

注册示例：

```bash
triggerctl add nightly  --root user --category ops   --every day --at 02:00
triggerctl add on-done  --root user --category watch --probe 'test -f /data/done.flag' --dedup-cmd 'stat -c %Y /data/done.flag'
triggerctl add commit   --root user --category git   --when '完成一个特性时：小提交/大推送'
triggerctl add guard    --root user --when '...' --locked
```
`add` 后**编辑生成的 .md 正文**，把动作写清楚（写给模型看的步骤）。

## 让 time/event 真正自动跑

`session` 型靠会话内 hook；`time`/`event` 型需要后台轮询：

```bash
triggerctl install --root user --loop --interval 60
nohup ~/.claude/triggers/run-loop.sh 60 >/dev/null 2>&1 &
# 有 cron：triggerctl install --root user --cron
```

## 嵌入机制（为什么用 hook）

- `time`/`event`：`triggerctl poll` 后台跑，**确定性**。
- `session`：条件是语义的，没有 shell 能判定。靠 `install --hook` 写入的 **UserPromptSubmit hook**，每轮把启用的 session 触发器条件注入上下文，模型据此自检执行。这是“可靠浮现 + 软执行”——比把条件埋在 `TRIGGERS.md` 里强很多。

## 常见问题（重要）

1. **改了触发器/CLAUDE.md/hook 后没生效？** 它们都只在**会话启动时**加载。运行中的会话看不到改动，**必须新开 `claude` 会话**。
2. **session 触发器没触发？**
   - 没装注入 hook：跑 `triggerctl install --hook` 再开新会话。
   - 它是软触发：即使条件注入了，模型仍可能在专注别的任务时漏掉——属预期，可靠性 < 确定性机制。
3. **时间不对 / 定时和时区？** 容器多为 UTC 且常缺 tzdata（`TZ=Asia/Shanghai` 无效）。要北京时间用 POSIX 偏移：`TZ='UTC-8' date +%H:%M`。`time` 型的 `--at` 默认按机器时钟（通常 UTC）解释。
4. **`python -m triggerctl` 报找不到包？** 默认 `python3` 可能不是装了本包的解释器；用 `triggerctl` 命令或对应解释器。

## 卸载

```bash
pip uninstall triggerctl
rm <PATH>/triggerctl                       # 你装的软链
# 从 ~/.claude/settings.json 的 hooks.UserPromptSubmit 删掉 triggerctl hook 那条
rm -rf ~/.claude/skills/triggerctl
```
