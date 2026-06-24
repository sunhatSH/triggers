"""Orchestrate the two tiers: cheap detect -> (only on DUE) model execute -> run-log.

`poll` is meant to be run frequently (e.g. every minute). Each tick is pure-Python
detection unless something is actually DUE, so high frequency stays cheap.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from . import detect, execute, runlog
from .model import discover
from .roots import Root
from .tz import effective_now


@dataclass
class Outcome:
    root: str
    name: str
    status: str       # due/not-due/deduped/disabled/invalid/error/executed/failed
    key: str
    reason: str
    output: str = ""


@dataclass
class Report:
    started_at: str
    outcomes: List[Outcome] = field(default_factory=list)

    def by_status(self, *statuses):
        return [o for o in self.outcomes if o.status in statuses]

    def summary(self) -> str:
        from collections import Counter
        c = Counter(o.status for o in self.outcomes)
        order = ["executed", "failed", "due", "deduped", "not-due", "disabled", "invalid", "error"]
        bits = [f"{s}={c[s]}" for s in order if c.get(s)]
        return ", ".join(bits) or "无触发器"


def poll(
    roots: List[Root],
    now: Optional[datetime] = None,
    do_execute: bool = True,
    claude_bin: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> Report:
    now = now or effective_now()
    rep = Report(started_at=now.isoformat(timespec="seconds"))

    for root in roots:
        entries = runlog.load(root)
        done = runlog.done_keys(entries)
        for t in discover(root):
            d = detect.evaluate(t, now=now, done=done)
            if not d.due:
                rep.outcomes.append(Outcome(str(root), t.name, d.status, d.key, d.reason))
                continue

            if not do_execute:
                rep.outcomes.append(Outcome(str(root), t.name, "due", d.key, d.reason))
                continue

            res = execute.execute(t, claude_bin=claude_bin, extra_args=extra_args)
            result_str = "ok" if res.ok else f"error: {res.detail}"
            runlog.append(root, t.name, d.key, result_str)
            done.add((t.name, d.key))
            rep.outcomes.append(
                Outcome(
                    str(root),
                    t.name,
                    "executed" if res.ok else "failed",
                    d.key,
                    res.detail,
                    output=res.output[:500],
                )
            )

    return rep
