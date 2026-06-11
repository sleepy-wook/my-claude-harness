#!/usr/bin/env python3
"""UserPromptSubmit hook: surface the per-project reuse catalog (Tier-1 pointer).

If the project has a reuse catalog (`.claude/reuse-index/` with one markdown file
per domain), inject a SHORT pointer every turn: which domains exist and where to
look. It does NOT inject the manifest bodies — only domain-level awareness, so the
AI knows to read the relevant domain's manifest (and from there the real source)
before writing new code, instead of duplicating. This is the deterministic floor
of the reuse catalog; the heavy content stays on-demand.

Activation: `.claude/reuse-index/` exists in cwd or an ancestor (file-presence =
on, like the evaluate gate). Otherwise inject nothing (exit 0).
"""

import json
import os
import sys
from pathlib import Path


def find_index_dir(start: Path) -> Path | None:
    cur = start
    for _ in range(40):
        d = cur / ".claude" / "reuse-index"
        if d.is_dir():
            return d
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    cwd = Path(event.get("cwd") or os.getcwd())
    index_dir = find_index_dir(cwd)
    if index_dir is None:
        return 0  # no catalog here

    domains = sorted(p.stem for p in index_dir.glob("*.md") if p.is_file())
    if not domains:
        return 0

    rel = os.path.relpath(index_dir, cwd).replace(os.sep, "/")
    context = (
        "This project keeps a reuse catalog of existing code, indexed per domain at "
        f"`{rel}/` (domains: {', '.join(domains)}). Each `<domain>.md` lists existing "
        "components/functions/queries with a one-line description and their location "
        "(path:symbol). When about to write new code in one of these domains, the "
        "relevant `<domain>.md` is the place to check for something reusable before "
        "creating it; the manifest points to the real source for full detail."
    )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
