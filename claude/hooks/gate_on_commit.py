#!/usr/bin/env python3
"""PreToolUse hook: gate `git commit` on the project's evaluate.recipe.

Deterministic verification runs at COMMIT time — a deliberate "this is a unit" act —
NOT on every turn. So trivial mid-work edits and plain questions never trigger it; the
recipe runs once, when you commit. If any check fails the commit is DENIED (failures fed
back to fix); pass => the commit proceeds.

Activation: tool is Bash and the command is a `git commit` (without `--no-verify`),
`.claude/evaluate.recipe` exists (cwd or ancestor), and `.claude/evaluate-off` does not.
Any error => allow (never trap the dev). `--no-verify` is the explicit escape hatch.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def find_root(start: Path) -> Path:
    cur = start
    for _ in range(40):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start


def load_recipe(root: Path):
    f = root / ".claude" / "evaluate.recipe"
    if not f.exists():
        return None
    checks = []
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


def run(cmd: str, cwd: Path):
    """Run a recipe command via bash where available so POSIX syntax (`!`, globs,
    pipes) behaves the same on every OS; on Windows `shell=True` would use cmd.exe."""
    try:
        bash = shutil.which("bash")
        argv, shell = ([bash, "-c", cmd], False) if bash else (cmd, True)
        p = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, timeout=280, shell=shell
        )
        return p.returncode, (p.stdout + p.stderr)
    except Exception as e:
        return 0, f"(could not run {cmd}: {e})"  # non-blocking


def deny(reason: str) -> int:
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    command = (event.get("tool_input") or {}).get("command") or ""
    if not re.search(r"\bgit\s+commit\b", command):
        return 0  # not a commit -> stay out of the way
    if "--no-verify" in command:
        return 0  # explicit escape hatch

    cwd = Path(event.get("cwd") or os.getcwd())
    root = find_root(cwd)
    if (root / ".claude" / "evaluate-off").exists():
        return 0
    checks = load_recipe(root)
    if checks is None:
        return 0  # no recipe => gate not active here

    failures = []
    for name, cmd in checks:
        rc, out = run(cmd, root)
        if rc != 0:
            failures.append((name, cmd, out))
    if not failures:
        return 0  # all pass -> allow the commit

    combined = "\n\n".join(f"[{n}] {c}\n{o}" for n, c, o in failures)
    tail = "\n".join(combined.strip().splitlines()[-30:])
    failed = ", ".join(n for n, *_ in failures)
    return deny(
        f"Commit gate: checks failing [{failed}] — fix before committing "
        f"(or `git commit --no-verify` to bypass).\n\n{tail}"
    )


if __name__ == "__main__":
    sys.exit(main())
