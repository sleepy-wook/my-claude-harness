#!/usr/bin/env python3
"""Behavioral tests for selfcheck's encoding guard — the harness's most-bitten trap.

Why this file exists: the cp949 trap bit us three times in one day (2026-07-17) and each
time the guard was blind to the new shape — decode sites, then our own stdout writes, then
an aliased subprocess and an indirect print. The guard IS the thing that stops a repeat, so
its precision is now pinned here: it must catch each proven shape AND stay quiet on the
safe ones (a guard that cries wolf gets ignored, and then it protects nothing).

Exercises the functions directly (selfcheck runs its checks at import time), by exec'ing
just the guard block. Run from the repo root. Exit 0 = all pass.

selfcheck-exempt: bad-code fixtures, not real call sites
  ^ this file's string literals deliberately contain unencoded read_text()/subprocess
  calls as test data. A static scan cannot tell a fixture from a real call site, so
  selfcheck skips this one file by that exact marker. Nothing here actually decodes.
"""

import io
import re
import sys
import tokenize
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
src = (REPO / "tools" / "selfcheck.py").read_text(encoding="utf-8")

m = re.search(r"def _strip_prose.*?(?=\nfor s in scripts)", src, re.S)
if not m:
    print("  [FAIL] could not locate the guard block in selfcheck.py")
    sys.exit(1)

g = {"re": re, "io": io, "tokenize": tokenize}
exec(compile(m.group(0), "guard", "exec"), g)
io_missing = g["_io_missing_encoding"]
prints_unguarded = g["_prints_nonascii_unguarded"]

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


print("Must CATCH — every shape that actually reached production")
check(
    "A subprocess text=True without encoding=",
    io_missing(
        'import subprocess\nsubprocess.run(["g"], capture_output=True, text=True)\n'
    ),
    "subprocess",
)
check(
    "B aliased subprocess (import subprocess as _sp) — evaluator slipped this past",
    io_missing(
        'import subprocess as _sp\n_sp.run(["g"], capture_output=True, text=True)\n'
    ),
    "subprocess",
)
check(
    "C read_text without encoding=",
    io_missing('from pathlib import Path\nPath("x").read_text()\n'),
    "read_text/write_text",
)
check(
    "D inline non-ascii print, no reconfigure — the gen_palette bug",
    prints_unguarded('print("대비 미달 - FAIL")\n'),
    True,
)
check(
    "E INDIRECT non-ascii print — evaluator proved the old guard missed this",
    prints_unguarded('msg = "한글 - em"\nprint(msg)\n'),
    True,
)

print("Must STAY QUIET — false positives kill a guard's credibility")
check(
    "F reconfigured stdout => exempt",
    prints_unguarded(
        'import sys\nsys.stdout.reconfigure(encoding="utf-8")\nprint("한글")\n'
    ),
    False,
)
check(
    "G json.dumps-only writes => exempt (our hooks' Korean reasons are escaped)",
    prints_unguarded(
        'import json, sys\nsys.stdout.write(json.dumps({"r": "한글 이유"}))\n'
    ),
    False,
)
check(
    "H prose mentioning a decode site is not one (guard flagged its own comment)",
    io_missing(
        '"""doc: subprocess.run(text=True) 예시"""\n# _sp.run(text=True) 예시\nx = 1\n'
    ),
    None,
)
check(
    "I subprocess WITH encoding= => exempt",
    io_missing(
        'import subprocess\nsubprocess.run(["g"], capture_output=True, text=True, encoding="utf-8")\n'
    ),
    None,
)
check(
    "J subprocess without text=True never decodes => exempt",
    io_missing('import subprocess\nsubprocess.run(["g"], capture_output=True)\n'),
    None,
)
check("K ascii-only script => exempt", prints_unguarded('print("hello")\n'), False)

print("Coverage — the gate executes these, so the guard must scan them")
scanned = re.search(r"scripts = \((.*?)\n\)", src, re.S).group(1)
for d in ("hooks", "harness", "skills", "tools", "deploy.py"):
    check(f"L scans {d}", d in scanned, True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
