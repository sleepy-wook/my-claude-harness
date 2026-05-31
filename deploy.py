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

# Managed subtrees under claude/ that get mirrored into ~/.claude/.
# Copied recursively so nested layouts (skills/<name>/SKILL.md) work.
MANAGED_DIRS = ("hooks", "harness", "agents", "skills")


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

    # 1+2. Copy managed subtrees recursively (preserves nested structure).
    for sub in MANAGED_DIRS:
        src_dir = SRC / sub
        if not src_dir.exists():
            continue
        for f in sorted(src_dir.rglob("*")):
            if not f.is_file():
                continue
            if "__pycache__" in f.parts or f.suffix == ".pyc":
                continue  # never deploy bytecode caches
            rel = f.relative_to(SRC)  # e.g. skills/evaluate/SKILL.md
            target = DEST / rel
            same = target.exists() and target.read_bytes() == f.read_bytes()
            actions.append(("copy", rel.as_posix(), "up-to-date" if same else "update"))
            if not check and not same:
                target.parent.mkdir(parents=True, exist_ok=True)
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
    # In --check mode, signal drift (source not deployed) with a non-zero exit so it
    # can act as a real gate criterion. An actual deploy always returns 0.
    if check and any(status != "up-to-date" for _, _, status in actions):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
