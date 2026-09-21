#!/usr/bin/env python3
"""Install the wook commit gate as `.git/hooks/pre-commit` in the current repo.

The gate itself is `gate_runner.py` (deployed to ~/.claude/harness/ — canonical on
this machine). This installer writes a
tiny sh shim so the gate is git-native: it fires for every committer (any agent or
human), `--no-verify` bypasses it natively, and no agent-side hook has to parse Bash
commands. `/wook-plan` and `/wook-onboard` run this right after writing a recipe.

Idempotent: re-running upgrades our own shim in place. A pre-existing pre-commit that
is NOT ours is never overwritten — we refuse and tell the developer, because
destroying someone's hook is worse than not installing ours.

Usage:  python ~/.claude/harness/install_gate.py   (from anywhere inside the repo)
"""

import subprocess
import sys
from pathlib import Path

MARKER = "wook-harness commit gate"

SHIM = f"""#!/bin/sh
# {MARKER} (installed by install_gate.py) — runs .claude/evaluate.recipe on commit.
# Bypass: git commit --no-verify   |   Disable: create .claude/evaluate-off
GATE="$HOME/.claude/harness/gate_runner.py"
[ -f "$GATE" ] || exit 0   # harness not deployed on this machine -> never trap
exec python "$GATE"
"""


def main() -> int:
    try:  # our messages are Korean; a cp949 console would raise while printing them
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # --git-common-dir, not --git-dir: in a linked worktree the latter returns
    # `.git/worktrees/<name>`, and git never runs hooks from there — the gate would be
    # installed where nothing executes it (observed 2026-09-21, #30). The common dir is
    # the main `.git`, which is where hooks actually live for every worktree. Falls back
    # to --git-dir on git < 2.5, where the two are always the same anyway.
    git_dir = None
    for flag in ("--git-common-dir", "--git-dir"):
        try:
            out = subprocess.run(
                ["git", "rev-parse", flag],
                capture_output=True,
                text=True,
                encoding="utf-8",  # not the locale default (cp949 raises on non-ascii paths)
                errors="replace",
                timeout=15,
            )
        except Exception as e:
            print(f"install_gate: git not available ({e})")
            return 1
        if out.returncode == 0 and out.stdout.strip():
            git_dir = Path(out.stdout.strip()).resolve()  # may be relative to cwd
            break
    if git_dir is None:
        print("install_gate: not inside a git repository")
        return 1

    hook = git_dir / "hooks" / "pre-commit"
    if hook.exists():
        try:
            existing = hook.read_text(encoding="utf-8")
        except Exception:
            existing = ""
        if MARKER not in existing:
            print(
                f"install_gate: {hook} 이미 존재하고 우리 것이 아님 — 덮어쓰지 않습니다.\n"
                "기존 훅에 다음 줄을 직접 추가하거나 훅을 정리한 뒤 다시 실행하세요:\n"
                '  python "$HOME/.claude/harness/gate_runner.py" || exit 1'
            )
            return 1
        if existing == SHIM:
            print(f"install_gate: up-to-date ({hook})")
            return 0

    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(SHIM, encoding="utf-8", newline="\n")
    try:
        hook.chmod(0o755)
    except Exception:
        pass
    print(f"install_gate: installed ({hook})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
