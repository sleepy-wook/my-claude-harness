#!/usr/bin/env python3
"""Tests for deploy.py's pure builders (Claude Code target).

Moved out of the retired multi-agent adapter test (Phase 1 of the Claude-only alignment):
  - copy_tree really writes files (regression for the 2026-06-15 write_bytes() bug that
    only bit when a file actually changed — `--check` runs never exercised it)
  - build_user_claude_md renders core-rules into a marked block, idempotently, and never
    touches text outside the block (the v2 standing-rules carrier)
"""

import shutil
import sys
import tempfile
from pathlib import Path

try:  # gate-executed via run_tests: output must survive a cp949 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import deploy  # noqa: E402

results: list[bool] = []


def check(name: str, ok: bool):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


print("Test — copy_tree actually writes")
src = Path(tempfile.mkdtemp(prefix="ct_"))
dst = Path(tempfile.mkdtemp(prefix="ct_"))
(src / "hooks").mkdir()
(src / "hooks" / "x.py").write_text("print('hi')\n", encoding="utf-8")
(src / "hooks" / "__pycache__").mkdir()
(src / "hooks" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
actions: list = []
deploy.copy_tree(src / "hooks", dst / "hooks", False, actions)
check(
    "wrote the file byte-exact",
    (dst / "hooks" / "x.py").read_bytes() == b"print('hi')\n",
)
check("skipped bytecode", not (dst / "hooks" / "__pycache__").exists())
check("reported update then up-to-date", actions[0][2] == "update")
actions2: list = []
deploy.copy_tree(src / "hooks", dst / "hooks", True, actions2)
check("second pass is a no-op (--check clean)", actions2[0][2] == "up-to-date")
for d in (src, dst):
    shutil.rmtree(d, ignore_errors=True)

print("Test — ~/.claude/CLAUDE.md builder (standing-rules carrier)")
core = (REPO / "claude" / "harness" / "core-rules.md").read_text(encoding="utf-8")
fresh = deploy.build_user_claude_md(core, None)
check(
    "fresh render has markers + a known rule",
    deploy.CLAUDE_MD_BEGIN in fresh and "테스트·검증" in fresh,
)
check("source H1 dropped", "# core-rules\n" not in fresh)
check("idempotent re-render", deploy.build_user_claude_md(core, fresh) == fresh)
merged = deploy.build_user_claude_md(
    core, "# my own notes\n\n" + fresh + "\nmore below\n"
)
check(
    "text outside the block preserved",
    merged.startswith("# my own notes") and merged.rstrip().endswith("more below"),
)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
