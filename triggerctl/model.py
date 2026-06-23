"""Trigger data model + discovery (scan .md files under a root)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from . import frontmatter
from .roots import Root

SKIP_NAMES = {"TRIGGERS.md", "README.md"}
SKIP_DIRS = {".state", ".git"}


@dataclass
class Trigger:
    name: str
    enabled: bool
    schedule: Optional[dict]
    dedup: Optional[str]
    probe: Optional[str]
    dedup_cmd: Optional[str]
    when: Optional[str]
    locked: bool
    body: str
    path: Path
    root: Root
    meta: dict = field(default_factory=dict)

    @property
    def kind(self) -> str:
        has_s = bool(self.schedule)
        has_p = bool(self.probe)
        has_w = bool(self.when)
        # `when` = 语义条件，由会话内 Agent 判断；轮询器不处理 -> session 型
        if has_w:
            return "session"
        if has_s and has_p:
            return "time+event"
        if has_s:
            return "time"
        if has_p:
            return "event"
        return "invalid"

    @property
    def is_session(self) -> bool:
        return bool(self.when)

    @property
    def valid(self) -> bool:
        return bool(self.name) and self.kind != "invalid"

    @property
    def rel_path(self) -> str:
        try:
            return str(self.path.relative_to(self.root.path))
        except ValueError:
            return str(self.path)

    _EVERY_ZH = {"day": "天", "hour": "小时", "week": "周", "month": "月"}

    def condition_summary(self) -> str:
        parts = []
        if self.when:
            parts.append(f"[会话内] {self.when}")
        if self.schedule:
            every = self.schedule.get("every", "?")
            at = self.schedule.get("at")
            on = self.schedule.get("on")
            seg = "每" + self._EVERY_ZH.get(every, every)
            if on is not None:
                seg += f" {on}"
            if at:
                seg += f" {at}"
            parts.append(seg)
        if self.probe:
            parts.append(f"probe: {self.probe}")
        return " 且 ".join(parts) if parts else "(无条件)"


def _from_file(path: Path, root: Root) -> Optional[Trigger]:
    try:
        meta, body = frontmatter.read_file(path)
    except Exception:
        return None
    name = meta.get("name")
    if not name:
        return None
    return Trigger(
        name=str(name),
        enabled=bool(meta.get("enabled", True)),
        schedule=meta.get("schedule"),
        dedup=meta.get("dedup"),
        probe=meta.get("probe"),
        dedup_cmd=meta.get("dedup_cmd"),
        when=meta.get("when"),
        locked=bool(meta.get("locked", False)),
        body=body,
        path=path,
        root=root,
        meta=meta,
    )


def discover(root: Root) -> List[Trigger]:
    if not root.path.is_dir():
        return []
    out: List[Trigger] = []
    for path in sorted(root.path.rglob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root.path).parts):
            continue
        t = _from_file(path, root)
        if t is not None:
            out.append(t)
    return out


def find(roots: List[Root], name: str) -> Optional[Trigger]:
    for root in roots:
        for t in discover(root):
            if t.name == name:
                return t
    return None
