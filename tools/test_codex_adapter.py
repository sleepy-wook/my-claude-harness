#!/usr/bin/env python3
"""Tests for the Codex adapter (deploy.py --target=codex transforms + field tolerance).

What we CAN verify here (no Codex installed): the rendered artifacts are valid and
equivalent to the Claude source. What we CANNOT: that Codex actually fires the hooks
(esp. apply_patch coverage) — that is a machine test on a real Codex install.
Run from the repo root. Exit 0 = all pass.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import deploy  # noqa: E402

HD = "/home/user/.codex/hooks"
results = []


def check(name, ok):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


settings_text = (REPO / "claude" / "settings.hooks.json").read_text(encoding="utf-8")

print("Test — Codex hooks.json transform")
cj = deploy.build_codex_hooks_json(settings_text, HD)
events = set(cj.get("hooks", {}))
check(
    "valid + has 4 events",
    {"PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop"} <= events,
)
json.dumps(cj)  # must be serialisable
check(
    "edit matcher gained apply_patch",
    "apply_patch" in cj["hooks"]["PreToolUse"][0]["matcher"],
)

all_hooks = [h for entries in cj["hooks"].values() for e in entries for h in e["hooks"]]
check(
    "commands are single strings (no args key)", all("args" not in h for h in all_hooks)
)
check(
    "commands point at the codex hooks dir", all(HD in h["command"] for h in all_hooks)
)

# equivalence: every Claude hook script appears in the Codex commands
claude_block = json.loads(settings_text.replace("{HOOKS_DIR}", HD))["hooks"]
claude_scripts = {
    Path(h["args"][0]).name
    for entries in claude_block.values()
    for e in entries
    for h in e["hooks"]
}
codex_cmd_blob = " ".join(h["command"] for h in all_hooks)
check(
    "all Claude scripts present in Codex commands",
    all(s in codex_cmd_blob for s in claude_scripts),
)

print("Test — AGENTS.md from core-rules")
agents = deploy.build_agents_md(
    (REPO / "claude" / "harness" / "core-rules.md").read_text(encoding="utf-8")
)
check("dropped source H1 (# core-rules)", "# core-rules" not in agents)
check("carries a known rule phrase", "테스트·검증" in agents)

print("Test — evaluator.toml")
ev = deploy.build_evaluator_toml(
    (REPO / "claude" / "agents" / "wook-evaluator.md").read_text(encoding="utf-8")
)
try:
    import tomllib

    data = tomllib.loads(ev)
    check("parses as TOML + sandbox read-only", data.get("sandbox_mode") == "read-only")
    check("has instructions", bool(data.get("instructions")))
except ImportError:
    check("tomllib unavailable — string check", 'sandbox_mode = "read-only"' in ev)

print("Test — hook field tolerance (file_path ↔ path)")
GP = str(REPO / "claude" / "hooks" / "guard_paths.py")


def run_guard(tool_input):
    p = subprocess.run(
        [sys.executable, GP],
        input=json.dumps({"tool_input": tool_input}),
        capture_output=True,
        text=True,
    )
    return p.stdout


check("denies via Codex `path`", "deny" in run_guard({"path": "secret.pem"}))
check("denies via Claude `file_path`", "deny" in run_guard({"file_path": "secret.pem"}))
check("allows a normal file", run_guard({"path": "app.py"}).strip() == "")

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
