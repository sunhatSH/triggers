---
name: gated-nightly
enabled: true
schedule:
  every: day
  at: "02:00"
probe: "test -f /data/ready"    # 同时声明 schedule + probe => 两者都满足才触发(AND)
---

# gated-nightly（示例：组合型 time+event）

每天 02:00 **且** `/data/ready` 存在时才执行（到点但没 ready 就不跑；ready 但没到点也不跑）。
去重键 = 当日周期键，所以满足条件后当天只触发一次。

触发后：执行你的夜间任务（训练/同步/清理…），并汇报。
