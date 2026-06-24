"""triggers-lock.json — track triggers installed from external sources (skills parity)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .roots import Root

LOCK_NAME = "triggers-lock.json"
VERSION = 1


def path_for(root: Root) -> Path:
    return root.path / LOCK_NAME


def load(root: Root) -> dict:
    p = path_for(root)
    if not p.exists():
        return {"version": VERSION, "packages": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"version": VERSION, "packages": []}
    if not isinstance(data, dict):
        return {"version": VERSION, "packages": []}
    data.setdefault("version", VERSION)
    data.setdefault("packages", [])
    return data


def save(root: Root, data: dict) -> None:
    root.path.mkdir(parents=True, exist_ok=True)
    data["version"] = VERSION
    path_for(root).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def upsert_package(root: Root, entry: dict) -> None:
    data = load(root)
    packages: List[dict] = data["packages"]
    key = (entry.get("source"), entry.get("subpath", ""))
    packages[:] = [p for p in packages if (p.get("source"), p.get("subpath", "")) != key]
    packages.append(entry)
    save(root, data)


def list_packages(root: Root) -> List[dict]:
    return list(load(root).get("packages", []))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def merge_triggers(existing: Dict[str, str], new: Dict[str, str]) -> Dict[str, str]:
    out = dict(existing or {})
    out.update(new)
    return out
