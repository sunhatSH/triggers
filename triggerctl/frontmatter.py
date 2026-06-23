"""Parse / dump Markdown files with a YAML frontmatter block.

Format:

    ---
    key: value
    ...
    ---
    <body markdown>
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import yaml

_DELIM = "---"


def parse(text: str) -> Tuple[dict, str]:
    """Return (meta, body). If there is no frontmatter, meta == {}."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _DELIM:
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _DELIM:
            end = i
            break
    if end is None:
        return {}, text
    raw = "\n".join(lines[1:end])
    meta = yaml.safe_load(raw) or {}
    if not isinstance(meta, dict):
        meta = {}
    body = "\n".join(lines[end + 1:])
    # drop a single leading blank line for tidiness
    if body.startswith("\n"):
        body = body[1:]
    return meta, body


def dump(meta: dict, body: str) -> str:
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip("\n")
    body = body.rstrip("\n")
    return f"{_DELIM}\n{fm}\n{_DELIM}\n\n{body}\n"


def read_file(path: Path) -> Tuple[dict, str]:
    return parse(Path(path).read_text(encoding="utf-8"))


def write_file(path: Path, meta: dict, body: str) -> None:
    Path(path).write_text(dump(meta, body), encoding="utf-8")
