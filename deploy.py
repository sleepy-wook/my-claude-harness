#!/usr/bin/env python3
"""Deploy the harness from this repo into ~/.claude (Claude Code only).

This repo is the single source of truth (and contains NO secrets). The live
harness lives in ~/.claude (which DOES hold secrets), so we never git that.
Instead we version clean copies here and render them on demand:
  hooks/ harness/ agents/ skills/  -> copied as-is
  settings.hooks.json               -> merged into ~/.claude/settings.json `hooks`
  harness/core-rules.md             -> rendered into a marked block in ~/.claude/CLAUDE.md

Idempotent. Usage:
  python deploy.py            # deploy
  python deploy.py --check    # dry-run; exit 1 on drift
"""

import argparse
import json
import sys
from pathlib import Path

try:  # gate-executed (`deploy --check` is a recipe line): our output must survive cp949
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent
SRC = REPO / "claude"  # tool-neutral source (name kept for git history)


# ---- shared file ops -------------------------------------------------------


def copy_tree(src_dir: Path, dest_dir: Path, check: bool, actions: list):
    """Mirror src_dir into dest_dir (recursive, byte-exact, skipping bytecode)."""
    if not src_dir.exists():
        return
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts or f.suffix == ".pyc":
            continue
        rel = f.relative_to(src_dir.parent)
        target = dest_dir.parent / rel
        new = f.read_bytes()
        same = target.exists() and target.read_bytes() == new
        actions.append(("copy", rel.as_posix(), "up-to-date" if same else "update"))
        if not check and not same:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(new)


def write_rendered(dest: Path, content: str, name: str, check: bool, actions: list):
    """Write a generated file iff its content changed."""
    same = dest.exists() and dest.read_text(encoding="utf-8") == content
    actions.append(("render", name, "up-to-date" if same else "update"))
    if not check and not same:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


# ---- pure builders (unit-testable) ----------------------------------------


def build_hooks_block(settings_text: str, hooks_dir: str) -> dict:
    """Claude `hooks` block: the file as-is, with the per-machine path filled in."""
    return json.loads(settings_text.replace("{HOOKS_DIR}", hooks_dir))["hooks"]


CLAUDE_MD_BEGIN = (
    "<!-- wook-harness:begin (deploy.py가 core-rules.md에서 렌더 — 직접 수정 금지) -->"
)
CLAUDE_MD_END = "<!-- wook-harness:end -->"


def build_user_claude_md(core_rules_text: str, existing: str | None) -> str:
    """Render ~/.claude/CLAUDE.md: the core-rules body inside a marked block.

    CLAUDE.md is loaded once per session (prompt-cached; per official docs it is
    re-injected after compaction) — the validated carrier for standing rules,
    replacing the old per-turn injection hook (~700 tokens duplicated every turn).
    Only the marked block is owned; any text outside it is preserved verbatim.
    """
    body = "\n".join(
        ln for ln in core_rules_text.splitlines() if not ln.startswith("# ")
    ).strip()
    block = f"{CLAUDE_MD_BEGIN}\n{body}\n{CLAUDE_MD_END}\n"
    if existing and CLAUDE_MD_BEGIN in existing and CLAUDE_MD_END in existing:
        pre = existing.split(CLAUDE_MD_BEGIN)[0]
        post = existing.split(CLAUDE_MD_END, 1)[1].lstrip("\n")
        return pre + block + post
    if existing and existing.strip():
        return existing.rstrip() + "\n\n" + block
    return block


# ---- targets ---------------------------------------------------------------


def deploy_claude(check: bool) -> list:
    dest = Path.home() / ".claude"
    hooks_dir = (dest / "hooks").as_posix()
    actions: list = []
    for sub in ("hooks", "harness", "agents", "skills"):
        copy_tree(SRC / sub, dest / sub, check, actions)
    settings_path = dest / "settings.json"
    settings = (
        json.loads(settings_path.read_text(encoding="utf-8"))
        if settings_path.exists()
        else {}
    )
    new_hooks = build_hooks_block(
        (SRC / "settings.hooks.json").read_text(encoding="utf-8"), hooks_dir
    )
    same = settings.get("hooks") == new_hooks
    actions.append(("settings", "hooks key", "up-to-date" if same else "update"))
    if not check and not same:
        settings["hooks"] = new_hooks
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    # Standing rules ride in ~/.claude/CLAUDE.md (loaded once, cached) — v2 carrier
    # replacing the per-turn inject_core_rules hook. Marked block only; rest preserved.
    claude_md = dest / "CLAUDE.md"
    existing = claude_md.read_text(encoding="utf-8") if claude_md.exists() else None
    write_rendered(
        claude_md,
        build_user_claude_md(
            (SRC / "harness" / "core-rules.md").read_text(encoding="utf-8"), existing
        ),
        "CLAUDE.md",
        check,
        actions,
    )
    return actions


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="dry-run; exit 1 on drift")
    args = ap.parse_args()

    dest = Path.home() / ".claude"
    actions = deploy_claude(args.check)

    print(f"{'DRY-RUN' if args.check else 'DEPLOY'}  dest={dest}")
    for kind, name, status in actions:
        print(f"  [{status:>10}] {kind}: {name}")
    if args.check and any(status != "up-to-date" for _, _, status in actions):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
