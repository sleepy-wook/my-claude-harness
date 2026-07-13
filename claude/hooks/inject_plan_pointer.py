#!/usr/bin/env python3
"""UserPromptSubmit hook: keep the IN-FLIGHT plan's acceptance criteria in context.

`/wook-plan` writes the current spec to `.claude/plan.md`, but a file written once
fades from context in long sessions and is lost at compaction — while the plan is
exactly the contract the work is being judged against (the commit gate runs the
recipe derived from it). This injects a SHORT pointer every turn: the plan title
plus its acceptance-criteria section only (capped), not the whole spec — the same
pointer-not-body pattern as the reuse/convention injectors, and the mechanism the
planning-with-files pattern validated (per-turn re-injection of the on-disk plan).

Activation: `.claude/plan.md` exists in cwd or an ancestor (file presence = on).
Otherwise inject nothing. Any error => exit 0.
"""

import json
import os
import re
import sys
from pathlib import Path

CAP = 1500
HEADING_RE = re.compile(r"^#{1,4}\s+(.*)")
CRITERIA_RE = re.compile(r"수용\s*기준|acceptance\s*criteria", re.IGNORECASE)


def find_plan(start: Path) -> Path | None:
    cur = start
    for _ in range(40):
        f = cur / ".claude" / "plan.md"
        if f.is_file():
            return f
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def extract(text: str):
    """Return (title, criteria_block). Criteria = the section whose heading matches
    CRITERIA_RE, up to the next heading; missing section => empty string."""
    lines = text.splitlines()
    title = ""
    crit: list[str] = []
    in_crit = False
    for ln in lines:
        m = HEADING_RE.match(ln)
        if m:
            if in_crit:
                break
            if not title and ln.startswith("# "):
                title = m.group(1).strip()
            if CRITERIA_RE.search(m.group(1)):
                in_crit = True
            continue
        if in_crit:
            crit.append(ln)
    return title, "\n".join(crit).strip()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    cwd = Path(event.get("cwd") or os.getcwd())
    plan = find_plan(cwd)
    if plan is None:
        return 0

    try:
        title, criteria = extract(plan.read_text(encoding="utf-8"))
    except Exception:
        return 0

    rel = os.path.relpath(plan, cwd).replace(os.sep, "/")
    if criteria:
        if len(criteria) > CAP:
            criteria = criteria[:CAP].rstrip() + "\n…(전체는 plan.md)"
        context = (
            f"This project has an in-flight plan at `{rel}`"
            + (f' ("{title}")' if title else "")
            + ". Its acceptance criteria (the commit gate verifies these):\n"
            + criteria
        )
    else:
        context = (
            f"This project has an in-flight plan at `{rel}`"
            + (f' ("{title}")' if title else "")
            + " — the current spec for the work in progress."
        )

    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
