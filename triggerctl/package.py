"""Install triggers from git repos or local paths (skills add parity)."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import frontmatter, lockfile, registry
from .model import SKIP_DIRS, SKIP_NAMES
from .roots import Root, primary

GITHUB_SHORT = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/(.*))?$")


@dataclass(frozen=True)
class SourceSpec:
    source: str          # canonical id for lock file
    subpath: str         # path inside repo or local tree
    git_url: Optional[str]
    local_path: Optional[Path]


@dataclass
class TriggerFile:
    path: Path
    name: str
    category: Optional[str]


@dataclass
class InstallResult:
    installed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def parse_source(raw: str) -> SourceSpec:
    raw = raw.strip().rstrip("/")
    if not raw:
        raise ValueError("source 不能为空")

    p = Path(raw).expanduser()
    if p.exists() or raw.startswith((".", "/")) or raw.startswith("~"):
        resolved = p.resolve()
        return SourceSpec(str(resolved), "", None, resolved)

    if raw.startswith("git@"):
        return SourceSpec(raw, "", raw, None)

    if raw.startswith("http://") or raw.startswith("https://"):
        return SourceSpec(raw, "", raw, None)

    m = GITHUB_SHORT.match(raw)
    if m:
        owner_repo = m.group(1)
        subpath = (m.group(2) or "").strip("/")
        url = f"https://github.com/{owner_repo}.git"
        return SourceSpec(owner_repo, subpath, url, None)

    raise ValueError(f"无法解析 source: {raw}")


def _cache_dir(spec: SourceSpec) -> Path:
    base = Path.home() / ".claude" / "triggers" / ".cache" / "repos"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", spec.source)
    return base / safe


def _run_git(args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def materialize(spec: SourceSpec) -> Tuple[Path, Optional[str]]:
    """Return (resolved tree root for browsing, commit hash or None for local)."""
    if spec.local_path is not None:
        if spec.local_path.is_file():
            return spec.local_path, None
        base = spec.local_path
        if spec.subpath:
            base = base / spec.subpath
        if not base.exists():
            raise FileNotFoundError(f"本地路径不存在: {base}")
        return base, None

    if not spec.git_url:
        raise ValueError(f"缺少 git URL: {spec.source}")

    cache = _cache_dir(spec)
    if cache.exists() and (cache / ".git").exists():
        cp = _run_git(["fetch", "--depth", "1", "origin"], cache)
        if cp.returncode != 0:
            shutil.rmtree(cache, ignore_errors=True)
        else:
            _run_git(["reset", "--hard", "origin/HEAD"], cache)
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cp = _run_git(["clone", "--depth", "1", spec.git_url, str(cache)])
        if cp.returncode != 0:
            err = (cp.stderr or cp.stdout or "").strip()
            raise RuntimeError(f"git clone 失败: {err}")

    head = _run_git(["rev-parse", "HEAD"], cache)
    commit = head.stdout.strip() if head.returncode == 0 else None
    base = cache / spec.subpath if spec.subpath else cache
    if not base.exists():
        raise FileNotFoundError(f"仓库内路径不存在: {spec.subpath or '/'}")
    return base, commit


def discover_trigger_files(base: Path) -> List[TriggerFile]:
    if base.is_file():
        if base.suffix.lower() != ".md":
            raise ValueError(f"不是 .md 触发器文件: {base}")
        meta, _ = frontmatter.read_file(base)
        name = meta.get("name")
        if not name:
            raise ValueError(f"缺少 frontmatter name: {base}")
        return [TriggerFile(base, str(name), _category_from_path(base.parent))]

    out: List[TriggerFile] = []
    for path in sorted(base.rglob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        rel_parts = path.relative_to(base).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        try:
            meta, _ = frontmatter.read_file(path)
        except Exception:
            continue
        name = meta.get("name")
        if not name:
            continue
        out.append(TriggerFile(path, str(name), _category_from_path(path.parent)))
    return out


def _category_from_path(folder: Path) -> Optional[str]:
    name = folder.name
    if name.endswith("-triggers"):
        return name[: -len("-triggers")]
    return None


def list_available(source: str) -> List[TriggerFile]:
    spec = parse_source(source)
    base, _ = materialize(spec)
    return discover_trigger_files(base)


def resolves_to_single_file(source: str) -> bool:
    """True when SOURCE points at one .md file (not a directory/repo root)."""
    spec = parse_source(source)
    if spec.local_path is not None:
        target = spec.local_path
        if spec.subpath:
            target = target / spec.subpath
        return target.is_file()
    if spec.subpath and spec.subpath.lower().endswith(".md"):
        return True
    base, _ = materialize(spec)
    return base.is_file()


def _dest_folder(root: Root, category: Optional[str], src_category: Optional[str]) -> Path:
    cat = category or src_category or "installed"
    return root.path / f"{cat}-triggers"


def install_from_source(
    source: str,
    selector: Optional[str],
    category: Optional[str],
    force: bool,
) -> InstallResult:
    spec = parse_source(source)
    base, commit = materialize(spec)
    root = primary(selector)
    root.path.mkdir(parents=True, exist_ok=True)
    files = discover_trigger_files(base)
    if not files:
        raise ValueError(f"在 {base} 未找到触发器 .md 文件")

    result = InstallResult()
    installed_map: Dict[str, str] = {}
    for tf in files:
        folder = _dest_folder(root, category, tf.category)
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f"{tf.name}.md"
        if dest.exists() and not force:
            result.skipped.append(tf.name)
            continue
        shutil.copy2(tf.path, dest)
        try:
            rel = str(dest.relative_to(root.path))
        except ValueError:
            rel = str(dest)
        installed_map[tf.name] = rel
        result.installed.append(tf.name)

    if installed_map:
        lockfile.upsert_package(
            root,
            {
                "source": spec.source,
                "subpath": spec.subpath,
                "commit": commit,
                "root": root.kind,
                "installed_at": lockfile.now_iso(),
                "triggers": installed_map,
            },
        )
        registry.sync(root)
    return result


def update_packages(selector: Optional[str], force: bool) -> InstallResult:
    from .roots import resolve

    result = InstallResult()
    for root in resolve(selector):
        for pkg in lockfile.list_packages(root):
            subpath = pkg.get("subpath", "")
            src = pkg.get("source", "")
            if not src:
                continue
            label = f"{src}/{subpath}" if subpath else src
            try:
                part = install_from_source(label, root.kind, None, force)
                result.installed.extend(part.installed)
                result.skipped.extend(part.skipped)
                result.errors.extend(part.errors)
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"{label}: {e}")
    return result
