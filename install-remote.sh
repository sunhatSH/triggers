#!/usr/bin/env bash
# One-line remote install (safe to pipe from curl):
#   curl -fsSL https://raw.githubusercontent.com/sunhatSH/triggers/main/install-remote.sh | bash
#
# Options (env):
#   TRIGGERCTL_BRANCH=main|dev     (default: main)
#   TRIGGERCTL_INSTALL_DIR=...     (default: ~/.local/share/triggerctl/repo)
#   AGENT=claude|hermes|codex|all  (passed to install.sh)
#   PYTHON=... PREFIX_BIN=...
set -euo pipefail

REPO_URL="${TRIGGERCTL_REPO:-https://github.com/sunhatSH/triggers.git}"
BRANCH="${TRIGGERCTL_BRANCH:-main}"
INSTALL_DIR="${TRIGGERCTL_INSTALL_DIR:-${HOME}/.local/share/triggerctl/repo}"

if ! command -v git >/dev/null 2>&1; then
  echo "!! git is required. Install git and retry." >&2
  exit 1
fi

if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "==> Updating ${INSTALL_DIR} (${BRANCH})"
  git -C "${INSTALL_DIR}" fetch --depth 1 origin "${BRANCH}"
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" reset --hard "origin/${BRANCH}"
else
  echo "==> Cloning ${REPO_URL} (${BRANCH}) -> ${INSTALL_DIR}"
  mkdir -p "$(dirname "${INSTALL_DIR}")"
  git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
fi

exec bash "${INSTALL_DIR}/install.sh"
