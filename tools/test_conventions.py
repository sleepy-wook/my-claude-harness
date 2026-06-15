#!/usr/bin/env python3
"""Behavioral tests for the convention system (pointer inject, stale check, gate enforce).

Self-contained: builds throwaway projects and pipes hook events to the real scripts.
Run from the repo root. Exit 0 = all pass.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "claude" / "hooks"
INJECT = str(HOOKS / "inject_convention_pointer.py")
CHECK = str(HOOKS / "check_convention_pointers.py")
GATE = str(HOOKS / "gate_on_commit.py")

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def run(script, cwd, extra=None):
    ev = {"cwd": cwd}
    if extra:
        ev.update(extra)
    p = subprocess.run(
        [sys.executable, script], input=json.dumps(ev), capture_output=True, text=True
    )
    return p.returncode, p.stdout.strip()


def conv_dir(d):
    c = Path(d) / ".claude" / "conventions"
    c.mkdir(parents=True)
    return c


def gate_decision(d):
    # The convention's machine-checkable rule is enforced at COMMIT time now.
    rc, out = run(GATE, d, {"tool_input": {"command": 'git commit -m "x"'}})
    if not out:
        return "allow"
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    return "block" if decision == "deny" else "allow"


print("Test 2 — pointer inject hook")
d = tempfile.mkdtemp(prefix="conv_")
c = conv_dir(d)
(c / "frontend.md").write_text(
    "# f\n- primary · x · src/theme.ts:primary\n", encoding="utf-8"
)
(c / "shared.md").write_text("# shared\n")
rc, out = run(INJECT, d)
check(
    "2a present: exit 0 + mentions shared + frontend",
    rc == 0 and "shared.md" in out and "frontend" in out and "additionalContext" in out,
    True,
)
d2 = tempfile.mkdtemp(prefix="conv_")  # no conventions dir
rc, out = run(INJECT, d2)
check("2b absent: exit 0 + no output", rc == 0 and out == "", True)

print("Test 3 — stale pointer check hook (needs git + code change)")
d = tempfile.mkdtemp(prefix="conv_")
subprocess.run("git init -q", cwd=d, shell=True, check=True)
(Path(d) / "app.py").write_text(
    "def good_fn():\n    return 1\n"
)  # untracked code change
c = conv_dir(d)
(c / "frontend.md").write_text(
    "# f\n- good · ok · app.py:good_fn\n- bad · gone · app.py:missing_fn\n",
    encoding="utf-8",
)
rc, out = run(CHECK, d)
check(
    "3a stale flagged: names missing, not good",
    "missing_fn" in out and "good_fn" not in out,
    True,
)
(c / "frontend.md").write_text(  # drop stale line
    "# f\n- good · ok · app.py:good_fn\n", encoding="utf-8"
)
rc, out = run(CHECK, d)
check("3b all valid: no output", out == "", True)

print("Test 4 — convention rule enforced by the commit gate")
d = tempfile.mkdtemp(prefix="conv_")  # recipe checked when committing
(Path(d) / ".claude").mkdir()
(Path(d) / ".claude" / "evaluate.recipe").write_text(
    "style: ! grep -q RAWHEX app.tsx\n"
)
(Path(d) / "app.tsx").write_text("const c = 'RAWHEX';\n")  # violation
check("4a violation -> block", gate_decision(d), "block")
d = tempfile.mkdtemp(prefix="conv_")
(Path(d) / ".claude").mkdir()
(Path(d) / ".claude" / "evaluate.recipe").write_text(
    "style: ! grep -q RAWHEX app.tsx\n"
)
(Path(d) / "app.tsx").write_text("const c = tokens.primary;\n")  # compliant
check("4b compliant -> allow", gate_decision(d), "allow")

for d in Path(tempfile.gettempdir()).glob("conv_*"):
    shutil.rmtree(d, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
