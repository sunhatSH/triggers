"""Repository layout paths (editable install: repo root is parent of package)."""
from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def skill_source() -> Path:
    return repo_root() / "skill" / "SKILL.md"


def library_dir() -> Path:
    return repo_root() / "library"


def catalog_dir() -> Path:
    """Deprecated alias for library_dir()."""
    return library_dir()
