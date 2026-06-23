"""run-log: append-only dedup ledger per root (.state/run-log.jsonl).

Each line: {"name", "key", "ran_at", "result"}
A trigger with the same (name, key) already present is considered done for that
period / event instance.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Set, Tuple

from .roots import Root


def _file(root: Root) -> Path:
    return root.state_dir / "run-log.jsonl"


def load(root: Root) -> List[dict]:
    f = _file(root)
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def done_keys(entries: List[dict]) -> Set[Tuple[str, str]]:
    return {(e.get("name", ""), e.get("key", "")) for e in entries}


def append(root: Root, name: str, key: str, result: str, ran_at: str = None) -> None:
    root.state_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "name": name,
        "key": key,
        "ran_at": ran_at or datetime.now().isoformat(timespec="seconds"),
        "result": result,
    }
    with _file(root).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
