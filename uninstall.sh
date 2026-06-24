#!/usr/bin/env bash
# triggerctl uninstall — remove integration and all trigger registry data.
#
# Usage:  bash uninstall.sh
# Options:
#   AGENT=claude|hermes|all   (default: all)
#   PYTHON=/opt/conda/bin/python3 bash uninstall.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -m triggerctl --help >/dev/null 2>&1; then
      echo "$cand"
      return 0
    fi
  done
  if command -v triggerctl >/dev/null 2>&1; then
    echo ""
    return 0
  fi
  return 1
}

if command -v triggerctl >/dev/null 2>&1; then
  TCTL=triggerctl
elif PY="$(_find_python)" && [ -n "$PY" ]; then
  TCTL="$PY -m triggerctl"
else
  echo "!! triggerctl not found" >&2
  exit 1
fi

echo "==> Uninstall triggerctl (AGENT=$AGENT)"
echo "    Removes user + project + system-triggers data and agent hooks/skills."
echo "    Python package is kept — run: python3 -m pip uninstall triggerctl"
echo

$TCTL uninstall --root all --agent "$AGENT" --yes

cat <<'EOF'

✅ Uninstall complete. Open a new Claude/Hermes session if you had hooks installed.
EOF
