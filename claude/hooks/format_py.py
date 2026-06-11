#!/usr/bin/env python3
"""PostToolUse hook: auto-format edited Python files with ruff.

Reads the Claude Code hook event JSON from stdin, finds the edited file via
`tool_input.file_path`, and runs `ruff format` on it when it is a `.py` file.

Design rules (from the harness spec):
- This is a PostToolUse hook: the edit has ALREADY happened. We only correct
  formatting after the fact, so the model cannot "forget" to format.
- It must NEVER block the edit flow. Any problem (bad JSON, missing ruff,
  format error) is swallowed and we exit 0. PostToolUse exit 2 would only
  surface stderr to Claude, never undo the edit — so we stay silent.
- No stdout is written, to avoid any chance of stdout being parsed as JSON.
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    # 1. Parse the hook event from stdin. If it's missing/invalid, do nothing.
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    # 2. Extract the edited file path. (`file_path` = Claude Code, `path` = Codex.)
    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path:
        return 0

    # 3. Only touch existing .py files.
    path = Path(file_path)
    if path.suffix.lower() != ".py" or not path.is_file():
        return 0

    # 4. Format with ruff. Never let a failure escape.
    try:
        subprocess.run(
            ["ruff", "format", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
