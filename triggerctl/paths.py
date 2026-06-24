"""Repository and library layout paths."""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def skill_source() -> Path:
    return repo_root() / "skill" / "SKILL.md"


def local_library_dir() -> Path:
    """Fixed local directory for the trigger library (sync target, default for list/install)."""
    env = os.environ.get("TRIGGERCTL_LIBRARY", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".local" / "share" / "triggerctl" / "library"


def default_library_remote() -> str:
    """Default remote used by `triggerctl fetch` (separate repo from triggerctl)."""
    return os.environ.get("TRIGGERCTL_LIBRARY_REMOTE", "sunhatSH/trigger-library").strip()


def catalog_dir() -> Path:
    """Deprecated alias for local_library_dir()."""
    return local_library_dir()
