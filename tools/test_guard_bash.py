#!/usr/bin/env python3
"""Behavioral tests for guard_bash.py — catastrophic-command ASK guard.

Dangerous commands must produce permissionDecision "ask"; everyday commands must
pass through silently (exit 0, no output) — the list is zero-false-positive by
design. Exit 0 = all pass.
"""

import json
import subprocess
import sys
from pathlib import Path

try:  # gate-executed script contract: our own output must survive a cp949 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


HOOK = str(
    Path(__file__).resolve().parent.parent / "claude" / "hooks" / "guard_bash.py"
)
results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def hook(command):
    ev = {"tool_input": {"command": command}}
    p = subprocess.run(
        [sys.executable, "-B", HOOK],
        input=json.dumps(ev),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        timeout=30,
    )
    out = p.stdout.strip()
    if not out:
        return "allow"
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


DANGEROUS = [
    ("rm -rf ~", "rm -rf ~"),
    ("rm -rf home slash", "rm -rf ~/"),
    ("rm -rf root", "rm -rf /"),
    ("rm -rf drive root", "rm -rf C:\\"),
    ("rm -rf parent", "rm -rf .."),
    ("rm -rf $HOME", "rm -rf $HOME"),
    ("force push", "git push --force origin main"),
    ("force push -f", "git push -f origin main"),
    ("reset hard", "git reset --hard HEAD~3"),
    ("git clean", "git clean -fdx"),
    ("rd /s", "rd /s /q C:\\projects"),
    ("mkfs", "mkfs.ext4 /dev/sdb1"),
    ("dd to device", "dd if=img.iso of=/dev/sda"),
    ("gate: rm pre-commit", "rm .git/hooks/pre-commit"),
    ("gate: overwrite pre-commit", "echo x > .git/hooks/pre-commit"),
    ("gate: create evaluate-off", "touch .claude/evaluate-off"),
    ("gate: redirect into recipe", "echo 'ok: true' > .claude/evaluate.recipe"),
    ("gate: sed -i recipe", "sed -i 's/x/y/' .claude/evaluate.recipe"),
]

SAFE = [
    ("ls", "ls -la"),
    ("commit", 'git commit -m "feat: x"'),
    ("rm project dir", "rm -rf build/"),
    ("rm node_modules", "rm -rf node_modules"),
    ("normal push", "git push origin main"),
    ("force-with-lease", "git push --force-with-lease origin feat"),
    ("soft reset", "git reset --soft HEAD~1"),
    ("remove evaluate-off (re-arm)", "rm .claude/evaluate-off"),
    ("read recipe", "cat .claude/evaluate.recipe"),
    ("run installer", "python ~/.claude/harness/install_gate.py"),
    ("run tests", "python -B tools/run_tests.py"),
]

print("Dangerous -> ask")
for name, cmd in DANGEROUS:
    check(name, hook(cmd), "ask")

print("Safe -> allow (silent)")
for name, cmd in SAFE:
    check(name, hook(cmd), "allow")

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
