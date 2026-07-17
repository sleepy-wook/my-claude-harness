#!/usr/bin/env python3
"""Behavioral tests for the convention system (pointer inject, stale warn, gate enforce).

v2: stale-pointer detection moved from a Stop hook into the commit gate
(gate_runner.py, warning-only), and machine-checkable rules are enforced by the
same gate at commit time. Self-contained throwaway projects. Exit 0 = all pass.
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


HOOKS = Path(__file__).resolve().parent.parent / "claude" / "hooks"
INJECT = str(HOOKS / "inject_convention_pointer.py")
GATE = str(HOOKS.parent / "harness" / "gate_runner.py")

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def run_hook(script, cwd, extra=None):
    ev = {"cwd": cwd}
    if extra:
        ev.update(extra)
    p = subprocess.run(
        [sys.executable, "-B", script],
        input=json.dumps(ev),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return p.returncode, p.stdout.strip()


def run_gate(cwd):
    p = subprocess.run(
        [sys.executable, "-B", GATE],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    return p.returncode, p.stdout + p.stderr


def conv_dir(d):
    c = Path(d) / ".claude" / "conventions"
    c.mkdir(parents=True)
    return c


print("Test 2 — pointer inject hook")
d = tempfile.mkdtemp(prefix="conv_")
c = conv_dir(d)
(c / "frontend.md").write_text(
    "# f\n- primary · x · src/theme.ts:primary\n", encoding="utf-8"
)
(c / "shared.md").write_text("# shared\n", encoding="utf-8")
rc, out = run_hook(INJECT, d)
check(
    "2a present: exit 0 + mentions shared + frontend",
    rc == 0 and "shared.md" in out and "frontend" in out and "additionalContext" in out,
    True,
)
d2 = tempfile.mkdtemp(prefix="conv_")  # no conventions dir
rc, out = run_hook(INJECT, d2)
check("2b absent: exit 0 + no output", rc == 0 and out == "", True)

print("Test 3 — stale pointers warned by the commit gate (never blocks)")
d = tempfile.mkdtemp(prefix="conv_")
(Path(d) / ".claude").mkdir()
(Path(d) / ".claude" / "evaluate.recipe").write_text("ok: true\n", encoding="utf-8")
(Path(d) / "app.py").write_text("def good_fn():\n    return 1\n", encoding="utf-8")
c = Path(d) / ".claude" / "conventions"
c.mkdir()
(c / "frontend.md").write_text(
    "# f\n- good · ok · app.py:good_fn\n- bad · gone · app.py:missing_fn\n",
    encoding="utf-8",
)
rc, out = run_gate(d)
check(
    "3a stale flagged but exit 0: names missing, not good",
    rc == 0 and "missing_fn" in out and "good_fn" not in out,
    True,
)
(c / "frontend.md").write_text(  # drop stale line
    "# f\n- good · ok · app.py:good_fn\n", encoding="utf-8"
)
rc, out = run_gate(d)
check("3b all valid: no warning", rc == 0 and "stale" not in out, True)

print("Test 4 — convention rule enforced by the commit gate")
d = tempfile.mkdtemp(prefix="conv_")  # recipe checked when committing
(Path(d) / ".claude").mkdir()
(Path(d) / ".claude" / "evaluate.recipe").write_text(
    "style: ! grep -q RAWHEX app.tsx\n", encoding="utf-8"
)
(Path(d) / "app.tsx").write_text("const c = 'RAWHEX';\n", encoding="utf-8")  # violation
rc, out = run_gate(d)
check("4a violation -> block", rc != 0, True)
d = tempfile.mkdtemp(prefix="conv_")
(Path(d) / ".claude").mkdir()
(Path(d) / ".claude" / "evaluate.recipe").write_text(
    "style: ! grep -q RAWHEX app.tsx\n", encoding="utf-8"
)
(Path(d) / "app.tsx").write_text("const c = tokens.primary;\n", encoding="utf-8")
rc, out = run_gate(d)
check("4b compliant -> allow", rc, 0)

for d in Path(tempfile.gettempdir()).glob("conv_*"):
    shutil.rmtree(d, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
