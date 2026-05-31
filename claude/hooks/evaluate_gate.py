#!/usr/bin/env python3
"""Stop hook: auto-evaluation gate (the PGE loop, deterministic + recipe-driven).

The gate is ON wherever the project declares a verification recipe — there is NO
separate "enable" step to forget. When Claude finishes a turn and code changed, it
runs the recipe and blocks "done" until every check passes (verdict bound to real
exit codes). This kills the "claimed done without running the checks" failure mode.

  Enable  = create `.claude/evaluate.recipe`  (e.g. via /wook-plan). `name: command`/line:
      tests: pytest -q
      lint:  ruff check .
      api:   curl -sf http://localhost:8000/health
  Disable = create `.claude/evaluate-off`  (escape hatch for a repo/checkout).

Activation (all must hold, else it allows the stop cheaply):
1. `.claude/evaluate-off` does NOT exist (project root or an ancestor).
2. `.claude/evaluate.recipe` exists (its presence = gate active here).
3. Code changed this session (uncommitted code files; non-git => assumed yes).

Runaway/oscillation guard (§0-4): normalized failure signature; same signature
STALL_LIMIT times in a row => give up (stuck); a changing failure resets stuck but
total attempts cap at MAX_ATTEMPTS. A fresh stop resets the episode. Claude Code's
own 8-block cap is a second net. Any internal error allows the stop (never trap the
dev). Recipe commands run via the shell in the project root — only declare commands
you trust (same trust level as a Makefile / CI config).
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


# ---- locating the project --------------------------------------------------


def find_root(start: Path) -> Path:
    """Nearest ancestor that has a `.claude` dir (where the recipe lives), else start."""
    cur = start
    for _ in range(40):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start


def load_recipe(root: Path) -> list[tuple[str, str]] | None:
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
        name, cmd = name.strip(), re.split(r"\s+#", cmd.strip(), maxsplit=1)[0].strip()
        if name and cmd:
            checks.append((name, cmd))
    return checks or None


# ---- running ---------------------------------------------------------------


def run(cmd, cwd: Path) -> tuple[int, str]:
    """str => shell command; list => direct exec."""
    shell = isinstance(cmd, str)
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=280, shell=shell
        )
        return p.returncode, (p.stdout + p.stderr)
    except Exception as e:
        return 0, f"(could not run {cmd}: {e})"  # non-blocking


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
    root = find_root(cwd)

    if (root / ".claude" / "evaluate-off").exists():
        return allow()  # explicitly disabled here

    checks = load_recipe(root)
    if checks is None:
        return allow()  # no recipe => gate not active in this project

    if not code_changed(root):
        reset_state(root)
        return allow()

    if not event.get("stop_hook_active"):
        reset_state(root)

    failures = []
    for name, cmd in checks:
        rc, out = run(cmd, root)
        if rc != 0:
            failures.append((name, cmd, out))

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
