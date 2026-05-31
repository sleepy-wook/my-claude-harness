#!/usr/bin/env python3
"""Stop hook: auto-evaluation gate (the PGE loop, deterministic).

Fires when Claude finishes a turn. If the project opted in and code changed, it
RUNS the configured gates and blocks "done" until they pass — so Claude cannot end
a turn claiming success without the checks actually passing. Verdict is bound to
real exit codes.

Activation (all must hold, else it allows the stop cheaply):
1. A `.claude/evaluate-on-stop` marker exists in the cwd or an ancestor.
2. Code changed this session (uncommitted code files; if not a git repo, assumed yes).
3. At least one configured gate is actually runnable.

Configurable gates (marker file content). Empty marker => tests only. To run more,
put a line in the marker file:
    gates: tests, lint, build
Supported: tests | lint | build. Block if ANY configured+runnable gate fails.

Runaway / oscillation guard (§0-4):
- Each failed turn computes a normalized failure SIGNATURE.
- Same signature repeating STALL_LIMIT times in a row => give up (stuck, no progress).
- Total attempts reaching MAX_ATTEMPTS => give up (not converging) even if changing.
- A fresh stop (not a hook-induced continuation) resets the episode.
- Claude Code's own 8-consecutive-block cap is a second safety net.
On give-up: allow the stop with a loud systemMessage. Any internal error also allows
the stop (never trap the developer).
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

STALL_LIMIT = 3  # same failure this many times in a row -> stuck -> give up
MAX_ATTEMPTS = 5  # absolute cap even if the failure keeps changing
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


# ---- decisions -------------------------------------------------------------


def allow() -> int:
    return 0


def block(reason: str) -> int:
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    return 0


def give_up(msg: str) -> int:
    sys.stdout.write(json.dumps({"systemMessage": msg}))
    return 0


# ---- helpers ---------------------------------------------------------------


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=280
        )
        return p.returncode, (p.stdout + p.stderr)
    except Exception as e:
        return 0, f"(could not run {' '.join(cmd)}: {e})"  # non-blocking


def find_marker(start: Path) -> Path | None:
    cur = start
    for _ in range(40):
        if (cur / ".claude" / "evaluate-on-stop").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def parse_gates(marker_file: Path) -> list[str]:
    try:
        text = marker_file.read_text(encoding="utf-8")
    except Exception:
        return ["tests"]
    for line in text.splitlines():
        s = line.strip().lower()
        if s.startswith("gates:"):
            items = [x.strip() for x in s.split(":", 1)[1].split(",")]
            items = [x for x in items if x in ("tests", "lint", "build")]
            return items or ["tests"]
    return ["tests"]


def code_changed(root: Path) -> bool:
    _, out = run(["git", "status", "--porcelain"], root)
    if "fatal:" in out or out.startswith("(could not run"):
        return True  # not a git repo / git missing -> assume yes
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        if Path(path).suffix.lower() in CODE_EXT:
            return True
    return False


def _node_info(root: Path) -> tuple[bool, dict, str]:
    pkg = root / "package.json"
    if not pkg.exists():
        return False, {}, "npm"
    scripts = {}
    try:
        scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts") or {}
    except Exception:
        pass
    pm = "npm"
    if (root / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (root / "yarn.lock").exists():
        pm = "yarn"
    return True, scripts, pm


def gate_commands(root: Path, gates: list[str]) -> list[tuple[str, list[str]]]:
    """Resolve each requested gate to a runnable command (skip if not applicable)."""
    is_node, scripts, pm = _node_info(root)
    has_py = any(root.rglob("*.py"))
    has_py_tests = any(root.rglob("test_*.py")) or any(root.rglob("*_test.py"))
    ruff_ok = run(["ruff", "--version"], root)[0] == 0

    cmds: list[tuple[str, list[str]]] = []
    for g in gates:
        if g == "tests":
            if is_node and "test" in scripts:
                cmds.append(("tests", [pm, "test"]))
            elif has_py_tests:
                pytest_ok = run(["python", "-c", "import pytest"], root)[0] == 0
                cmds.append(
                    (
                        "tests",
                        # -B: ignore stale .pyc so a just-edited file is always
                        # re-read from source (no bytecode-cache flakiness).
                        ["python", "-B", "-m", "pytest", "-q"]
                        if pytest_ok
                        else ["python", "-B", "-m", "unittest", "discover"],
                    )
                )
        elif g == "lint":
            if is_node and "lint" in scripts:
                cmds.append(("lint", [pm, "run", "lint"]))
            elif ruff_ok and has_py:
                cmds.append(("lint", ["ruff", "check", "."]))
        elif g == "build":
            if is_node and "build" in scripts:
                cmds.append(("build", [pm, "run", "build"]))
            # python: no universal build step -> skip
    return cmds


def signature(text: str) -> str:
    norm = re.sub(r"\d+", "N", text)  # volatile numbers/timings -> N
    norm = re.sub(r"\s+", " ", norm).strip()  # collapse whitespace
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


# ---- per-project episode state --------------------------------------------


def state_path(root: Path) -> Path:
    h = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:16]
    return STATE_DIR / f"{h}.json"


def read_state(root: Path) -> dict:
    try:
        return json.loads(state_path(root).read_text())
    except Exception:
        return {"attempts": 0, "sig": None, "stuck": 0}


def write_state(root: Path, st: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_path(root).write_text(json.dumps(st))
    except Exception:
        pass


def reset_state(root: Path) -> None:
    try:
        state_path(root).unlink()
    except Exception:
        pass


# ---- main ------------------------------------------------------------------


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return allow()

    cwd = Path(event.get("cwd") or os.getcwd())
    root = find_marker(cwd)
    if root is None:
        return allow()  # gate not enabled here

    if not code_changed(root):
        reset_state(root)
        return allow()

    gates = parse_gates(root / ".claude" / "evaluate-on-stop")
    cmds = gate_commands(root, gates)
    if not cmds:
        return allow()  # nothing runnable

    # Fresh stop (user-initiated) starts a new episode.
    if not event.get("stop_hook_active"):
        reset_state(root)

    failures = []
    for name, cmd in cmds:
        rc, out = run(cmd, root)
        if rc != 0:
            failures.append((name, cmd, rc, out))

    if not failures:
        reset_state(root)
        return allow()  # all configured gates pass -> done is legitimate

    combined = "\n\n".join(f"[{n}] {' '.join(c)}\n{o}" for n, c, _, o in failures)
    tail = "\n".join(combined.strip().splitlines()[-30:])
    sig = signature(combined)

    st = read_state(root)
    attempts = st.get("attempts", 0) + 1
    stuck = st.get("stuck", 0) + 1 if sig == st.get("sig") else 1
    failed_gates = ", ".join(n for n, *_ in failures)

    if stuck >= STALL_LIMIT:
        reset_state(root)
        return give_up(
            f"⚠️ auto-evaluate gate: stuck on the SAME failing result "
            f"{stuck}x in a row (no progress) — gate [{failed_gates}]. Stopping the "
            f"auto-loop; your turn.\n\n{tail}"
        )
    if attempts >= MAX_ATTEMPTS:
        reset_state(root)
        return give_up(
            f"⚠️ auto-evaluate gate: {MAX_ATTEMPTS} attempts without passing "
            f"[{failed_gates}] — not converging. Stopping the auto-loop; your turn."
            f"\n\n{tail}"
        )

    write_state(root, {"attempts": attempts, "sig": sig, "stuck": stuck})
    progress = "same failure" if stuck > 1 else "new failure"
    return block(
        f"Auto-evaluate gate: NOT passing — not done yet "
        f"(attempt {attempts}/{MAX_ATTEMPTS}, {progress}). Failing gate(s): "
        f"[{failed_gates}].\n\n{tail}\n\nFix the failure(s) and finish again."
    )


if __name__ == "__main__":
    sys.exit(main())
