#!/usr/bin/env python3
"""Stop hook: auto-evaluation gate (the PGE loop, deterministic).

Fires when Claude finishes a turn. If the project opted in and code changed,
it RUNS the tests and blocks "done" until they pass — so Claude cannot end a
turn claiming success without the tests actually passing. This is the automatic
generate -> evaluate loop, bound to real exit codes.

Activation (all must hold, else it allows the stop immediately and cheaply):
1. A `.claude/evaluate-on-stop` marker exists in the cwd or an ancestor.
2. Code changed this session (uncommitted code files; if not a git repo, assumed yes).
3. A test setup exists (python tests, or a package.json "test" script).

Behaviour:
- Tests pass  -> allow stop (exit 0), reset the retry counter.
- Tests fail  -> {"decision":"block", reason=<failure tail>} so Claude keeps working.
- Failed RETRY_CAP times in a row -> give up, allow stop with a loud systemMessage
  (runaway/oscillation guard, §0-4). Claude Code's own 8-block cap is a second net.
- Any internal error -> allow stop (never trap the developer).

Only TESTS gate here (the core "claimed done without running tests" problem). Lint/
build are available on demand via /evaluate.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RETRY_CAP = 3
CODE_EXT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".php",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".kt",
    ".swift",
}
STATE_DIR = Path.home() / ".claude" / "cache" / "eval_gate"


# ---- helpers ---------------------------------------------------------------


def allow() -> int:
    """Allow the stop (no objection)."""
    return 0


def block(reason: str) -> int:
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    return 0


def give_up(msg: str) -> int:
    sys.stdout.write(json.dumps({"systemMessage": msg}))
    return 0


def find_marker(start: Path) -> Path | None:
    cur = start
    for _ in range(40):  # bounded walk to filesystem root
        if (cur / ".claude" / "evaluate-on-stop").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=280
        )
        return p.returncode, (p.stdout + p.stderr)
    except Exception as e:
        return 0, f"(could not run {' '.join(cmd)}: {e})"  # treat as non-blocking


def code_changed(root: Path) -> bool:
    code, out = run(["git", "status", "--porcelain"], root)
    if "fatal:" in out or out.startswith("(could not run"):
        return True  # not a git repo / git missing -> can't tell, assume yes
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        if Path(path).suffix.lower() in CODE_EXT:
            return True
    return False


def detect_test_command(root: Path) -> list[str] | None:
    """Return the command to run the project's tests, or None if no tests."""
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "test" in (data.get("scripts") or {}):
                pm = "npm"
                if (root / "pnpm-lock.yaml").exists():
                    pm = "pnpm"
                elif (root / "yarn.lock").exists():
                    pm = "yarn"
                return [pm, "test"]
        except Exception:
            pass

    has_py_tests = any(root.rglob("test_*.py")) or any(root.rglob("*_test.py"))
    if has_py_tests:
        pytest_ok, _ = run(["python", "-c", "import pytest"], root)
        if pytest_ok == 0:
            return ["python", "-m", "pytest", "-q"]
        return ["python", "-m", "unittest", "discover"]
    return None


def counter_path(root: Path) -> Path:
    h = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:16]
    return STATE_DIR / f"{h}.count"


def read_counter(root: Path) -> int:
    try:
        return int(counter_path(root).read_text())
    except Exception:
        return 0


def write_counter(root: Path, n: int) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        counter_path(root).write_text(str(n))
    except Exception:
        pass


def reset_counter(root: Path) -> None:
    try:
        counter_path(root).unlink()
    except Exception:
        pass


# ---- main ------------------------------------------------------------------


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return allow()

    cwd = Path(event.get("cwd") or os.getcwd())
    marker_root = find_marker(cwd)
    if marker_root is None:
        return allow()  # gate not enabled here

    if not code_changed(marker_root):
        reset_counter(marker_root)
        return allow()  # nothing to verify

    test_cmd = detect_test_command(marker_root)
    if test_cmd is None:
        return allow()  # no tests to run

    # Fresh stop (not a hook-induced continuation) resets the retry episode.
    if not event.get("stop_hook_active"):
        reset_counter(marker_root)

    rc, out = run(test_cmd, marker_root)
    tail = "\n".join(out.strip().splitlines()[-25:])

    if rc == 0:
        reset_counter(marker_root)
        return allow()  # tests pass -> done is legitimate

    # Tests failed.
    n = read_counter(marker_root) + 1
    write_counter(marker_root, n)
    if n >= RETRY_CAP:
        reset_counter(marker_root)
        return give_up(
            f"⚠️ auto-evaluate gate gave up after {RETRY_CAP} tries — tests still "
            f"failing (`{' '.join(test_cmd)}`). Stopping the auto-loop; your turn.\n\n"
            f"{tail}"
        )
    return block(
        f"Auto-evaluate gate: tests are NOT passing — not done yet "
        f"(attempt {n}/{RETRY_CAP}). Command: `{' '.join(test_cmd)}` exited {rc}.\n\n"
        f"{tail}\n\nFix the failing test(s) and finish again."
    )


if __name__ == "__main__":
    sys.exit(main())
