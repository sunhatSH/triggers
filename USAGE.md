# triggerctl 使用说明

把"触发器"作为能力嵌入 Claude Code Agent：让命令/prompt 在**到点**、**条件成立**或 **Agent 判断某语义条件成立**时执行。

## 安装

```bash
git clone git@github.com:sunhatSH/triggers.git
cd triggers
bash install.sh
```

`install.sh` 会：用带 pip 的 Python 安装 `triggerctl` → 初始化用户级触发器根 → 安装 skill → 写入 hook + statusLine。**装完务必新开一个 `claude` 会话**才生效。

> 本机通常**没有 `pip` 命令**（`/usr/bin/python3` 也无 pip 模块）。请直接：
> ```bash
> cd triggers && bash install.sh
> # 或指定解释器：
> PYTHON=/opt/conda/bin/python3 bash install.sh
> ```

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
triggerctl add --from <SOURCE> [--list]        # 从 Git/本地安装（见下）
triggerctl update [--root user] [--force]      # 按 triggers-lock.json 更新已装包
triggerctl doctor                              # 健康检查：PATH/hook/索引/轮询
triggerctl validate [--probe-test]             # 校验 frontmatter、重名、索引过期
triggerctl enable/disable/remove <name>        # 开/关/删
triggerctl detect                              # 便宜检测：现在哪些 DUE（不调模型）
triggerctl poll [--dry-run]                    # 检测 + 仅对 DUE 调模型执行
triggerctl status -n 20                        # run-log
triggerctl sync                                # 由触发器文件重建 TRIGGERS.md
triggerctl hook                                # 输出 session 条件块（hook 内部用）
```

从 Git / 本地安装（对标 `skills add`）：

```bash
triggerctl add --from sunhatSH/triggers/examples --list
triggerctl add --from ./examples/time-daily-backup.md --root user
triggerctl update --root user
```

SOURCE：`owner/repo[/path]`、git URL、本地目录或单个 `.md`。安装记录写入 `triggers-lock.json`。

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

## 嵌入机制（为什么用 hook + statusLine）

- `time`/`event`：`triggerctl poll` 后台跑，**确定性**。
- `session`：条件是语义的，没有 shell 能判定。靠三层嵌入：
  1. **`triggerctl sync`** 写入 CLAUDE.md managed block（最高优先级）
  2. **`install --hook`**：UserPromptSubmit 每轮注入条件 + 换算后本地时间
  3. **`install --statusline`**：状态栏确定性显示（如休息提醒，不依赖模型）
- 装完或改配置后**必须新开 `claude` 会话**才生效。

## 常见问题（重要）

1. **改了触发器/CLAUDE.md/hook 后没生效？** 它们都只在**会话启动时**加载。运行中的会话看不到改动，**必须新开 `claude` 会话**。
2. **不确定装对了没？** 跑 **`triggerctl doctor`**；改完触发器文件后跑 **`triggerctl validate`** 看索引是否过期、schedule 是否合法。
3. **session 触发器没触发？**
   - 没装注入 hook：跑 `triggerctl install --hook` 再开新会话。
   - 它是软触发：即使条件注入了，模型仍可能在专注别的任务时漏掉——属预期，可靠性 < 确定性机制。
4. **时间不对 / 定时和时区？** 容器多为 UTC 且常缺 tzdata。统一用 **`export TRIGGERCTL_TZ_OFFSET=8`**（默认已是 +8）：`schedule --at`、`poll`/`detect`、hook、statusLine 都按此本地时间解释。POSIX `TZ='UTC-8' date` 仅作 shell 参考。
5. **`python -m triggerctl` 报找不到包？** 默认 `/usr/bin/python3` 没装本包；用 **`triggerctl` 命令**（链到 conda）或 **`/opt/conda/bin/python3 -m triggerctl`**。安装/升级用 **`/opt/conda/bin/python3 -m pip install -e .`**，不要写裸 `pip`。

## 卸载

```bash
/opt/conda/bin/python3 -m pip uninstall triggerctl   # 用装包时的同一个 Python
rm /usr/local/bin/triggerctl                       # 或 ~/.local/bin/triggerctl
# 从 ~/.claude/settings.json 的 hooks.UserPromptSubmit 删掉 triggerctl hook 那条
rm -rf ~/.claude/skills/triggerctl
```
