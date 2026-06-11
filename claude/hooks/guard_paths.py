#!/usr/bin/env python3
"""PreToolUse hook: block edits to protected paths (over-action guard, deterministic part).

Reads the Claude Code PreToolUse event JSON from stdin. For Edit/Write tool
calls, it checks the target `file_path` against a small, conservative list of
paths that should never be hand-edited by the agent (VCS internals, credential
files, private keys). On a match it returns a `deny` decision; otherwise it
stays silent (exit 0) so the normal permission flow applies.

Design rules (from the harness spec):
- PreToolUse blocks via `hookSpecificOutput.permissionDecision = "deny"` with a
  reason fed back to Claude. (exit 2 also blocks, but JSON gives a clean reason.)
- A `deny` here cannot be bypassed by permission mode — it is a hard floor.
- The default list is intentionally ULTRA-conservative: only things the agent
  has no legitimate reason to edit, so normal work is never blocked. Add more
  patterns (e.g. ".env", lock files) to PROTECTED if you want them guarded.
- exec form (no shell) keeps stdout clean for the JSON decision.
"""

import json
import sys
from pathlib import PurePath


def protection_reason(file_path: str) -> str | None:
    """Return a human reason if the path is protected, else None."""
    p = PurePath(file_path)
    segments = [s.lower() for s in p.parts]
    name = p.name.lower()

    # 1. Git internals (NOT .gitignore / .gitattributes — those are real files).
    if ".git" in segments:
        return "Git internal directory (.git/)"

    # 2. Credential / secret stores.
    if "credentials" in name and name.endswith(".json"):
        return "credentials file"
    if name in {".credentials.json", "secrets.json"}:
        return "secrets store"

    # 3. Private keys.
    if name.endswith((".pem", ".key")) or name in {"id_rsa", "id_ed25519"}:
        return "private key material"

    # --- opt-in (uncomment to also guard these) -----------------------------
    # if name == ".env" or (name.startswith(".env.") and not name.endswith(
    #     (".example", ".sample", ".template"))):
    #     return "environment/secrets file (.env)"
    # if name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}:
    #     return "dependency lock file"
    # ------------------------------------------------------------------------

    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0  # can't parse -> stay out of the way

    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")  # Claude / Codex
    if not file_path:
        return 0

    reason = protection_reason(str(file_path))
    if reason is None:
        return 0  # not protected -> defer to normal permission flow

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Blocked by guard hook: this path is protected ({reason}). "
                f"Path: {file_path}. Ask the developer before modifying it, or "
                f"edit the PROTECTED list in ~/.claude/hooks/guard_paths.py."
            ),
        }
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
