#!/usr/bin/env python3
"""Stop hook: warn (non-blocking) about STALE reuse-catalog pointers.

The reuse catalog's entries point to real code (`path:symbol`). When code is
renamed/deleted, those pointers can go stale. This is the deterministic half of
catalog maintenance: adding NEW entries needs judgment (the AI does that, per
core-rules), but detecting a pointer that no longer resolves is pure code — so a
hook handles it.

It only NUDGES (systemMessage) and never blocks the stop — a stale catalog is a
maintenance issue, not a correctness gate. Activation: `.claude/reuse-index/`
exists (cwd or ancestor) AND code changed this turn. Any error => silent allow.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

CODE_EXT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".php",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".kt",
    ".swift",
    ".sql",
}


def find_index_dir(start: Path):
    cur = start
    for _ in range(40):
        d = cur / ".claude" / "reuse-index"
        if d.is_dir():
            return cur, d
        if cur.parent == cur:
            break
        cur = cur.parent
    return None, None


def code_changed(root: Path) -> bool:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:
        return True
    if "fatal:" in out:
        return True
    return any(
        Path(ln[3:].strip().strip('"')).suffix.lower() in CODE_EXT
        for ln in out.splitlines()
    )


def stale_pointers(root: Path, index_dir: Path) -> list[str]:
    stale = []
    for man in sorted(index_dir.glob("*.md")):
        for line in man.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("- ") or "·" not in line or ":" not in line:
                continue
            ptr = line.split("·")[-1].strip()
            path, _, sym = ptr.rpartition(":")
            f = root / path
            try:
                ok = f.is_file() and re.search(
                    rf"\b{re.escape(sym)}\b", f.read_text(encoding="utf-8")
                )
            except Exception:
                ok = False
            if not ok:
                stale.append(f"{man.name}: {ptr}")
    return stale


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    cwd = Path(event.get("cwd") or os.getcwd())
    root, index_dir = find_index_dir(cwd)
    if index_dir is None or not code_changed(root):
        return 0

    stale = stale_pointers(root, index_dir)
    if not stale:
        return 0

    listed = "\n".join(f"  - {s}" for s in stale[:10])
    more = f"\n  …(+{len(stale) - 10} more)" if len(stale) > 10 else ""
    sys.stdout.write(
        json.dumps(
            {
                "systemMessage": (
                    f"⚠️ reuse catalog: {len(stale)} stale pointer(s) — the code they name no "
                    f"longer resolves (renamed/deleted). Run /wook-index to refresh.\n{listed}{more}"
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
