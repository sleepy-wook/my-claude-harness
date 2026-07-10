#!/usr/bin/env python3
"""Behavioral tests for inject_plan_pointer.py — in-flight plan re-injection.

plan.md present => additionalContext with title + acceptance-criteria section,
capped; absent => silent. Exit 0 = all pass.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = str(
    Path(__file__).resolve().parent.parent
    / "claude"
    / "hooks"
    / "inject_plan_pointer.py"
)
results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def run(d):
    ev = {"cwd": str(d)}
    p = subprocess.run(
        [sys.executable, "-B", HOOK],
        input=json.dumps(ev),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return p.returncode, p.stdout.strip()


def proj(plan_text=None):
    d = Path(tempfile.mkdtemp(prefix="planptr_"))
    (d / ".claude").mkdir()
    if plan_text is not None:
        (d / ".claude" / "plan.md").write_text(plan_text, encoding="utf-8")
    return d


PLAN = (
    "# SPEC — 로그인 기능\n\n## Scope\n- 이것저것\n\n"
    "## 수용 기준 (Acceptance criteria)\n- `pytest tests/auth` 통과\n- `/login` 200 응답\n\n"
    "## Edge cases\n- 만료 토큰\n"
)

rc, out = run(proj(PLAN))
ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""
check("A present: criteria injected", "pytest tests/auth" in ctx, True)
check("B present: title included", "로그인 기능" in ctx, True)
check("C present: other sections excluded", "만료 토큰" not in ctx, True)

rc, out = run(proj(None))
check("D absent: silent exit 0", (rc, out), (0, ""))

long_plan = "# BIG\n\n## Acceptance criteria\n" + "\n".join(
    f"- criterion {i} " + "x" * 40 for i in range(200)
)
rc, out = run(proj(long_plan))
ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
check("E capped near limit", len(ctx) < 1800, True)

rc, out = run(proj("# 제목만 있는 플랜\n\n내용.\n"))
ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""
check("F no criteria section: pointer only", "제목만 있는 플랜" in ctx, True)

for p in Path(tempfile.gettempdir()).glob("planptr_*"):
    shutil.rmtree(p, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
