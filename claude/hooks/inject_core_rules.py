#!/usr/bin/env python3
"""UserPromptSubmit hook: re-inject core rules every turn (forgetting guard).

Reads ~/.claude/harness/core-rules.md, strips HTML comments and the top-level
H1 title, and emits the remaining body as `additionalContext` so it lands in
Claude's context alongside every user prompt. Because it fires every turn, the
rules cannot fade as the conversation grows.

Design rules (from the harness spec):
- UserPromptSubmit has a 30s timeout, so this stays trivial (read one file).
- additionalContext must read as factual statements; framing here is neutral,
  and the rules file itself is authored in factual ("the developer prefers...")
  style to avoid tripping prompt-injection defenses.
- Never block a prompt. Any problem -> exit 0 with no output (no injection).
- exec form (spawned directly, no shell) keeps stdout clean for JSON.
"""

import json
import re
import sys
from pathlib import Path

RULES_FILE = Path.home() / ".claude" / "harness" / "core-rules.md"
MAX_CHARS = 9000  # additionalContext hard cap is 10k; stay under with headroom

# Factual, non-imperative framing line prepended to the injected body.
FRAMING = (
    "The following are this developer's standing working agreements for this "
    "environment, re-stated each turn so they stay present in long sessions:"
)


def load_body() -> str:
    try:
        text = RULES_FILE.read_text(encoding="utf-8")
    except Exception:
        return ""
    # Remove HTML comment blocks (possibly multi-line).
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Drop the leading H1 title line(s).
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("# ")]
    body = "\n".join(lines).strip()
    return body


def main() -> int:
    # Consume stdin (the hook event) even though we don't need its fields.
    try:
        sys.stdin.read()
    except Exception:
        pass

    body = load_body()
    if not body:
        return 0  # nothing to inject

    context = f"{FRAMING}\n\n{body}"
    if len(context) > MAX_CHARS:
        context = context[:MAX_CHARS]

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
