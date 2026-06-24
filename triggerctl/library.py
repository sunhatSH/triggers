"""Official trigger library — list and install optional templates remotely."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

from . import package
from .paths import library_dir

DEFAULT_LIBRARY_SOURCE = "sunhatSH/triggers/library"


@dataclass(frozen=True)
class LibraryEntry:
    name: str
    path: str
    kind: str
    category: str
    inject: bool
    description: str


def default_source() -> str:
    """Default library location (GitHub subpath or local ./library)."""
    env = os.environ.get("TRIGGERCTL_LIBRARY", "").strip()
    if env:
        return env
    local = library_dir()
    if (local / "manifest.yaml").is_file():
        return str(local)
    return DEFAULT_LIBRARY_SOURCE


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


def materialize_library(source: Optional[str] = None) -> Path:
    spec = package.parse_source(source or default_source())
    base, _ = package.materialize(spec)
    return base


def list_entries(source: Optional[str] = None) -> List[LibraryEntry]:
    base = materialize_library(source)
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
    raw = (source or default_source()).strip()
    spec = package.parse_source(raw)
    if spec.local_path is not None:
        return str(spec.local_path / entry.path)
    label = spec.source
    if spec.subpath:
        label = f"{spec.source}/{spec.subpath}"
    return f"{label}/{entry.path}"


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
    return package.install_from_source(source or default_source(), selector, None, force)
