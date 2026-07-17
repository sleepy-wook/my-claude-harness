#!/usr/bin/env python3
"""Behavioral tests for the independent-evaluator pieces (reminder hook + allowlist).

remind_evaluator is a PostToolUse(Bash) hook now: it fires ONCE after a real
`git commit`, only when the commit changed >= 30 code lines (below = presumed
trivial, silent). The old Stop version nagged every turn on a dirty tree.
Playwright-MCP evaluation itself can't be unit-tested here (needs live MCP);
these cover the deterministic pieces. Run from the repo root. Exit 0 = all pass.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # gate-executed script contract: our own output must survive a cp949 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


REPO = Path(__file__).resolve().parent.parent
REMIND = str(REPO / "claude" / "hooks" / "remind_evaluator.py")
EVALUATOR = REPO / "claude" / "agents" / "wook-evaluator.md"

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def run_hook(cwd, command):
    ev = {"cwd": cwd, "tool_input": {"command": command}}
    p = subprocess.run(
        [sys.executable, REMIND], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return p.stdout.strip()


def repo_with_commit(fname, n_lines, claude=True):
    """Throwaway git repo whose HEAD is a fresh commit touching fname (n_lines)."""
    d = tempfile.mkdtemp(prefix="eval_")
    subprocess.run("git init -q", cwd=d, shell=True, check=True)
    if claude:
        (Path(d) / ".claude").mkdir()
    (Path(d) / fname).write_text(
        "\n".join(f"x{i} = {i}" for i in range(n_lines)) + "\n", encoding="utf-8"
    )
    subprocess.run(f"git add -A", cwd=d, shell=True, check=True)
    subprocess.run(
        "git -c user.email=t@t -c user.name=t commit -q -m x",
        cwd=d,
        shell=True,
        check=True,
    )
    return d


print("Test — remind_evaluator hook (commit-time, size-gated)")
# A: big frontend commit -> reminds + Playwright
out = run_hook(repo_with_commit("app.tsx", 40), 'git commit -m "x"')
check(
    "A big frontend commit: reminds + Playwright",
    "wook-evaluator" in out and "Playwright" in out,
    True,
)

# B: big backend commit -> reminds, no Playwright clause
out = run_hook(repo_with_commit("api.py", 40), 'git commit -m "x"')
check(
    "B big backend commit: reminds, no Playwright",
    "wook-evaluator" in out and "Playwright" not in out,
    True,
)

# C: tiny commit (< 30 code lines) -> silent (presumed trivial)
check(
    "C tiny commit: silent",
    run_hook(repo_with_commit("api.py", 3), 'git commit -m "x"'),
    "",
)

# D: non-commit command -> silent even with a big fresh commit
check(
    "D non-commit command: silent",
    run_hook(repo_with_commit("api.py", 40), "git status"),
    "",
)

# E: big commit but not harness-aware (no .claude) -> silent
check(
    "E no .claude: silent",
    run_hook(repo_with_commit("api.py", 40, claude=False), 'git commit -m "x"'),
    "",
)

print("Test — evaluator tool allowlist")
txt = EVALUATOR.read_text(encoding="utf-8")
tools_line = next((ln for ln in txt.splitlines() if ln.startswith("tools:")), "")
check("F1 has Playwright MCP", "mcp__playwright__*" in tools_line, True)
check(
    "F2 excludes Edit/Write/WebFetch",
    not any(t in tools_line for t in ("Edit", "Write", "WebFetch")),
    True,
)

for d in Path(tempfile.gettempdir()).glob("eval_*"):
    shutil.rmtree(d, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
