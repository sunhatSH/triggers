"""Registration roots — where triggers live (analogous to skills' user/project scopes).

- user root:    ~/.claude/triggers          (global, all projects)
- project root: <project>/triggers          (nearest ancestor that has a triggers/ dir,
                                              else <cwd>/triggers)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DIRNAME = "triggers"


@dataclass(frozen=True)
class Root:
    kind: str          # "user" | "project"
    path: Path         # the triggers/ directory

    @property
    def base(self) -> Path:
        """The directory claude should run in for this root (loads its CLAUDE.md)."""
        return Path.home() if self.kind == "user" else self.path.parent

    @property
    def state_dir(self) -> Path:
        return self.path / ".state"

    @property
    def index_file(self) -> Path:
        return self.path / "TRIGGERS.md"

    def __str__(self) -> str:
        return f"{self.kind}:{self.path}"


def user_root() -> Root:
    return Root("user", Path.home() / ".claude" / DIRNAME)


def project_root(start: Optional[Path] = None) -> Root:
    start = Path(start or Path.cwd()).resolve()
    for d in [start, *start.parents]:
        cand = d / DIRNAME
        if cand.is_dir():
            return Root("project", cand)
    return Root("project", start / DIRNAME)


def all_roots(start: Optional[Path] = None) -> List[Root]:
    roots: List[Root] = []
    pr = project_root(start)
    if pr.path.is_dir():
        roots.append(pr)
    ur = user_root()
    if ur.path.is_dir() and ur.path != pr.path:
        roots.append(ur)
    return roots


def resolve(selector: Optional[str], start: Optional[Path] = None) -> List[Root]:
    """selector: None/'all' -> all existing; 'user'; 'project'; or an explicit path."""
    if selector in (None, "all"):
        return all_roots(start)
    if selector == "user":
        return [user_root()]
    if selector == "project":
        return [project_root(start)]
    p = Path(selector).expanduser().resolve()
    if p.name != DIRNAME:
        p = p / DIRNAME
    kind = "user" if p == (Path.home() / ".claude" / DIRNAME) else "project"
    return [Root(kind, p)]


def primary(selector: Optional[str], start: Optional[Path] = None) -> Root:
    """A single root for write commands; defaults to user root."""
    if selector in (None, "user"):
        return user_root()
    return resolve(selector, start)[0]
