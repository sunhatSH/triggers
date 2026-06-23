---
name: commit-on-feature
enabled: true
when: 开发过程中完成了一个特性时（小特性=仅提交；大特性=提交并推送）
---

# commit-on-feature（示例：会话型 session）

`when` 是**语义条件**——没有 shell 探针能判定"完成了一个特性"，所以轮询器不碰它，由 **Agent 在会话内自检并执行**（本质是 push：做开发的就是 Agent，它知道完成的时刻）。

触发后（开头标来源 `[触发器: commit-on-feature]`）：
- 小特性：`git add -A` → `git commit`（不推送）。
- 大特性：提交后 `git push`。

前置干净门槛（任一不满足→不自动做，只提醒用户）：在功能分支（非 main/master）、不在 merge/rebase 中途、暂存仅含本特性改动、无密钥/大文件。**禁止** force push。
