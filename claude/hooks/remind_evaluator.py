#!/usr/bin/env python3
"""Stop hook: remind to run the INDEPENDENT evaluator after a real code change.

The problem this solves: the deep, domain-appropriate evaluation lives in the
`wook-evaluator` subagent (the only thing that can drive a browser via Playwright
MCP, hit an API, run a query, etc.) — but that subagent is invoked by *choice*, so
on a busy turn it gets forgotten even after a sizable change. The deterministic
Stop gate can only run shell checks; it cannot drive an MCP/browser evaluation.

So this hook is the deterministic *reminder*: when code changed this turn, it nudges
the author to dispatch the independent evaluator for anything non-trivial — the
author still judges trivial-vs-not (we do NOT mechanically force it), but "forgot"
is removed. Non-blocking (systemMessage), never blocks the stop. Tailors the hint to
the domain that changed (frontend → Playwright MCP visual check).

Activation: a `.claude/` dir exists (cwd or ancestor = harness-aware project) AND
code changed this turn. Any error => silent allow.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

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


def changed_code_exts(root: Path) -> set[str]:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:
        return set()
    if "fatal:" in out:
        return set()
    exts = set()
    for ln in out.splitlines():
        suf = Path(ln[3:].strip().strip('"')).suffix.lower()
        if suf in CODE_EXT:
            exts.add(suf)
    return exts


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    cwd = Path(event.get("cwd") or os.getcwd())
    root = find_claude_root(cwd)
    if root is None:
        return 0  # not a harness-aware project

    exts = changed_code_exts(root)
    if not exts:
        return 0  # no code change this turn

    msg = (
        "You changed code this turn. For anything beyond a trivial edit, do NOT grade "
        "your own work — dispatch the INDEPENDENT evaluator (the wook-evaluator subagent, "
        "e.g. via /wook-evaluate) to verify it in a domain-appropriate way before calling "
        "it done. (You judge trivial-vs-not; skip only if truly trivial.)"
    )
    if exts & FRONTEND_EXT:
        msg += (
            " Frontend changed: have the evaluator drive the Playwright MCP to actually "
            "VIEW the UI (render, key interactions, console errors) — not just check that "
            "commands exit 0."
        )

    sys.stdout.write(json.dumps({"systemMessage": msg}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
