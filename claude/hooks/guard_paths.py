#!/usr/bin/env python3
"""PreToolUse hook: guard protected paths on Edit/Write (over-action guard, deterministic part).

Reads the Claude Code PreToolUse event JSON from stdin and checks the target
`file_path` against two small, conservative lists:

  DENY — paths the agent has no legitimate reason to hand-edit, ever: VCS
  internals, credential files, private keys. A `deny` cannot be bypassed by
  permission mode — it is a hard floor.

  ASK — the commit gate's own control files (v2 self-protection): the bar the
  gate checks (`.claude/evaluate.recipe`) and its kill switch
  (`.claude/evaluate-off`). An agent under gate pressure tends to edit the check
  instead of the code (CI-gaming — GitHub's agent-PR guidance treats "any change
  that weakens CI" as an automatic blocker), so changing these is fine but must
  be a conscious human approval, not a silent edit. `/wook-plan` writing a new
  recipe triggers exactly one prompt — that's the developer approving the bar.

Everything else stays silent (exit 0) so the normal permission flow applies.
Design rules: JSON `permissionDecision` (deny/ask) with a reason; ultra-
conservative lists so normal work is never blocked; exec form keeps stdout clean.
"""

import json
import sys
from pathlib import PurePath


def protection_decision(file_path: str):
    """Return (decision, reason) — ("deny"|"ask", str) — or None if unprotected."""
    p = PurePath(file_path)
    segments = [s.lower() for s in p.parts]
    name = p.name.lower()

    # --- DENY: never hand-edited by the agent -------------------------------
    # 1. Git internals (NOT .gitignore / .gitattributes — those are real files).
    if ".git" in segments:
        return "deny", "Git internal directory (.git/)"
    # 2. Credential / secret stores.
    if "credentials" in name and name.endswith(".json"):
        return "deny", "credentials file"
    if name in {".credentials.json", "secrets.json"}:
        return "deny", "secrets store"
    # 3. Private keys.
    if name.endswith((".pem", ".key")) or name in {"id_rsa", "id_ed25519"}:
        return "deny", "private key material"

    # --- ASK: commit-gate control files (developer approves bar changes) ----
    per_tool_dir = {".claude", ".codex"} & set(segments)
    if per_tool_dir:
        if name == "evaluate.recipe":
            return (
                "ask",
                "commit-gate criteria (evaluate.recipe) — 기준 변경은 개발자 승인",
            )
        if name == "evaluate-off":
            return (
                "ask",
                "commit-gate kill switch (evaluate-off) — 게이트 비활성화는 개발자 승인",
            )

    # --- opt-in (uncomment to also guard these) -----------------------------
    # if name == ".env" or (name.startswith(".env.") and not name.endswith(
    #     (".example", ".sample", ".template"))):
    #     return "deny", "environment/secrets file (.env)"
    # if name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}:
    #     return "deny", "dependency lock file"
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

    verdict = protection_decision(str(file_path))
    if verdict is None:
        return 0  # not protected -> defer to normal permission flow
    decision, reason = verdict

    if decision == "deny":
        why = (
            f"Blocked by guard hook: this path is protected ({reason}). "
            f"Path: {file_path}. Ask the developer before modifying it, or "
            f"edit the protected list in ~/.claude/hooks/guard_paths.py."
        )
    else:
        why = f"guard_paths: {reason}. Path: {file_path}. 의도한 변경이면 승인하세요."

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": why,
        }
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
