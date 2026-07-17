#!/usr/bin/env python3
"""PostToolUse hook: after a git commit, remind ONCE to run the independent evaluator.

Why commit-time, not Stop-time: the old Stop version keyed on a dirty tree, so it
nagged EVERY turn while work was uncommitted — pushing a 2-3 minute evaluator
dispatch into every wrap-up. A commit is the deliberate "this is a unit" moment
(same reasoning as the commit gate, #16), so the nudge fires exactly once there,
and only when the commit is big enough to plausibly be non-trivial. Small commits
stay silent (success is silent; the developer still judges trivial-vs-not — this
only removes "forgot", it never forces).

Activation: tool is Bash, the command ran a `git commit`, HEAD is a fresh commit
(committed within the last 5 minutes — a denied/failed commit leaves HEAD stale),
a `.claude/` dir exists, and the commit changed >= MIN_CODE_LINES lines of code.
Non-blocking (systemMessage). Any error => silent.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

MIN_CODE_LINES = 30  # below this, the commit is presumed trivial -> stay silent

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
    ".sql",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".vue",
    ".svelte",
    ".astro",
}
FRONTEND_EXT = {
    ".tsx",
    ".jsx",
    ".vue",
    ".svelte",
    ".astro",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
}


def find_claude_root(start: Path) -> Path | None:
    cur = start
    for _ in range(40):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def git(root: Path, *args: str) -> str:
    """UTF-8, not the locale default — a Korean commit message or path would otherwise
    raise UnicodeDecodeError on Windows (cp949) and kill the reminder."""
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    ).stdout


def head_is_fresh(root: Path) -> bool:
    """True if HEAD was committed in the last 5 min — i.e. this command really
    produced a commit (a denied/failed commit leaves an older HEAD)."""
    ts = git(root, "log", "-1", "--format=%ct").strip()
    return ts.isdigit() and (time.time() - int(ts)) < 300


def commit_code_stats(root: Path):
    """(code lines changed, set of code exts) for the HEAD commit."""
    lines, exts = 0, set()
    for row in git(root, "show", "--numstat", "--format=", "HEAD").splitlines():
        parts = row.split("\t")
        if len(parts) != 3:
            continue
        ins, dels, path = parts
        suf = Path(path.strip().strip('"')).suffix.lower()
        if suf not in CODE_EXT:
            continue
        exts.add(suf)
        for n in (ins, dels):
            if n.isdigit():
                lines += int(n)
    return lines, exts


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    command = (event.get("tool_input") or {}).get("command") or ""
    if not re.search(r"\bgit\s+commit\b", command):
        return 0  # not a commit -> silent

    cwd = Path(event.get("cwd") or os.getcwd())
    root = find_claude_root(cwd)
    if root is None:
        return 0  # not a harness-aware project

    try:
        if not head_is_fresh(root):
            return 0  # the commit didn't actually land
        lines, exts = commit_code_stats(root)
    except Exception:
        return 0
    if lines < MIN_CODE_LINES:
        return 0  # presumed trivial -> silent

    msg = (
        f"This commit changed ~{lines} lines of code. For a change this size, do NOT "
        "grade your own work — consider dispatching the INDEPENDENT evaluator "
        "(wook-evaluator, e.g. via /wook-evaluate) to verify it in a domain-appropriate "
        "way before calling it done. (You still judge trivial-vs-not.)"
    )
    if exts & FRONTEND_EXT:
        msg += (
            " Frontend changed: have the evaluator drive the Playwright MCP to actually "
            "VIEW the UI (render, key interactions, console errors) — not just exit codes."
        )

    sys.stdout.write(json.dumps({"systemMessage": msg}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
