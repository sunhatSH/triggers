#!/usr/bin/env bash
# triggerctl install — embed triggers into Claude Code, Hermes Agent, and/or Codex CLI.
#
# 1) Install triggerctl (editable) with a Python that has pip; link onto PATH
# 2) Initialize user registry (includes default guardrail trigger)
# 3) Install triggerctl skill + hooks per agent
#
# Usage:  bash install.sh
# Options:
#   AGENT=claude|hermes|codex|all   (default: all)
#   PYTHON=/opt/conda/bin/python3 bash install.sh
#   PREFIX_BIN=~/.local/bin bash install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
AGENT="${AGENT:-all}"

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

echo "==> Install triggerctl ($PY -m pip install -e)"
echo "    Python: $PY"
echo "    AGENT: $AGENT"
# macOS CLT Python often ships pip 21.x, which cannot do pyproject-only editable installs.
"$PY" -m pip install --upgrade pip setuptools wheel -q
if ! "$PY" -m pip install -e "$REPO_DIR" -q; then
  cat >&2 <<EOF
!! pip editable install failed.

Try upgrading pip manually, then re-run install.sh:
  $PY -m pip install --upgrade pip setuptools wheel
  $PY -m pip install -e "$REPO_DIR"

Or point at a newer Python (3.10+ recommended):
  PYTHON=/path/to/python3 bash install.sh
EOF
  exit 1
fi

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

echo "==> Initialize user triggers root"
"$TCTL" init --root user

echo "==> Sync trigger library (optional templates, not auto-installed)"
if "$TCTL" fetch; then
  echo "    library -> $("$PY" - <<'PY'
from pathlib import Path
print(Path.home() / ".local/share/triggerctl/library")
PY
)"
else
  echo "    ⚠️ fetch failed (offline?). Retry: triggerctl fetch"
fi

install_claude() {
  echo "==> Claude Code: skill + UserPromptSubmit hook + statusLine"
  mkdir -p "$CLAUDE_DIR/skills/triggerctl"
  cp "$REPO_DIR/skill/SKILL.md" "$CLAUDE_DIR/skills/triggerctl/SKILL.md"
  echo "    skill -> $CLAUDE_DIR/skills/triggerctl/SKILL.md"
  "$TCTL" install --hook
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
print("    env: TRIGGERCTL_HOOK_REPLACE=1, TRIGGERCTL_HOOK_JSON=1, TRIGGERCTL_TZ_OFFSET=8")
PY
}

install_hermes() {
  echo "==> Hermes Agent: skill + pre_llm_call hook"
  "$TCTL" install --hermes
}

install_codex() {
  echo "==> Codex CLI: skill + UserPromptSubmit hook"
  "$TCTL" install --codex
}

case "$AGENT" in
  claude) install_claude ;;
  hermes) install_hermes ;;
  codex) install_codex ;;
  all) install_claude; install_hermes; install_codex ;;
  *)
    echo "!! Unknown AGENT=$AGENT (use claude, hermes, codex, or all)" >&2
    exit 1
    ;;
esac

cat <<EOF

✅ Done (Python: $PY, AGENT: $AGENT).
- triggerctl --help
- triggerctl doctor
- triggerctl list
- Optional poll loop: triggerctl install --root user --loop && nohup $CLAUDE_DIR/triggers/run-loop.sh 60 >/dev/null 2>&1 &

Upgrade later:
   $PY -m pip install -e $REPO_DIR

⚠️ Start a new Claude, Hermes, and/or Codex session to verify hooks and skills.
EOF
