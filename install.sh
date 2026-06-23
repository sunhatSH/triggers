#!/usr/bin/env bash
# triggerctl 安装脚本 —— 把触发器能力嵌入 Claude Code Agent。
#
# 做四件事：
#   1) pip 安装 triggerctl（可编辑），并把 `triggerctl` 命令放上 PATH
#   2) 初始化用户级触发器根（含默认护栏触发器）
#   3) 安装 `triggerctl` skill（让 Claude 能自助注册触发器）
#   4) 写入 UserPromptSubmit hook（把 session 触发器条件每轮注入上下文 —— 这才是“嵌入”）
#
# 用法：  bash install.sh
# 选项：  PREFIX_BIN=~/.local/bin bash install.sh   # 指定放 triggerctl 软链的目录
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"

echo "==> 1/4 安装 triggerctl (pip install -e)"
"$PY" -m pip install -e "$REPO_DIR" -q
# 找到 console script
TCTL="$("$PY" - <<'EOF'
import shutil, sys, os
p = shutil.which("triggerctl")
if not p:
    # console script 常在解释器的 bin 目录
    cand = os.path.join(os.path.dirname(sys.executable), "triggerctl")
    p = cand if os.path.exists(cand) else ""
print(p)
EOF
)"
if [ -z "$TCTL" ]; then
  echo "!! 找不到 triggerctl console script，安装可能失败" >&2; exit 1
fi
echo "    triggerctl: $TCTL"

# 放到 PATH（优先 /usr/local/bin，否则 ~/.local/bin）
BIN_DIR="${PREFIX_BIN:-}"
if [ -z "$BIN_DIR" ]; then
  if [ -w /usr/local/bin ]; then BIN_DIR=/usr/local/bin; else BIN_DIR="$HOME/.local/bin"; fi
fi
mkdir -p "$BIN_DIR"
ln -sf "$TCTL" "$BIN_DIR/triggerctl"
echo "    软链: $BIN_DIR/triggerctl -> $TCTL"
case ":$PATH:" in *":$BIN_DIR:"*) :;; *) echo "    ⚠️ $BIN_DIR 不在 PATH，请加入 PATH";; esac

echo "==> 2/4 初始化用户级触发器根"
"$TCTL" init --root user

echo "==> 3/4 安装 triggerctl skill"
mkdir -p "$CLAUDE_DIR/skills/triggerctl"
cp "$REPO_DIR/skill/SKILL.md" "$CLAUDE_DIR/skills/triggerctl/SKILL.md"
echo "    -> $CLAUDE_DIR/skills/triggerctl/SKILL.md"

echo "==> 4/4 安装 UserPromptSubmit 注入 hook (settings.json)"
"$TCTL" install --hook

cat <<EOF

✅ 安装完成。
- 命令：  triggerctl --help
- 列触发器： triggerctl list
- 让定时/条件型自动跑（可选）： triggerctl install --root user --loop && nohup $CLAUDE_DIR/triggers/run-loop.sh 60 >/dev/null 2>&1 &

⚠️ hook / skill / 触发器都在**会话启动时**加载，请**新开一个 claude 会话**后再验证。
EOF
