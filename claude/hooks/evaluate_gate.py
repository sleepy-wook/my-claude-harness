#!/usr/bin/env python3
"""Stop hook: auto-evaluation gate (the PGE loop, deterministic + recipe-driven).

Fires when Claude finishes a turn. If the project opted in and code changed, it
RUNS the project's verification checks and blocks "done" until they pass. Verdict
is bound to real exit codes.

WHAT TO RUN is not hardcoded per stack — it is data the project declares, so any
stack/domain works and changing stacks just means editing a file:

    .claude/evaluate.recipe         # `name: shell command` per line; exit 0 = pass
        tests: pytest -q
        lint:  ruff check .
        api:   curl -sf http://localhost:8000/health
        db:    python scripts/check_db.py

If no recipe file exists, falls back to auto-detect (python/node) for zero-config.
Recipe commands run via the shell in the project root — only enable in repos you
trust (same trust level as a Makefile / CI config).

Activation (all must hold, else it allows the stop cheaply):
1. `.claude/evaluate-on-stop` marker exists in cwd or an ancestor (opt-in).
   Its optional content is a comma list of check names to enforce on Stop
   (subset of the recipe); empty => all checks.
2. Code changed this session (uncommitted code files; non-git => assumed yes).
3. At least one selected check is runnable.

Runaway / oscillation guard (§0-4): normalized failure SIGNATURE; same signature
STALL_LIMIT times in a row => give up (stuck); changing failure resets stuck but
total attempts cap at MAX_ATTEMPTS. Fresh stop resets the episode. CC's 8-block
cap is a second net. Any internal error allows the stop (never trap the dev).
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

STALL_LIMIT = 3
MAX_ATTEMPTS = 5
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


# ---- running ---------------------------------------------------------------


def run(cmd, cwd: Path) -> tuple[int, str]:
    """Run a check. str => shell command; list => direct exec."""
    shell = isinstance(cmd, str)
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=280, shell=shell
        )
        return p.returncode, (p.stdout + p.stderr)
    except Exception as e:
        return 0, f"(could not run {cmd}: {e})"  # non-blocking


# ---- what to verify --------------------------------------------------------


def load_recipe(root: Path) -> list[tuple[str, str]] | None:
    """Read `.claude/evaluate.recipe` -> [(name, shell_command), ...] or None."""
    f = root / ".claude" / "evaluate.recipe"
    if not f.exists():
        return None
    checks: list[tuple[str, str]] = []
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        name, cmd = s.split(":", 1)
        name, cmd = name.strip(), cmd.strip()
        # strip trailing inline comment that starts with "  #"
        cmd = re.split(r"\s+#", cmd, maxsplit=1)[0].strip()
        if name and cmd:
            checks.append((name, cmd))
    return checks or None


def autodetect(root: Path) -> list[tuple[str, list[str]]]:
    """Fallback when no recipe: detect python/node checks. names: tests|lint."""
    checks: list[tuple[str, list[str]]] = []
    pkg = root / "package.json"
    scripts = {}
    pm = "npm"
    if pkg.exists():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts") or {}
        except Exception:
            pass
        if (root / "pnpm-lock.yaml").exists():
            pm = "pnpm"
        elif (root / "yarn.lock").exists():
            pm = "yarn"
        if "test" in scripts:
            checks.append(("tests", [pm, "test"]))
        if "lint" in scripts:
            checks.append(("lint", [pm, "run", "lint"]))
        return checks

    has_py = any(root.rglob("*.py"))
    has_py_tests = any(root.rglob("test_*.py")) or any(root.rglob("*_test.py"))
    if has_py_tests:
        pytest_ok = run(["python", "-c", "import pytest"], root)[0] == 0
        # -B: ignore stale .pyc so a just-edited file is re-read from source.
        checks.append(
            (
                "tests",
                ["python", "-B", "-m", "pytest", "-q"]
                if pytest_ok
                else ["python", "-B", "-m", "unittest", "discover"],
            )
        )
    if has_py and run(["ruff", "--version"], root)[0] == 0:
        checks.append(("lint", ["ruff", "check", "."]))
    return checks


def get_checks(root: Path) -> list[tuple[str, object]]:
    recipe = load_recipe(root)
    if recipe is not None:
        return list(recipe)
    return list(autodetect(root))


def marker_subset(marker_file: Path) -> set[str] | None:
    try:
        text = marker_file.read_text(encoding="utf-8")
    except Exception:
        return None
    names: set[str] = set()
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        for part in s.split(","):
            part = part.strip()
            if part:
                names.add(part)
    return names or None


# ---- helpers ---------------------------------------------------------------


def find_marker(start: Path) -> Path | None:
    cur = start
    for _ in range(40):
        if (cur / ".claude" / "evaluate-on-stop").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def code_changed(root: Path) -> bool:
    _, out = run(["git", "status", "--porcelain"], root)
    if "fatal:" in out or out.startswith("(could not run"):
        return True
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        if Path(path).suffix.lower() in CODE_EXT:
            return True
    return False


def signature(text: str) -> str:
    norm = re.sub(r"\d+", "N", text)
    norm = re.sub(r"\s+", " ", norm).strip()
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
        return allow()

    if not code_changed(root):
        reset_state(root)
        return allow()

    checks = get_checks(root)
    subset = marker_subset(root / ".claude" / "evaluate-on-stop")
    if subset is not None:
        checks = [c for c in checks if c[0] in subset]
    if not checks:
        return allow()

    if not event.get("stop_hook_active"):
        reset_state(root)

    failures = []
    for name, cmd in checks:
        rc, out = run(cmd, root)
        if rc != 0:
            shown = cmd if isinstance(cmd, str) else " ".join(cmd)
            failures.append((name, shown, out))

    if not failures:
        reset_state(root)
        return allow()

    combined = "\n\n".join(f"[{n}] {c}\n{o}" for n, c, o in failures)
    tail = "\n".join(combined.strip().splitlines()[-30:])
    sig = signature(combined)
    failed = ", ".join(n for n, *_ in failures)

    st = read_state(root)
    attempts = st.get("attempts", 0) + 1
    stuck = st.get("stuck", 0) + 1 if sig == st.get("sig") else 1

    if stuck >= STALL_LIMIT:
        reset_state(root)
        return give_up(
            f"⚠️ auto-evaluate gate: stuck on the SAME failing result {stuck}x in a "
            f"row (no progress) — [{failed}]. Stopping the auto-loop; your turn.\n\n{tail}"
        )
    if attempts >= MAX_ATTEMPTS:
        reset_state(root)
        return give_up(
            f"⚠️ auto-evaluate gate: {MAX_ATTEMPTS} attempts without passing "
            f"[{failed}] — not converging. Stopping the auto-loop; your turn.\n\n{tail}"
        )

    write_state(root, {"attempts": attempts, "sig": sig, "stuck": stuck})
    progress = "same failure" if stuck > 1 else "new failure"
    return block(
        f"Auto-evaluate gate: NOT passing — not done yet (attempt "
        f"{attempts}/{MAX_ATTEMPTS}, {progress}). Failing check(s): [{failed}].\n\n"
        f"{tail}\n\nFix the failure(s) and finish again."
    )


if __name__ == "__main__":
    sys.exit(main())
