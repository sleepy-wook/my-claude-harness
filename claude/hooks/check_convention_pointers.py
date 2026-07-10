#!/usr/bin/env python3
"""Stop hook: warn (non-blocking) about STALE convention pointers.

Convention docs keep VALUES out of the doc and point to the real source-of-truth
(`path:symbol`, e.g. a theme/tokens file) so detail never goes stale. But the
POINTER itself can rot when that source is renamed/deleted. This is the
deterministic half of convention maintenance: writing/updating a convention needs
judgment (the AI does that, per core-rules), but detecting a pointer that no longer
resolves is pure code — so a hook handles it. Sibling of `check_reuse_pointers.py`.

Pointer lines use the same compact form as the reuse manifest, anywhere in a doc:
    - <name> · <one-line> · <path>:<symbol>
Prose lines without that shape are ignored.

It only NUDGES (systemMessage) and never blocks the stop. Activation:
`.claude/conventions/` exists (cwd or ancestor) AND code changed this turn. Any
error => silent allow.
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
    ".css",
    ".scss",
}


def find_conventions_dir(start: Path):
    cur = start
    for _ in range(40):
        d = cur / ".claude" / "conventions"
        if d.is_dir():
            return cur, d
        if cur.parent == cur:
            break
        cur = cur.parent
    return None, None


def changed_paths(root: Path):
    """Changed file paths from git status; None = unknown (fail open to full scan)."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:
        return None
    if "fatal:" in out:
        return None
    return {ln[3:].strip().strip('"') for ln in out.splitlines() if ln.strip()}


def stale_pointers(root: Path, conv_dir: Path, changed) -> list[str]:
    """Cheap existence check on every entry; the expensive symbol scan (read+regex)
    runs ONLY for pointers whose target file changed this session — Stop cost scales
    with the change, not with doc size (which grows over a project's life). Full
    sweep stays available via /wook-conventions."""
    stale = []
    for doc in sorted(conv_dir.glob("*.md")):
        for line in doc.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("- ") or "·" not in line or ":" not in line:
                continue
            ptr = line.split("·")[-1].strip()
            path, _, sym = ptr.rpartition(":")
            if not path or not sym:
                continue
            f = root / path
            if not f.is_file():
                stale.append(f"{doc.name}: {ptr}")
                continue
            if changed is not None and path not in changed:
                continue  # unchanged target -> skip the expensive scan
            try:
                ok = re.search(rf"\b{re.escape(sym)}\b", f.read_text(encoding="utf-8"))
            except Exception:
                ok = False
            if not ok:
                stale.append(f"{doc.name}: {ptr}")
    return stale


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    cwd = Path(event.get("cwd") or os.getcwd())
    root, conv_dir = find_conventions_dir(cwd)
    if conv_dir is None:
        return 0
    changed = changed_paths(root)
    if changed is not None and not any(
        Path(p).suffix.lower() in CODE_EXT for p in changed
    ):
        return 0  # no code change -> nothing to re-verify

    stale = stale_pointers(root, conv_dir, changed)
    if not stale:
        return 0

    listed = "\n".join(f"  - {s}" for s in stale[:10])
    more = f"\n  …(+{len(stale) - 10} more)" if len(stale) > 10 else ""
    sys.stdout.write(
        json.dumps(
            {
                "systemMessage": (
                    f"⚠️ conventions: {len(stale)} stale pointer(s) — the source they name no "
                    f"longer resolves (renamed/deleted). Update the doc or run /wook-conventions.\n"
                    f"{listed}{more}"
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
