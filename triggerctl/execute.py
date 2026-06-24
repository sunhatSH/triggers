"""Model execution tier — invoke Claude Code or Hermes to run a DUE trigger body."""
from __future__ import annotations

from typing import List, Optional

from .agents import ExecResult, build_prompt, find_agent_bin, run_prompt
from .model import Trigger

# Re-export for callers/tests.
__all__ = ["ExecResult", "find_claude", "find_hermes", "find_agent_bin", "execute"]


def find_claude() -> Optional[str]:
    from .agents import find_claude as _fc

    return _fc()


def find_hermes() -> Optional[str]:
    from .agents import find_hermes as _fh

    return _fh()


def execute(
    trigger: Trigger,
    claude_bin: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    dry_run: bool = False,
    agent: Optional[str] = None,
) -> ExecResult:
    """Run trigger body via headless agent (claude -p or hermes chat -q)."""
    if claude_bin and not agent:
        agent = "claude"
    elif not agent and not find_agent_bin():
        return ExecResult(False, "", "no agent CLI (claude or hermes) on PATH")

    prompt = build_prompt(trigger.name, trigger.body)
    agent = agent or ("claude" if claude_bin else None)
    return run_prompt(
        prompt,
        trigger.root.base,
        agent=agent,
        extra_args=extra_args,
        dry_run=dry_run,
        claude_bin=claude_bin,
    )
