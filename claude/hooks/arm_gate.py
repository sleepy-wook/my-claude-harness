#!/usr/bin/env python3
"""SessionStart hook: arm the commit gate in a project that declares one.

The harness rule is "`.claude/evaluate.recipe` exists = the gate is ON", but the gate
itself is a git hook, and `.git/hooks/` is machine-local — it is never cloned. So a repo
that has a committed recipe still starts UNGATED on a fresh clone or a new machine, and
every commit until someone remembers `install_gate.py` goes unverified. That is not
hypothetical: this harness repo hit exactly that on 2026-09-21 (#30) — the recipe was
committed, the gate was missing, and the first commits of the session were ungated.

So: at session start, if the project declares a recipe and our shim is not installed,
install it. Silent when it is already ours (the common case — success is silent).

Never blocks a session: no recipe, no git, no repo, any exception -> exit 0 quietly.
A foreign pre-commit hook is never overwritten (install_gate refuses); we relay its
reason once so the developer can decide.
"""

import json
import subprocess
import sys
from pathlib import Path

try:  # our notices are Korean; a cp949 console would raise while printing them
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MARKER = "wook-harness commit gate"
INSTALLER = Path(__file__).resolve().parent.parent / "harness" / "install_gate.py"


def find_recipe_root(start: Path) -> Path | None:
    """Nearest ancestor (incl. start) holding `.claude/evaluate.recipe`."""
    cur = start
    for _ in range(40):
        if (cur / ".claude" / "evaluate.recipe").is_file():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def hooks_dir(root: Path) -> Path | None:
    """The directory git actually runs hooks from (main .git even in a worktree)."""
    for flag in ("--git-common-dir", "--git-dir"):
        out = subprocess.run(
            ["git", "rev-parse", flag],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if out.returncode == 0 and out.stdout.strip():
            p = Path(out.stdout.strip())
            return (root / p if not p.is_absolute() else p).resolve() / "hooks"
    return None


def emit(message: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "systemMessage": message,
                }
            },
            ensure_ascii=False,
        )
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        cwd = Path(event.get("cwd") or ".").resolve()
        root = find_recipe_root(cwd)
        if root is None:
            return 0  # project doesn't declare a gate -> nothing to arm
        hd = hooks_dir(root)
        if hd is None:
            return 0  # not a git repo
        hook = hd / "pre-commit"
        if hook.is_file() and MARKER in hook.read_text(
            encoding="utf-8", errors="replace"
        ):
            return 0  # already armed -> stay silent
        if not INSTALLER.is_file():
            return 0
        out = subprocess.run(
            [sys.executable, "-B", str(INSTALLER)],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        detail = (out.stdout + out.stderr).strip()
        if out.returncode == 0:
            emit(
                "커밋 게이트를 설치했습니다 — 이 repo의 `.claude/evaluate.recipe`가 "
                "이제 매 `git commit`에서 실행됩니다 (우회: `--no-verify`, 끄기: "
                "`.claude/evaluate-off`)."
            )
        elif detail:
            emit(f"커밋 게이트를 설치하지 못했습니다:\n{detail}")
    except Exception:
        return 0  # a session must never fail to start because of this
    return 0


if __name__ == "__main__":
    sys.exit(main())
