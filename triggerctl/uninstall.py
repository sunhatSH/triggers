"""Remove triggerctl integration and trigger registry data."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

import yaml

from . import codex, hermes, registry
from .roots import Root

TRIGGERCTL_ENV_KEYS = (
    "TRIGGERCTL_HOOK_REPLACE",
    "TRIGGERCTL_HOOK_JSON",
    "TRIGGERCTL_TZ_OFFSET",
    "TRIGGERCTL_AGENT",
    "TRIGGERCTL_CLAUDE",
    "TRIGGERCTL_HERMES",
    "TRIGGERCTL_CODEX",
    "TRIGGERCTL_CODEX_EXEC_ARGS",
)


@dataclass
class UninstallReport:
    removed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    dry_run: bool = False

    def note_removed(self, msg: str) -> None:
        self.removed.append(msg)

    def note_skipped(self, msg: str) -> None:
        self.skipped.append(msg)


def _is_triggerctl_command(command: str) -> bool:
    cmd = command or ""
    return any(
        token in cmd
        for token in (
            "triggerctl hook",
            "triggerctl hermes-hook",
            "triggerctl codex-hook",
            "triggerctl statusline",
            "triggerctl-pre-llm",
            "triggerctl-user-prompt",
        )
    )


def _unique_roots(roots: List[Root]) -> List[Root]:
    seen: Set[Path] = set()
    out: List[Root] = []
    for root in roots:
        try:
            key = root.path.resolve()
        except OSError:
            key = root.path
        if key in seen:
            continue
        seen.add(key)
        out.append(root)
    return out


def _rmtree(path: Path, rep: UninstallReport) -> None:
    if not path.exists():
        rep.note_skipped(f"not found: {path}")
        return
    if rep.dry_run:
        rep.note_removed(f"would delete: {path}")
        return
    if path.is_symlink():
        path.unlink()
    else:
        shutil.rmtree(path)
    rep.note_removed(f"deleted: {path}")


def _remove_file(path: Path, rep: UninstallReport) -> None:
    if not path.is_file():
        rep.note_skipped(f"not found: {path}")
        return
    if rep.dry_run:
        rep.note_removed(f"would delete: {path}")
        return
    path.unlink()
    rep.note_removed(f"deleted: {path}")


def uninstall_claude(rep: UninstallReport) -> None:
    settings = Path.home() / ".claude" / "settings.json"
    if not settings.is_file():
        rep.note_skipped(f"Claude settings not found: {settings}")
    else:
        data = json.loads(settings.read_text(encoding="utf-8"))
        changed = False

        hooks = data.get("hooks") or {}
        ups = hooks.get("UserPromptSubmit")
        if isinstance(ups, list):
            new_ups = []
            for group in ups:
                if not isinstance(group, dict):
                    new_ups.append(group)
                    continue
                inner = group.get("hooks") or []
                kept = [h for h in inner if not _is_triggerctl_command(str(h.get("command", "")))]
                if kept:
                    new_ups.append({**group, "hooks": kept})
                elif inner:
                    changed = True
                    rep.note_removed("Claude UserPromptSubmit triggerctl hook")
            if new_ups != ups:
                changed = True
                if new_ups:
                    hooks["UserPromptSubmit"] = new_ups
                elif "UserPromptSubmit" in hooks:
                    del hooks["UserPromptSubmit"]

        sl = data.get("statusLine")
        if isinstance(sl, dict) and _is_triggerctl_command(str(sl.get("command", ""))):
            del data["statusLine"]
            changed = True
            rep.note_removed("Claude statusLine (triggerctl)")

        env = data.get("env")
        if isinstance(env, dict):
            for key in TRIGGERCTL_ENV_KEYS:
                if key in env:
                    del env[key]
                    changed = True
                    rep.note_removed(f"Claude env {key}")

        if changed and not rep.dry_run:
            settings.with_suffix(".json.triggerctl.bak").write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            settings.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif changed and rep.dry_run:
            rep.note_removed(f"would update: {settings}")

    skill_dir = Path.home() / ".claude" / "skills" / "triggerctl"
    _rmtree(skill_dir, rep)


def uninstall_hermes(rep: UninstallReport) -> None:
    path, data = hermes.load_config()
    if not path.is_file():
        rep.note_skipped(f"Hermes config not found: {path}")
    else:
        pre = hermes._pre_llm_entries(data)
        kept = [e for e in pre if not _is_triggerctl_command(str(e.get("command", "")))]
        if len(kept) != len(pre):
            hooks = data.setdefault("hooks", {})
            if kept:
                hooks["pre_llm_call"] = kept
            elif "pre_llm_call" in hooks:
                del hooks["pre_llm_call"]
            rep.note_removed("Hermes pre_llm_call triggerctl hook")
            if not rep.dry_run:
                path.with_suffix(path.suffix + ".triggerctl.bak").write_text(
                    path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                path.write_text(
                    yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
                    encoding="utf-8",
                )
        else:
            rep.note_skipped("Hermes pre_llm_call hook not configured")

    _remove_file(hermes.agent_hooks_dir() / "triggerctl-pre-llm.sh", rep)
    _rmtree(hermes.skill_path().parent, rep)

    # Revert cli.py status bar patch if backup exists
    cli_restored = hermes.uninstall_statusline_cli_py()
    if cli_restored:
        rep.note_removed(f"restored Hermes cli.py from backup (triggerctl statusline)")


def uninstall_codex(rep: UninstallReport) -> None:
    path, data = codex.load_hooks()
    if not path.is_file():
        rep.note_skipped(f"Codex hooks.json not found: {path}")
    else:
        groups = codex._user_prompt_submit_groups(data)
        kept = []
        removed_any = False
        for group in groups:
            inner = group.get("hooks") or []
            kept_inner = [
                h
                for h in inner
                if isinstance(h, dict) and not _is_triggerctl_command(str(h.get("command", "")))
            ]
            if kept_inner:
                kept.append({**group, "hooks": kept_inner})
            elif inner:
                removed_any = True
        if removed_any:
            hooks = data.setdefault("hooks", {})
            if kept:
                hooks["UserPromptSubmit"] = kept
            elif "UserPromptSubmit" in hooks:
                del hooks["UserPromptSubmit"]
            rep.note_removed("Codex UserPromptSubmit triggerctl hook")
            if not rep.dry_run:
                path.with_suffix(".json.triggerctl.bak").write_text(
                    path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            rep.note_skipped("Codex UserPromptSubmit hook not configured")

    _remove_file(codex.hooks_dir() / "triggerctl-user-prompt-submit.sh", rep)
    _rmtree(codex.skill_path().parent, rep)


def uninstall_triggers(roots: List[Root], rep: UninstallReport) -> None:
    for root in _unique_roots(roots):
        if registry.strip_claude_session_block(root):
            rep.note_removed(f"legacy CLAUDE.md block: {root.claude_md}")

        if not root.path.is_dir():
            rep.note_skipped(f"triggers root not found: {root.path}")
            continue

        scope = root.kind
        system_dir = root.path / "system-triggers"
        if system_dir.is_dir():
            rep.note_removed(f"{scope} system-triggers: {system_dir}")

        rep.note_removed(f"{scope} triggers root: {root.path}")
        _rmtree(root.path, rep)


def run_uninstall(
    *,
    roots: List[Root],
    agents: str = "all",
    remove_triggers: bool = True,
    remove_integration: bool = True,
    dry_run: bool = False,
) -> UninstallReport:
    rep = UninstallReport(dry_run=dry_run)

    if remove_triggers:
        uninstall_triggers(roots, rep)

    if remove_integration:
        if agents in ("all", "claude"):
            uninstall_claude(rep)
        if agents in ("all", "hermes"):
            uninstall_hermes(rep)
        if agents in ("all", "codex"):
            uninstall_codex(rep)

    return rep
