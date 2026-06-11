#!/usr/bin/env python3
"""UserPromptSubmit hook: surface the per-project convention catalog (Tier-1 pointer).

If the project has coding conventions (`.claude/conventions/` with one markdown
file per domain), inject a SHORT pointer every turn: which conventions exist and
how to use them. It does NOT inject the convention bodies — only awareness, so the
AI reads the relevant doc (and from there the real source-of-truth file) before
writing or changing code in that area. Sibling of `inject_reuse_pointer.py`:
reuse-index answers "what to reuse"; conventions answer "what rules/style to follow".

Cross-cutting vs vertical: `shared.md` holds conventions that apply to EVERY task
(testing, security, logging/errors, git) and is flagged "always"; the other
`<domain>.md` files are domain-scoped (read the one you're touching).

Activation: `.claude/conventions/` exists in cwd or an ancestor (file-presence =
on, like the evaluate gate). Otherwise inject nothing (exit 0).
"""

import json
import os
import sys
from pathlib import Path


def find_conventions_dir(start: Path) -> Path | None:
    cur = start
    for _ in range(40):
        d = cur / ".claude" / "conventions"
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
    conv_dir = find_conventions_dir(cwd)
    if conv_dir is None:
        return 0  # no conventions here

    stems = sorted(p.stem for p in conv_dir.glob("*.md") if p.is_file())
    if not stems:
        return 0

    has_shared = "shared" in stems
    domains = [s for s in stems if s != "shared"]
    rel = os.path.relpath(conv_dir, cwd).replace(os.sep, "/")

    parts = [
        "This project defines coding conventions per domain at "
        f"`{rel}/`. Follow them when writing or changing code."
    ]
    if has_shared:
        parts.append(
            f"ALWAYS consult `{rel}/shared.md` — cross-cutting conventions "
            "(testing, security, logging/errors, git) that apply to every task."
        )
    if domains:
        parts.append(
            f"Domain-specific: {', '.join(domains)}. Before working in a domain, "
            f"read the matching `{rel}/<domain>.md` first and follow it; its values "
            "point to the real source-of-truth file (e.g. a theme/tokens file), and "
            "machine-checkable rules are enforced by the evaluate gate."
        )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": " ".join(parts),
        }
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
