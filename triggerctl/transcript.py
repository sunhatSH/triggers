"""Experimental transcript surgery for hook context replacement.

Claude Code persists UserPromptSubmit ``additionalContext`` in the session
transcript. Until the platform supports replacement/ephemeral injection, we
can strip prior trigger blocks from the JSONL transcript before each new
injection so only the latest block remains in history.

See docs/proposals/user-prompt-submit-replacement-context.md.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Tuple

from .hookgen import TRIGGER_MARKERS


def line_contains_trigger_marker(line: str) -> bool:
    return any(m in line for m in TRIGGER_MARKERS)


def filter_transcript_lines(lines: Iterable[str]) -> Tuple[list[str], int]:
    """Drop JSONL lines that contain trigger injection markers."""
    kept: list[str] = []
    removed = 0
    for line in lines:
        if line_contains_trigger_marker(line):
            removed += 1
            continue
        kept.append(line)
    return kept, removed


def strip_prior_injections(transcript_path: Path) -> int:
    """Remove prior trigger injection lines from a session transcript.

    Returns the number of lines removed. No-op if the file is missing or empty.
    """
    if not transcript_path.is_file():
        return 0
    text = transcript_path.read_text(encoding="utf-8")
    if not text.strip():
        return 0
    lines = text.splitlines(keepends=True)
    if not any(line_contains_trigger_marker(ln) for ln in lines):
        return 0

    kept, removed = filter_transcript_lines(lines)
    if removed == 0:
        return 0

    parent = transcript_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".triggerctl-", suffix=".jsonl", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines(kept)
        os.replace(tmp_name, transcript_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return removed


def validate_jsonl(path: Path) -> bool:
    """Return True if every non-empty line is valid JSON."""
    if not path.is_file():
        return True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            return False
    return True
