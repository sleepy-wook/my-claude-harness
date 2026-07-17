#!/usr/bin/env python3
"""Run every tools/test_*.py with `python -B`; exit 0 iff ALL pass.

The recipe's standing `tests:` line — feature acceptance criteria live as tests so
the recipe converges instead of growing per feature. `-B` avoids stale-.pyc false
results; PYTHONIOENCODING is pinned so Korean output survives cp949 consoles.
"""

import glob
import os
import subprocess
import sys
from pathlib import Path

try:  # gate-executed script contract: our own output must survive a cp949 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


TOOLS = Path(__file__).resolve().parent


def main() -> int:
    tests = sorted(glob.glob(str(TOOLS / "test_*.py")))
    if not tests:
        print("run_tests: no tools/test_*.py found")
        return 1

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    failed = []
    for t in tests:
        name = os.path.basename(t)
        p = subprocess.run(
            [sys.executable, "-B", t],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(TOOLS.parent),
            timeout=240,
        )
        ok = p.returncode == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed.append(name)
            tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-20:])
            print("        " + tail.replace("\n", "\n        "))

    print(f"\nRUN_TESTS: {len(tests) - len(failed)}/{len(tests)} files passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
