#!/usr/bin/env python3
"""Behavioral tests for gate_runner.py — the git pre-commit commit gate (v2).

Covers: recipe pass/fail, no-recipe/evaluate-off passthrough, self-protection
(staged recipe change / test deletion blocked unless GATE_EDIT_OK=1), stall
detection (same failure 3x switches the message), and pointer-freshness warnings
that never block. Self-contained throwaway git repos. Exit 0 = all pass.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNER = str(
    Path(__file__).resolve().parent.parent / "claude" / "harness" / "gate_runner.py"
)
results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def repo(recipe="gate: test -f PASS\n", passing=True, git=True):
    d = Path(tempfile.mkdtemp(prefix="gaterun_"))
    if git:
        subprocess.run(["git", "init", "-q"], cwd=d, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=d, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    (d / ".claude").mkdir()
    if recipe is not None:
        (d / ".claude" / "evaluate.recipe").write_text(recipe, encoding="utf-8")
    if passing:
        (d / "PASS").write_text("ok\n", encoding="utf-8")
    return d


def gate(d, env_extra=None):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env.pop("GATE_EDIT_OK", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        [sys.executable, "-B", RUNNER],
        cwd=str(d),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )
    return p.returncode, p.stdout + p.stderr


def commit_all(d, msg="init"):
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    subprocess.run(["git", "commit", "-q", "--no-verify", "-m", msg], cwd=d, check=True)


print("Test A-F — recipe execution basics")
rc, out = gate(repo(passing=True))
check("A passing recipe -> 0", rc, 0)
d = repo(passing=False)
rc, out = gate(d)
check("B failing recipe -> nonzero + names check", rc != 0 and "gate" in out, True)
rc, out = gate(repo(recipe=None))
check("C no recipe -> 0", rc, 0)
d = repo(passing=False)
(d / ".claude" / "evaluate-off").write_text("", encoding="utf-8")
rc, out = gate(d)
check("D evaluate-off -> 0", rc, 0)
rc, out = gate(repo(recipe="ok: true\n", passing=False))
check("E POSIX builtin via bash -> 0", rc, 0)
d = repo(recipe="ok: true\n", git=False)
rc, out = gate(d)
check("F no git dir -> still runs recipe (0)", rc, 0)

print("Test G-J — self-protection (gate-weakening commits)")
d = repo(recipe="ok: true\n")
commit_all(d)  # recipe now tracked
(d / ".claude" / "evaluate.recipe").write_text(
    "ok: true\n# weakened\n", encoding="utf-8"
)
subprocess.run(["git", "add", "-A"], cwd=d, check=True)
rc, out = gate(d)
check("G staged recipe edit -> blocked + hint", rc != 0 and "GATE_EDIT_OK" in out, True)
rc, out = gate(d, {"GATE_EDIT_OK": "1"})
check("H GATE_EDIT_OK=1 -> allowed", rc, 0)
d = repo(recipe="ok: true\n")
(d / "test_thing.py").write_text("def test_x():\n    pass\n", encoding="utf-8")
commit_all(d)
subprocess.run(["git", "rm", "-q", "test_thing.py"], cwd=d, check=True)
rc, out = gate(d)
check("I staged test deletion -> blocked", rc != 0 and "GATE_EDIT_OK" in out, True)
d = repo(recipe=None)  # adding a recipe for the first time = arming, not weakening
(d / ".claude" / "evaluate.recipe").write_text("ok: true\n", encoding="utf-8")
subprocess.run(["git", "add", "-A"], cwd=d, check=True)
rc, out = gate(d)
check("J staged recipe ADD -> allowed", rc, 0)

print("Test K-L — stall detection")
d = repo(passing=False)
gate(d)
gate(d)
rc, out = gate(d)
check("K same failure 3x -> stall message", rc != 0 and "STALL" in out, True)
(d / "PASS").write_text("ok\n", encoding="utf-8")
rc, out = gate(d)
state = Path(
    subprocess.run(
        ["git", "rev-parse", "--git-dir"], cwd=d, capture_output=True, text=True
    ).stdout.strip()
)
state = (d / state if not state.is_absolute() else state) / "wook-gate-state.json"
check("L pass clears stall state", rc == 0 and not state.exists(), True)

print("Test O-Q — a check that cannot run must NOT pass (fail-closed) + utf-8 output")
# Regression (2026-07-17): run() used locale decoding (cp949 on Windows) so a check whose
# output contained an em-dash or Korean crashed the reader thread — and the handler
# `return 0` turned that crash into a PASS, letting a genuinely failing commit through.
d = repo(recipe="unicode: python -c \"print('대비 미달 — FAIL'); exit(1)\"\n")
rc, out = gate(d)
check("O non-ascii FAILING output -> still blocks", rc != 0, True)
check("P non-ascii text survived decoding", "대비 미달" in out, True)
d = repo(recipe="ok: python -c \"print('통과 — OK')\"\n")
rc, out = gate(d)
check("Q non-ascii PASSING output -> allows", rc == 0, True)

print("Test M-N — pointer freshness warns, never blocks")
d = repo(recipe="ok: true\n")
idx = d / ".claude" / "reuse-index"
idx.mkdir()
(d / "app.py").write_text("def good_fn():\n    pass\n", encoding="utf-8")
(idx / "backend.md").write_text(
    "# b\n- good · ok · app.py:good_fn\n- bad · gone · app.py:missing_fn\n",
    encoding="utf-8",
)
rc, out = gate(d)
check("M stale pointer -> exit 0 + warning", rc == 0 and "missing_fn" in out, True)
check("N valid pointer not flagged", "good_fn" not in out, True)

for p in Path(tempfile.gettempdir()).glob("gaterun_*"):
    shutil.rmtree(p, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
