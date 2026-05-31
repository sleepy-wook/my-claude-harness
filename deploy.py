#!/usr/bin/env python3
"""Deploy the harness from this repo into ~/.claude.

This repo is the source of truth and contains NO secrets. The live harness
lives in ~/.claude (which DOES hold secrets), so we never git that directory.
Instead we version clean copies here and copy them out on demand.

What this does:
1. Copy `claude/hooks/*`   -> ~/.claude/hooks/
2. Copy `claude/harness/*` -> ~/.claude/harness/
3. Merge `claude/settings.hooks.json` (the `hooks` key we own) into
   ~/.claude/settings.json, substituting the real per-machine hooks path for
   the `{HOOKS_DIR}` placeholder. All other settings keys are preserved.

Idempotent: running it again produces the same result. Portable: the absolute
hook paths are computed for THIS machine, so a fresh clone on another machine
deploys correct paths without editing.

Usage:  python deploy.py            # deploy
        python deploy.py --check    # dry-run: print what WOULD change, write nothing
"""

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SRC = REPO / "claude"
DEST = Path.home() / ".claude"
HOOKS_DIR = (DEST / "hooks").as_posix()  # e.g. C:/Users/<you>/.claude/hooks
SETTINGS = DEST / "settings.json"

SUBDIRS = ("hooks", "harness")


def build_hooks_block() -> dict:
    template = (SRC / "settings.hooks.json").read_text(encoding="utf-8")
    template = template.replace("{HOOKS_DIR}", HOOKS_DIR)
    return json.loads(template)["hooks"]


def load_settings() -> dict:
    if SETTINGS.exists():
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    return {}


def main() -> int:
    check = "--check" in sys.argv[1:]
    actions = []

    # 1+2. Copy script/rule files.
    for sub in SUBDIRS:
        src_dir = SRC / sub
        dest_dir = DEST / sub
        for f in sorted(src_dir.iterdir()):
            if not f.is_file():
                continue
            target = dest_dir / f.name
            same = target.exists() and target.read_bytes() == f.read_bytes()
            actions.append(
                ("copy", f"{sub}/{f.name}", "up-to-date" if same else "update")
            )
            if not check and not same:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)

    # 3. Merge the hooks key into settings.json (preserve everything else).
    settings = load_settings()
    new_hooks = build_hooks_block()
    hooks_same = settings.get("hooks") == new_hooks
    actions.append(("settings", "hooks key", "up-to-date" if hooks_same else "update"))
    if not check and not hooks_same:
        settings["hooks"] = new_hooks
        SETTINGS.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    # Report.
    print(f"{'DRY-RUN' if check else 'DEPLOY'}  source={SRC}  dest={DEST}")
    for kind, name, status in actions:
        print(f"  [{status:>10}] {kind}: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
