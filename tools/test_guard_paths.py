#!/usr/bin/env python3
"""Tests for the guard_paths PreToolUse hook (Claude Code `file_path` field).

Moved out of the retired Codex-adapter test. Runs the hook as a subprocess with a real
stdin event, exactly as Claude Code does.
"""

import json
import subprocess
import sys
from pathlib import Path

try:  # gate-executed via run_tests: output must survive a cp949 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
GP = str(REPO / "claude" / "hooks" / "guard_paths.py")

results: list[bool] = []


def check(name: str, ok: bool):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


def run_guard(tool_input: dict) -> str:
    p = subprocess.run(
        [sys.executable, GP],
        input=json.dumps({"tool_input": tool_input}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.stdout


def decision(out: str) -> str:
    return (
        json.loads(out)["hookSpecificOutput"]["permissionDecision"]
        if out.strip()
        else ""
    )


print("Test — deny floor")
check("denies private key", decision(run_guard({"file_path": "secret.pem"})) == "deny")
check(
    "denies .git internals", decision(run_guard({"file_path": ".git/config"})) == "deny"
)
check(
    "denies credentials json",
    decision(run_guard({"file_path": "aws_credentials.json"})) == "deny",
)
check(
    "allows .gitignore (not an internal)",
    run_guard({"file_path": ".gitignore"}).strip() == "",
)
check("allows a normal file", run_guard({"file_path": "app.py"}).strip() == "")

print("Test — commit-gate self-protection (ask)")
check(
    "asks on evaluate.recipe",
    decision(run_guard({"file_path": ".claude/evaluate.recipe"})) == "ask",
)
check(
    "asks on evaluate-off",
    decision(run_guard({"file_path": ".claude/evaluate-off"})) == "ask",
)
check(
    "recipe outside .claude is not special",
    run_guard({"file_path": "notes/evaluate.recipe"}).strip() == "",
)

print("Test — robustness")
check("no file_path -> silent", run_guard({}).strip() == "")

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
