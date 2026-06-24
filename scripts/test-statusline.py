#!/usr/bin/env python3
"""Test statusLine output (rest window + too-many-triggers warning).

Usage (from triggerctl repo root):
  python3 scripts/test-statusline.py           # synthetic + live checks
  python3 scripts/test-statusline.py --live    # live environment only
  python3 scripts/test-statusline.py --demo    # print example lines only

Does not modify your trigger registry.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from triggerctl import frontmatter, hookgen  # noqa: E402
from triggerctl.roots import Root  # noqa: E402

SAMPLE = {
    "model": {"display_name": "TestModel"},
    "cwd": "/tmp/demo-proj",
}


def _seed_triggers(root: Path, count: int) -> Root:
    r = Root("project", root)
    r.path.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        frontmatter.write_file(
            r.path / f"t-{i:02d}.md",
            {"name": f"t-{i:02d}", "enabled": True, "when": "always"},
            f"# t-{i:02d}\n",
        )
    return r


def run_synthetic_tests() -> bool:
    print("== Synthetic statusLine tests (temp registry) ==")
    ok = True

    with tempfile.TemporaryDirectory(prefix="triggerctl-statusline-") as tmp:
        over = _seed_triggers(Path(tmp) / "over", 21)
        under = _seed_triggers(Path(tmp) / "under", 3)

        cases = [
            ("too many (21)", over, datetime(2026, 6, 24, 15, 0), True, False),
            ("under threshold (3)", under, datetime(2026, 6, 24, 15, 0), False, False),
            ("rest window", under, datetime(2026, 6, 24, 23, 30), False, True),
            ("rest + too many", over, datetime(2026, 6, 24, 23, 30), True, True),
        ]
        for label, root, now, want_warn, want_rest in cases:
            line = hookgen.statusline(SAMPLE, now=now, roots=[root])
            print(f"  [{label}]")
            print(f"    {line}")
            has_warn = "⚠️" in line
            has_rest = "🌙" in line
            if has_warn == want_warn and has_rest == want_rest:
                print("    PASS")
            else:
                print(
                    f"    FAIL  expected warn={want_warn} rest={want_rest}, "
                    f"got warn={has_warn} rest={has_rest}"
                )
                ok = False

    print()
    return ok


def run_live_checks() -> bool:
    print("== Live environment ==")
    ok = True

    count = hookgen.enabled_trigger_count()
    threshold = hookgen.TOO_MANY_THRESHOLD
    print(f"  context-injected triggers (all roots): {count}  (threshold {threshold})")

    payload = json.dumps(
        {
            "model": {"display_name": "LiveModel"},
            "cwd": str(Path.cwd()),
            "workspace": {"current_dir": str(Path.cwd())},
        }
    )
    cmd = ["triggerctl", "statusline"]
    try:
        subprocess.run(["triggerctl", "--help"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        cmd = [sys.executable, "-m", "triggerctl", "statusline"]

    cp = subprocess.run(cmd, input=payload, text=True, capture_output=True, check=False)
    if cp.returncode != 0:
        print(f"  FAIL  triggerctl statusline exited {cp.returncode}: {cp.stderr.strip()}")
        return False

    line = cp.stdout.strip()
    print(f"  line: {line}")

    has_warn = "⚠️" in line and "triggers" in line
    if count > threshold:
        if has_warn:
            print("  PASS  live statusLine shows too-many warning")
        else:
            print("  FAIL  live statusLine missing too-many warning")
            ok = False
    elif has_warn:
        print("  FAIL  live statusLine shows warning but count is under threshold")
        ok = False
    else:
        print("  PASS  live statusLine has no too-many warning (expected)")

    print()
    return ok


def print_demo() -> None:
    print("== Example statusLine strings ==")
    data = {"model": {"display_name": "Opus"}, "cwd": "/path/sunhao4"}
    with tempfile.TemporaryDirectory() as tmp:
        for label, now, n in [
            ("normal", datetime(2026, 6, 24, 15, 0), 5),
            ("rest window", datetime(2026, 6, 24, 23, 15), 5),
            ("too many", datetime(2026, 6, 24, 15, 0), 23),
            ("rest + too many", datetime(2026, 6, 24, 23, 15), 23),
        ]:
            root = _seed_triggers(Path(tmp) / label, n)
            line = hookgen.statusline(data, now=now, roots=[root])
            print(f"  [{label}]")
            print(f"    {line}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Test triggerctl statusLine output")
    parser.add_argument("--live", action="store_true", help="live checks only")
    parser.add_argument("--demo", action="store_true", help="print example lines")
    args = parser.parse_args()

    if args.demo:
        print_demo()
        return 0

    passed = True
    if not args.live:
        passed = run_synthetic_tests() and passed
    passed = run_live_checks() and passed

    if passed:
        print("All checks passed.")
        return 0
    print("Some checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
