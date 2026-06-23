---
name: on-train-done
enabled: true
probe: "test -f /data/done.flag"            # 退出码 0 = 条件成立
dedup_cmd: "stat -c %Y /data/done.flag"     # 事件实例键：同一次完成只触发一次
---

# on-train-done（示例：条件型）

约定长任务结束时落一个标志文件 `/data/done.flag`（producer 侧 `touch` 即可，无需改其内部）。
本触发器由轮询探针检测到该文件后触发。

触发后：
1. 读取产出（如 `/data/result/`），跑评测 / 归档 / 发通知。
2. 汇报结果。

要点：`probe` 必须只读、轻量、快（每轮检测都会跑）。下一次任务重新 `touch`（mtime 变）才会再次触发。
