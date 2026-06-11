#!/usr/bin/env python3
"""Behavioral tests for the independent-evaluator changes (reminder hook + tool allowlist).

Note: the actual Playwright-MCP visual evaluation can't be unit-tested here (needs a live
MCP server + browser + app) — that part is verified by a live trial after deploy. These
tests cover the deterministic pieces: the reminder hook and the evaluator's tool allowlist.
Run from the repo root. Exit 0 = all pass.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REMIND = str(REPO / "claude" / "hooks" / "remind_evaluator.py")
EVALUATOR = REPO / "claude" / "agents" / "wook-evaluator.md"

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def run(script, cwd):
    p = subprocess.run(
        [sys.executable, script],
        input=json.dumps({"cwd": cwd}),
        capture_output=True,
        text=True,
    )
    return p.stdout.strip()


def gitrepo(claude=True):
    d = tempfile.mkdtemp(prefix="eval_")
    subprocess.run("git init -q", cwd=d, shell=True, check=True)
    if claude:
        (Path(d) / ".claude").mkdir()
    return d


print("Test — remind_evaluator hook")
# A: frontend file changed -> reminder mentions Playwright
d = gitrepo()
(Path(d) / "app.tsx").write_text("export const A = () => <div/>;\n")
out = run(REMIND, d)
check(
    "A frontend: reminds + Playwright",
    "wook-evaluator" in out and "Playwright" in out,
    True,
)

# B: backend file changed -> reminder, but no Playwright clause
d = gitrepo()
(Path(d) / "api.py").write_text("def handler():\n    return 1\n")
out = run(REMIND, d)
check(
    "B backend: reminds, no Playwright",
    "wook-evaluator" in out and "Playwright" not in out,
    True,
)

# C: no code change (only a .md under .claude) -> silent
d = gitrepo()
(Path(d) / ".claude" / "notes.md").write_text("# notes\n")
check("C no code change: silent", run(REMIND, d), "")

# D: code changed but project is not harness-aware (no .claude) -> silent
d = gitrepo(claude=False)
(Path(d) / "app.py").write_text("x = 1\n")
check("D no .claude: silent", run(REMIND, d), "")

print("Test — evaluator tool allowlist")
txt = EVALUATOR.read_text(encoding="utf-8")
tools_line = next((ln for ln in txt.splitlines() if ln.startswith("tools:")), "")
check("E1 has Playwright MCP", "mcp__playwright__*" in tools_line, True)
check(
    "E2 excludes Edit/Write/WebFetch",
    not any(t in tools_line for t in ("Edit", "Write", "WebFetch")),
    True,
)

for d in Path(tempfile.gettempdir()).glob("eval_*"):
    shutil.rmtree(d, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
