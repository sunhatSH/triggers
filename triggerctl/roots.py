"""Registration roots — where triggers live (analogous to skills' user/project scopes).

- user root:    ~/.claude/triggers/          (global, all projects)
- project root: <project>/triggers/          (preferred; committed with repo)
                <project>/.claude/triggers/  (only if distinct from user root)

Note: when ~/.claude/triggers is symlinked into a repo's .claude/triggers, that
path is treated as **user** scope only — project scope uses <project>/triggers/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DIRNAME = "triggers"
CLAUDE_DIRNAME = ".claude"


@dataclass(frozen=True)
class Root:
    kind: str          # "user" | "project"
    path: Path         # the triggers/ directory

    @property
    def project_dir(self) -> Path:
        """Project/repo root for project roots; home for user roots."""
        if self.kind == "user":
            return Path.home()
        if self.path.parent.name == CLAUDE_DIRNAME:
            return self.path.parent.parent
        return self.path.parent

    @property
    def base(self) -> Path:
        """Cwd for `claude -p` when executing triggers in this root."""
        return self.project_dir if self.kind == "project" else Path.home()

    @property
    def state_dir(self) -> Path:
        return self.path / ".state"

    @property
    def index_file(self) -> Path:
        return self.path / "TRIGGERS.md"

    @property
    def claude_md(self) -> Path:
        if self.kind == "user":
            return Path.home() / CLAUDE_DIRNAME / "CLAUDE.md"
        return self.project_dir / "CLAUDE.md"

    def __str__(self) -> str:
        return f"{self.kind}:{self.path}"


def user_root() -> Root:
    return Root("user", Path.home() / CLAUDE_DIRNAME / DIRNAME)


def _is_user_triggers_path(path: Path) -> bool:
    try:
        return path.resolve() == user_root().path.resolve()
    except OSError:
        return False


def project_root(start: Optional[Path] = None) -> Root:
    """Nearest project triggers root walking up from *start* (default cwd).

    Prefers ``<repo>/triggers/``. Uses ``<repo>/.claude/triggers/`` only when
    it is **not** the same directory as the user-global root.
    """
    start = Path(start or Path.cwd()).resolve()
    for d in [start, *start.parents]:
        classic = d / DIRNAME
        if classic.is_dir() and not _is_user_triggers_path(classic):
            return Root("project", classic)
        nested = d / CLAUDE_DIRNAME / DIRNAME
        if nested.is_dir() and not _is_user_triggers_path(nested):
            return Root("project", nested)
    return Root("project", start / DIRNAME)


def all_roots(start: Optional[Path] = None) -> List[Root]:
    roots: List[Root] = []
    pr = project_root(start)
    if pr.path.is_dir():
        roots.append(pr)
    ur = user_root()
    try:
        same = ur.path.resolve() == pr.path.resolve()
    except OSError:
        same = ur.path == pr.path
    if ur.path.is_dir() and not same:
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
    kind = "user" if _is_user_triggers_path(p) else "project"
    return [Root(kind, p)]


def primary(selector: Optional[str], start: Optional[Path] = None) -> Root:
    """A single root for write commands; defaults to user root."""
    if selector in (None, "user"):
        return user_root()
    return resolve(selector, start)[0]
