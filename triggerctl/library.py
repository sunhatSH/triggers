"""Trigger library — separate from triggerctl; synced to a fixed local directory."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

from . import package
from .paths import default_library_remote, local_library_dir

DEFAULT_LIBRARY_REMOTE = "sunhatSH/trigger-library"


@dataclass(frozen=True)
class LibraryEntry:
    name: str
    path: str
    kind: str
    category: str
    inject: bool
    description: str


def default_remote() -> str:
    return default_library_remote()


def _load_manifest_yaml(base: Path) -> dict:
    manifest = base / "manifest.yaml"
    if not manifest.is_file():
        return {}
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _entries_from_manifest(base: Path, data: dict) -> List[LibraryEntry]:
    raw = data.get("triggers") or []
    out: List[LibraryEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        rel = str(item.get("path", "")).strip()
        if not name or not rel:
            continue
        if not (base / rel).is_file():
            continue
        out.append(
            LibraryEntry(
                name=name,
                path=rel,
                kind=str(item.get("kind", "-")),
                category=str(item.get("category", "-")),
                inject=bool(item.get("inject", True)),
                description=str(item.get("description", "")).strip(),
            )
        )
    return out


def _entries_from_discover(base: Path) -> List[LibraryEntry]:
    out: List[LibraryEntry] = []
    for tf in package.discover_trigger_files(base):
        rel = str(tf.path.relative_to(base))
        out.append(
            LibraryEntry(
                name=tf.name,
                path=rel,
                kind="-",
                category=tf.category or "-",
                inject=True,
                description="",
            )
        )
    return out


def _replace_tree(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def sync_library(source: Optional[str] = None) -> Path:
    """Copy or clone a library SOURCE into the fixed local library directory."""
    dest = local_library_dir()
    raw = (source or default_remote()).strip()
    spec = package.parse_source(raw)
    if spec.local_path is not None:
        src = spec.local_path
        if spec.subpath:
            src = src / spec.subpath
        if not src.is_dir():
            raise FileNotFoundError(f"Local library path not found: {src}")
        _replace_tree(src, dest)
        return dest
    base, _ = package.materialize(spec)
    _replace_tree(base, dest)
    return dest


def _resolve_base(source: Optional[str]) -> Path:
    """List/install base path: default = fixed local dir; --source = ad-hoc path."""
    if source:
        spec = package.parse_source(source.strip())
        base, _ = package.materialize(spec)
        return base
    dest = local_library_dir()
    if not (dest / "manifest.yaml").is_file() and not any(dest.rglob("*.md")):
        raise FileNotFoundError(
            f"Local library missing at {dest}. Run: triggerctl fetch"
        )
    return dest


def list_entries(source: Optional[str] = None) -> List[LibraryEntry]:
    base = _resolve_base(source)
    data = _load_manifest_yaml(base)
    entries = _entries_from_manifest(base, data)
    if entries:
        return entries
    return _entries_from_discover(base)


def find_entry(name: str, source: Optional[str] = None) -> LibraryEntry:
    for entry in list_entries(source):
        if entry.name == name:
            return entry
    raise KeyError(f"library entry not found: {name}")


def _install_source_for_entry(source: Optional[str], entry: LibraryEntry) -> str:
    if source:
        raw = source.strip()
        spec = package.parse_source(raw)
        if spec.local_path is not None:
            base = spec.local_path
            if spec.subpath:
                base = base / spec.subpath
            return str(base / entry.path)
        label = spec.source
        if spec.subpath:
            label = f"{spec.source}/{spec.subpath}"
        return f"{label}/{entry.path}"
    return str(local_library_dir() / entry.path)


def install_names(
    names: List[str],
    selector: Optional[str],
    force: bool,
    source: Optional[str] = None,
) -> package.InstallResult:
    result = package.InstallResult()
    for name in names:
        try:
            entry = find_entry(name, source)
            part = package.install_from_source(
                _install_source_for_entry(source, entry),
                selector,
                entry.category if entry.category != "-" else None,
                force,
            )
            result.installed.extend(part.installed)
            result.skipped.extend(part.skipped)
            result.errors.extend(part.errors)
        except Exception as e:  # noqa: BLE001
            result.errors.append(f"{name}: {e}")
    return result


def install_all(
    selector: Optional[str],
    force: bool,
    source: Optional[str] = None,
) -> package.InstallResult:
    if source:
        return package.install_from_source(source.strip(), selector, None, force)
    base = _resolve_base(None)
    return package.install_from_source(str(base), selector, None, force)
