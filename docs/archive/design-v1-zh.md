# 触发器系统（Triggers）— 最终方案

> 一句话：在 Claude Code 里建一套和 `skills/` 平级的「触发器」机制，让某些命令/prompt 在**满足条件时自动执行**——既支持「Agent 在会话中自查触发」，也支持「Agent 不在运行时由定时轮询拉起执行」（如夜里）。

## 1. 为什么要做

- 现状：触发器只能在每次发请求时，模型读到注册表后才检查、才触发（如触发 `git commit & push`）。
- 痛点：有些触发器需要在 **Agent 不运行时**执行（例：夜里 02:00 自动备份/提交）。
- 方案：加一个**独立启动方式**——定时拉起 Claude Code（headless），让模型**轮询 triggers**，判断当前时间段有没有该执行的触发器。
- 代价（已接受）：有延迟。每小时轮询时，14:30 的任务可能 15:00 才跑；事件型触发器也会延迟。这是定时轮询的固有缺陷。

## 2. 两条执行路径

| 路径 | 触发时机 | 适用类型 | 机制 |
|---|---|---|---|
| 会话内自查 | 用户每次发请求时 | 含 `probe` 的（条件型/组合型） | `CLAUDE.md` 索引 → 模型读注册表 → 判断条件 → 执行 |
| 独立轮询 | 定时（如每小时） | 全部（time / event / 组合） | `cron`/循环脚本 → `claude -p poll.md` → 模型筛 DUE → 执行 |

轮询能处理全部类型；会话内自查只对"含 `probe` 的"有意义（定时型无需会话参与）。两条路径若同时可能触发同一条触发器，靠同一份 `run-log` 去重防双跑。

## 3. 目录结构（和 skills 平级）

```
CLAUDE.md                       # 注册入口：引用 triggers/TRIGGERS.md
triggers/
    TRIGGERS.md                 # 唯一权威索引（一级）：一张扁平表列全部触发器+条件
    poll.md                     # 轮询 prompt（headless 用，模型读它执行轮询）
    run-poll.sh                 # 单次轮询：cron 调它（claude -p poll.md）
    loop-poll.sh                # 无 cron 环境的兜底：while+sleep 自循环
    .state/
        run-log.jsonl           # 去重状态（每次执行追加一行）
        poll.out                # 轮询运行日志
    git-triggers/               # 子目录仅用于“收纳”，不再放二级 TRIGGERS.md
        auto-commit-push.md     # 触发器文件（frontmatter + prompt 正文）
    watch-triggers/
        on-done-marker.md
    .../
```

**一级索引（关键设计）**：条件必须出现在模型每次都读的入口。所以顶层 `TRIGGERS.md` 是**唯一**索引，一张扁平表把所有触发器的条件直接列出；子目录只做文件收纳，**不**再用「每个子目录一个 TRIGGERS.md」当索引层——否则二级里的条件在入口处不可见，事件型自查就失效了。

## 4. 登记表字段（一张扁平表，写在顶层 `TRIGGERS.md`）

| 字段 | 含义 |
|---|---|
| 名称 | 唯一名 / id |
| 类型 | `time` / `event` / `time+event`（人看的摘要；实际由 frontmatter 是否含 `schedule`/`probe` 决定） |
| 触发条件 | 条件型=自然语言条件；定时型=可读时间（如「每天 14:30」）；组合型两者都写 |
| 文件 | 触发器文件路径 `子目录/文件.md`。**一文件一触发器**，触发器数量有限，不用行号定位 |

> 登记表保持精简、但**必须含条件**，因为它是模型每次唯一会读的索引。轮询用的**结构化元数据**（`schedule` / `probe` / `dedup` / `dedup_cmd` / `enabled`）放在每个触发器**自己文件的 frontmatter** 里，不污染登记表。

## 5. 每个触发器文件的内部结构

**一文件一触发器**。frontmatter 不写 `type`——类型由是否声明 `schedule` / `probe` 推断：只写 `schedule`=定时型；只写 `probe`=条件型；**两个都写=组合，二者都满足才触发（AND）**。至少要声明其一。

```yaml
---
name: auto-commit-push          # 与登记表一致的唯一名
enabled: true                   # 启用开关，临时停用改 false 即可
schedule:                       # 时间条件（可选）
  every: day                    # day | hour | week | month
  at: "14:30"                   # 当前周期内的目标时刻（hour 型可写 ":30"）
  # on: 周一 / 1                # week 指定星期、month 指定日号时用
dedup: day                      # schedule 的去重周期粒度，默认同 every
probe: "test -f /path/flag"     # 条件探针（可选）：一条 shell 命令，退出码 0 = 成立
dedup_cmd: "stat -c %Y /path/flag"  # 可选；stdout 作为「事件实例键」，同实例只触发一次
---

# <正文>：触发后真正要执行的 prompt / 命令步骤
```

- 纯定时型：只留 `schedule`（+可选 `dedup`）。
- 纯条件型：只留 `probe`（+可选 `dedup_cmd`）。
- 组合型：两者都写，「到点」且「条件成立」才触发。

## 6. 轮询语义（poll.md 的判定逻辑，模型解释执行）

定时只是**节拍**：cron/循环每隔一段拉起 `claude -p poll.md`，真正"该不该触发"的判断由**模型**完成——它要读触发器、**跑探针**、比对 run-log。对每个 `enabled: true` 的触发器，评估它声明的**所有**条件，**全部成立**才 DUE，并拼出去重键 `key`：

**若有 `schedule`（时间条件）**
- `target` = 当前周期内目标时刻（如今天 14:30）；该条件成立当 `now >= target`。
- 子键 = period_key：`day→YYYY-MM-DD`、`hour→YYYY-MM-DD HH`、`week→YYYY-Www`、`month→YYYY-MM`（粒度取 `dedup`，默认 `every`）。

**若有 `probe`（条件探针）**
- 跑 `probe`，退出码 0 = 条件成立。
- 子键 = 跑 `dedup_cmd` 的 stdout（去空白）；无则 `"once"`。

**合成**
- **DUE = 所有已声明条件都成立**（AND）。
- **key** = 用到的子键按 `schedule|probe` 顺序用 `|` 拼接；都没有子键则 `"once"`。

**去重 + 执行**
- 若 `.state/run-log.jsonl` 已有同 `(name, key)` 记录 → 跳过。
- 否则执行正文 → 追加 `{name, key, ran_at, result}`；即使"无需动作"也记一条 `skip:...`，避免反复重试。
- 汇报：执行了 / 条件未全满足 / 已处理跳过 / 出错 各有哪些。

这套语义同时满足：定时型「延迟也能补跑、同周期不重复」；条件型「夜里也能被定时拉起评估、同一事件实例只触发一次」；组合型「到点且条件成立才动，按周期去重」。

## 7. 启动方式

- **有 cron 的机器**：把 `run-poll.sh` 注册进 crontab，例如每小时：
  ```cron
  0 * * * * /mnt/afs_toolcall/sunhao4/triggers/run-poll.sh
  ```
- **无 cron 的环境（当前容器即是）**：后台跑兜底循环：
  ```bash
  nohup /mnt/afs_toolcall/sunhao4/triggers/loop-poll.sh 3600 >/dev/null 2>&1 &
  ```
  （参数是轮询间隔秒数，3600=每小时一次）

## 8. 关键约束

- **幂等优先**：必须先查 `run-log.jsonl` 再决定执行，否则每次轮询会重复触发。
- **轮询同时处理 time / event / 组合**：定时型按时间表、条件型按 `probe` 探针、组合型两者都满足才触发（AND），都由被拉起的模型评估，共用 run-log 去重。会话内自查与轮询若都可能触发同一条含 `probe` 的触发器，靠同一份 run-log 防双跑。
- **probe 要只读、轻量、快**：每次轮询都会跑它，别在 probe 里做有副作用或耗时的事。
- **headless 运行位置决定加载哪份注册表**：项目级 `cd` 到项目根；用户级 `cd $HOME`，才能读到对应的 `CLAUDE.md` / `.claude/settings.json`。
- **登记 = 注册**：触发器只要登记在文档里（`CLAUDE.md → TRIGGERS.md`）即生效，不需要额外注册步骤。
