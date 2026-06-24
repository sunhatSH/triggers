"""UserPromptSubmit hook orchestration (stdin JSON → stdout context)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from . import hookgen, transcript


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def read_hook_input() -> Dict[str, Any]:
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except Exception:
        raw = ""
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_hook_output(block: str, *, replace_mode: bool) -> str:
    payload: dict = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": block,
        }
    }
    if replace_mode:
        # Proposed Claude Code field — ignored today; documents intent for upstream PR.
        payload["hookSpecificOutput"]["replacesPrevious"] = True
    return json.dumps(payload, ensure_ascii=False)


def build_hermes_output(block: str) -> str:
    return json.dumps({"context": block}, ensure_ascii=False)


def run_pre_llm_call(data: Dict[str, Any] | None = None) -> int:
    """Emit session trigger context for Hermes pre_llm_call (JSON {\"context\": ...})."""
    _ = data if data is not None else read_hook_input()
    block = hookgen.session_context()
    if not block:
        print("{}")
        return 0
    print(build_hermes_output(block))
    return 0


def run_user_prompt_submit(data: Dict[str, Any] | None = None) -> int:
    """Emit session trigger context for the current user turn."""
    data = data if data is not None else read_hook_input()
    block = hookgen.session_context()
    if not block:
        return 0

    replace_mode = _env_flag("TRIGGERCTL_HOOK_REPLACE")
    use_json = replace_mode or _env_flag("TRIGGERCTL_HOOK_JSON")

    if replace_mode:
        tpath = data.get("transcript_path")
        if tpath:
            try:
                transcript.strip_prior_injections(Path(str(tpath)))
            except OSError as exc:
                print(f"triggerctl: transcript replace failed: {exc}", file=sys.stderr)

    if use_json:
        print(build_hook_output(block, replace_mode=replace_mode))
    else:
        print(block)
    return 0
