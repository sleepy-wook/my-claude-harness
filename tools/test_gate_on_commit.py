#!/usr/bin/env python3
"""Behavioral tests for gate_on_commit.py (PreToolUse) — fires only on `git commit`.

Core: the recipe runs at COMMIT time, not every turn. So a `git commit` with a failing
recipe is DENIED; a non-commit command, a passing recipe, `--no-verify`, or no recipe all
pass through untouched. Run from the repo root. Exit 0 = all pass.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = str(
    Path(__file__).resolve().parent.parent / "claude" / "hooks" / "gate_on_commit.py"
)
results = []

_spec = importlib.util.spec_from_file_location("gate_on_commit", HOOK)
gmod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gmod)


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} want={want}")


def proj(recipe=True, passing=True):
    d = tempfile.mkdtemp(prefix="commitgate_")
    (Path(d) / ".claude").mkdir()
    if recipe:
        (Path(d) / ".claude" / "evaluate.recipe").write_text(
            "gate: test -f PASS\n", encoding="utf-8"
        )
    if passing:
        (Path(d) / "PASS").write_text("ok\n", encoding="utf-8")
    return d


def hook(d, command):
    ev = {"cwd": d, "tool_input": {"command": command}}
    p = subprocess.run(
        [sys.executable, HOOK], input=json.dumps(ev), capture_output=True, text=True
    )
    out = p.stdout.strip()
    if not out:
        return "allow"
    return (
        "deny"
        if json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
        else "allow"
    )


check(
    "A git commit + failing recipe -> deny",
    hook(proj(passing=False), 'git commit -m "x"'),
    "deny",
)
check(
    "B git commit + passing recipe -> allow",
    hook(proj(passing=True), 'git commit -m "x"'),
    "allow",
)
check("C non-commit command -> allow", hook(proj(passing=False), "git status"), "allow")
check(
    "D --no-verify bypass -> allow",
    hook(proj(passing=False), 'git commit --no-verify -m "x"'),
    "allow",
)
check(
    "E no recipe -> allow",
    hook(proj(recipe=False, passing=False), 'git commit -m "x"'),
    "allow",
)
check(
    "F commit in && chain, failing -> deny",
    hook(proj(passing=False), 'git add -A && git commit -m "x"'),
    "deny",
)

# G: the WSL launcher (%WINDIR%\System32\bash.exe) must be REJECTED — running the
# recipe through WSL breaks every check on Windows. With no Git Bash on this machine,
# find_bash must return None rather than the System32 stub.
_orig_which, _orig_windir = shutil.which, os.environ.get("WINDIR")
try:
    os.environ["WINDIR"] = r"C:\Windows"
    shutil.which = lambda name: r"C:\Windows\System32\bash.exe"
    check("G find_bash rejects WSL System32 stub", gmod.find_bash(), None)
finally:
    shutil.which = _orig_which
    if _orig_windir is None:
        os.environ.pop("WINDIR", None)
    else:
        os.environ["WINDIR"] = _orig_windir

for p in Path(tempfile.gettempdir()).glob("commitgate_*"):
    shutil.rmtree(p, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
