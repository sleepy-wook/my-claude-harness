#!/usr/bin/env python3
"""Behavioral tests for evaluate_gate.py — signature-based triggering.

Core guarantee: the gate runs the recipe ONLY when code changed since the last pass.
A plain question / non-code change after a pass must SKIP (no recipe, no waiting),
even while the tree is dirty — that's the "fires on trivial questions" fix.
Run from the repo root. Exit 0 = all pass.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = str(
    Path(__file__).resolve().parent.parent / "claude" / "hooks" / "evaluate_gate.py"
)
STATE_DIR = Path.home() / ".claude" / "cache" / "eval_gate"
results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} want={want}")


def sh(cmd, cwd):
    subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        shell=isinstance(cmd, str),
    )


def new_repo():
    d = tempfile.mkdtemp(prefix="gate_")
    sh("git init -q", d)
    sh("git config user.email t@t.com", d)
    sh("git config user.name t", d)
    sh("git config commit.gpgsign false", d)
    (Path(d) / ".claude").mkdir()
    (Path(d) / ".claude" / "evaluate.recipe").write_text(
        "gate: test -f PASS\n", encoding="utf-8"
    )
    (Path(d) / "foo.py").write_text("x = 1\n", encoding="utf-8")
    (Path(d) / "PASS").write_text("ok\n", encoding="utf-8")
    sh("git add -A", d)
    sh("git commit -q -m init", d)
    return d


def gate(d):
    p = subprocess.run(
        [sys.executable, GATE],
        input=json.dumps({"cwd": d, "stop_hook_active": False}),
        capture_output=True,
        text=True,
    )
    out = p.stdout.strip()
    if not out:
        return "allow"
    obj = json.loads(out)
    return (
        "block"
        if obj.get("decision") == "block"
        else ("giveup" if "systemMessage" in obj else "allow")
    )


if STATE_DIR.exists():
    shutil.rmtree(STATE_DIR)

print("A — uncommitted code change, recipe FAILS -> block")
d = new_repo()
(Path(d) / "foo.py").write_text("x = 2\n", encoding="utf-8")
(Path(d) / "PASS").unlink()
check("A", gate(d), "block")

print("B — uncommitted code change, recipe PASSES -> allow")
d = new_repo()
(Path(d) / "foo.py").write_text("x = 2\n", encoding="utf-8")
check("B", gate(d), "allow")

print(
    "C — KEY: after a pass, NO code change -> SKIP (allow even though recipe would now fail)"
)
d = new_repo()
(Path(d) / "foo.py").write_text("x = 2\n", encoding="utf-8")
check("C1 first (pass)", gate(d), "allow")
(Path(d) / "PASS").unlink()  # recipe would now FAIL, but this is not a code change
check("C2 skip (no code change)", gate(d), "allow")

print("D — after that, an actual code change -> runs again (now fails -> block)")
(Path(d) / "foo.py").write_text("x = 3\n", encoding="utf-8")  # real code change
check("D", gate(d), "block")

print("E — commit-bypass still caught: edit+commit (clean tree) failing -> block")
d = new_repo()
(Path(d) / "foo.py").write_text("x = 9\n", encoding="utf-8")
(Path(d) / "PASS").unlink()
sh("git add -A", d)
sh("git commit -q -m work", d)
check("E", gate(d), "block")

print("F — non-git project with recipe -> always evaluates (fail -> block)")
d = tempfile.mkdtemp(prefix="gate_nogit_")
(Path(d) / ".claude").mkdir()
(Path(d) / ".claude" / "evaluate.recipe").write_text(
    "gate: test -f PASS\n", encoding="utf-8"
)
check("F", gate(d), "block")

for p in list(Path(tempfile.gettempdir()).glob("gate_*")):
    shutil.rmtree(p, ignore_errors=True)
if STATE_DIR.exists():
    shutil.rmtree(STATE_DIR, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
