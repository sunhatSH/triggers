#!/usr/bin/env bash
# triggerctl install — embed triggers into Claude Code.
#
# 1) Install triggerctl (editable) with a Python that has pip; link onto PATH
# 2) Initialize user registry (includes default guardrail trigger)
# 3) Install triggerctl skill
# 4) Write UserPromptSubmit hook + statusLine
# 5) Enable experimental hook replace env vars in settings.json
#
# Usage:  bash install.sh
# Options:  PYTHON=/opt/conda/bin/python3 bash install.sh
#           PREFIX_BIN=~/.local/bin bash install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"

_find_python() {
  if [ -n "${PYTHON:-}" ]; then
    echo "$PYTHON"
    return 0
  fi
  local cand
  for cand in \
    /opt/conda/bin/python3 \
    /usr/local/bin/python3 \
    python3 \
    python; do
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -m pip --version >/dev/null 2>&1; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

if ! PY="$(_find_python)"; then
  cat >&2 <<'EOF'
!! No Python with pip found (many systems lack a `pip` command).

Retry with an interpreter that has pip, e.g.:
  PYTHON=/opt/conda/bin/python3 bash install.sh

Or manually:
  /opt/conda/bin/python3 -m pip install -e .
  /opt/conda/bin/python3 -m triggerctl init --root user
EOF
  exit 1
fi

echo "==> 1/5 Install triggerctl ($PY -m pip install -e)"
echo "    Python: $PY"
"$PY" -m pip install -e "$REPO_DIR" -q

TCTL="$("$PY" - <<'EOF'
import shutil, sys, os
p = shutil.which("triggerctl")
if not p:
    cand = os.path.join(os.path.dirname(sys.executable), "triggerctl")
    p = cand if os.path.exists(cand) else ""
print(p)
EOF
)"
if [ -z "$TCTL" ]; then
  echo "!! triggerctl console script not found; install may have failed" >&2
  exit 1
fi
echo "    triggerctl: $TCTL"

BIN_DIR="${PREFIX_BIN:-}"
if [ -z "$BIN_DIR" ]; then
  if [ -w /usr/local/bin ]; then BIN_DIR=/usr/local/bin; else BIN_DIR="$HOME/.local/bin"; fi
fi
mkdir -p "$BIN_DIR"
if [ "$TCTL" != "$BIN_DIR/triggerctl" ]; then
  ln -sf "$TCTL" "$BIN_DIR/triggerctl"
  echo "    symlink: $BIN_DIR/triggerctl -> $TCTL"
else
  echo "    already on PATH: $TCTL"
fi
case ":$PATH:" in *":$BIN_DIR:"*) :;; *) echo "    ⚠️ $BIN_DIR not on PATH; add it";; esac

echo "==> 2/5 Initialize user triggers root"
"$TCTL" init --root user

echo "==> 3/5 Install triggerctl skill"
mkdir -p "$CLAUDE_DIR/skills/triggerctl"
cp "$REPO_DIR/skill/SKILL.md" "$CLAUDE_DIR/skills/triggerctl/SKILL.md"
echo "    -> $CLAUDE_DIR/skills/triggerctl/SKILL.md"

echo "==> 4/5 Install UserPromptSubmit hook (settings.json)"
"$TCTL" install --hook

echo "==> 5/5 Install statusLine + hook replace env"
"$TCTL" install --statusline
"$PY" - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".claude" / "settings.json"
if not p.exists():
    raise SystemExit(0)
data = json.loads(p.read_text(encoding="utf-8"))
env = data.setdefault("env", {})
env.setdefault("TRIGGERCTL_HOOK_REPLACE", "1")
env.setdefault("TRIGGERCTL_HOOK_JSON", "1")
env.setdefault("TRIGGERCTL_TZ_OFFSET", "8")
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("    set TRIGGERCTL_HOOK_REPLACE=1, TRIGGERCTL_HOOK_JSON=1 in settings env")
PY

cat <<EOF

✅ Done (Python: $PY).
- triggerctl --help
- triggerctl doctor
- triggerctl list
- Optional poll loop: triggerctl install --root user --loop && nohup $CLAUDE_DIR/triggers/run-loop.sh 60 >/dev/null 2>&1 &

Upgrade later:
   $PY -m pip install -e $REPO_DIR

⚠️ Hook/skill/triggers load at session start — open a new Claude session to verify.
EOF
