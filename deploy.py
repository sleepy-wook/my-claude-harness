#!/usr/bin/env python3
"""Deploy the harness from this repo into a target agent's config dir.

This repo is the single source of truth (and contains NO secrets). The live
harness lives in the agent's home dir (which DOES hold secrets), so we never git
that. Instead we version clean copies here and render them per target on demand.

Targets:
  claude  -> ~/.claude   (settings.json `hooks` block; agents/*.md subagents)
  codex   -> ~/.codex    (hooks.json; AGENTS.md from core-rules; agents/*.toml)

Codex deliberately mirrors Claude Code's hook schema (same events + JSON), so the
hook *scripts* are shared as-is; only the *registration* (settings.json hooks vs
hooks.json), the rules file (core-rules inject-hook vs AGENTS.md), and the
evaluator wrapper (.md subagent vs .toml agent) differ — that is all the adapter is.

Idempotent. Usage:
  python deploy.py [--target claude|codex]            # deploy
  python deploy.py [--target claude|codex] --check    # dry-run; exit 1 on drift
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SRC = REPO / "claude"  # tool-neutral source (name kept for git history)


# ---- shared file ops -------------------------------------------------------


def copy_tree(
    src_dir: Path, dest_dir: Path, check: bool, actions: list, transform=None
):
    """Mirror src_dir into dest_dir (recursive, skipping bytecode).

    `transform`: if given, files are treated as UTF-8 text and rewritten through it
    (used by the Codex target to rename the per-tool dir `.claude` -> `.codex`).
    """
    if not src_dir.exists():
        return
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts or f.suffix == ".pyc":
            continue
        rel = f.relative_to(src_dir.parent)
        target = dest_dir.parent / rel
        if transform is None:
            new = f.read_bytes()
            same = target.exists() and target.read_bytes() == new
            writer = target.write_bytes
        else:
            new = transform(f.read_text(encoding="utf-8"))
            same = target.exists() and target.read_text(encoding="utf-8") == new
            writer = lambda data=new: target.write_text(data, encoding="utf-8")  # noqa: E731
        actions.append(("copy", rel.as_posix(), "up-to-date" if same else "update"))
        if not check and not same:
            target.parent.mkdir(parents=True, exist_ok=True)
            writer()


def codex_text(s: str) -> str:
    """Rename the per-tool dir for Codex: `.claude` -> `.codex` (project artifacts
    like `.claude/conventions` AND home paths like `~/.claude/cache`). `.claude`
    always names a directory in our files; the product name "Claude Code" has no dot."""
    return s.replace(".claude", ".codex")


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


def build_codex_hooks_json(settings_text: str, hooks_dir: str) -> dict:
    """Translate Claude settings.hooks.json -> Codex `hooks.json`.

    Codex mirrors the schema, with two differences we adapt: (1) file-edit matchers
    must also match Codex's `apply_patch` tool; (2) Codex's command is a single
    string (no separate args array). Everything else is structurally identical.
    """
    block = json.loads(settings_text.replace("{HOOKS_DIR}", hooks_dir))["hooks"]
    out: dict = {}
    for event, entries in block.items():
        new_entries = []
        for entry in entries:
            e = dict(entry)
            m = e.get("matcher")
            if m and ("Edit" in m or "Write" in m) and "apply_patch" not in m:
                e["matcher"] = "apply_patch|" + m
            new_hooks = []
            for h in e.get("hooks", []):
                cmd = " ".join([h.get("command", ""), *h.get("args", [])]).strip()
                nh = {k: v for k, v in h.items() if k != "args"}
                nh["command"] = cmd
                new_hooks.append(nh)
            e["hooks"] = new_hooks
            new_entries.append(e)
        out[event] = new_entries
    return {"hooks": out}


def _strip_frontmatter(md: str) -> str:
    if md.startswith("---"):
        parts = md.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return md


def build_agents_md(core_rules_text: str) -> str:
    """Codex AGENTS.md from core-rules (drop the H1; keep the rule body)."""
    body = "\n".join(
        ln for ln in core_rules_text.splitlines() if not ln.startswith("# ")
    ).strip()
    return (
        "# AGENTS.md — wook harness rules\n\n"
        "> Auto-generated from `core-rules.md` by `deploy.py --target=codex`.\n"
        "> Edit the source and re-deploy; do not hand-edit this file.\n\n"
        f"{body}\n"
    )


def build_evaluator_toml(evaluator_md_text: str) -> str:
    """Codex custom-agent TOML for the independent evaluator (best-effort port).

    Restriction is via sandbox + scoped MCP (not Claude's `tools:` frontmatter):
    read-only sandbox, and the Playwright MCP for frontend visual checks.
    NOTE: verify the exact field names against your installed Codex version.
    """
    body = _strip_frontmatter(evaluator_md_text).strip().replace('"""', '\\"\\"\\"')
    return (
        "# wook-evaluator — Codex custom agent (independent evaluator).\n"
        "# Best-effort port: confirm the schema against your Codex version.\n"
        'sandbox_mode = "read-only"   # judge only, never edits code\n'
        "# For frontend visual checks, configure a `playwright` MCP server in\n"
        '# config.toml and scope it here, e.g.:  mcp_servers = ["playwright"]\n'
        f'instructions = """\n{body}\n"""\n'
    )


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
    return actions


def deploy_codex(check: bool) -> list:
    dest = Path.home() / ".codex"
    hooks_dir = (dest / "hooks").as_posix()
    actions: list = []
    # Shared scripts/skills/templates — copied with `.claude` -> `.codex` so the agent
    # reads/writes the project's `.codex/` dir (conventions, reuse-index, recipe, map).
    for sub in ("hooks", "skills", "harness"):
        copy_tree(SRC / sub, dest / sub, check, actions, transform=codex_text)
    # Rendered per-tool: hooks registration, rules file, evaluator wrapper.
    write_rendered(
        dest / "hooks.json",
        json.dumps(
            build_codex_hooks_json(
                (SRC / "settings.hooks.json").read_text(encoding="utf-8"), hooks_dir
            ),
            indent=2,
        )
        + "\n",
        "hooks.json",
        check,
        actions,
    )
    write_rendered(
        dest / "AGENTS.md",
        codex_text(
            build_agents_md(
                (SRC / "harness" / "core-rules.md").read_text(encoding="utf-8")
            )
        ),
        "AGENTS.md",
        check,
        actions,
    )
    write_rendered(
        dest / "agents" / "wook-evaluator.toml",
        codex_text(
            build_evaluator_toml(
                (SRC / "agents" / "wook-evaluator.md").read_text(encoding="utf-8")
            )
        ),
        "agents/wook-evaluator.toml",
        check,
        actions,
    )
    return actions


TARGETS = {"claude": deploy_claude, "codex": deploy_codex}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=TARGETS, default="claude")
    ap.add_argument("--check", action="store_true", help="dry-run; exit 1 on drift")
    args = ap.parse_args()

    dest = Path.home() / (".claude" if args.target == "claude" else ".codex")
    actions = TARGETS[args.target](args.check)

    print(f"{'DRY-RUN' if args.check else 'DEPLOY'}  target={args.target}  dest={dest}")
    for kind, name, status in actions:
        print(f"  [{status:>10}] {kind}: {name}")
    if args.check and any(status != "up-to-date" for _, _, status in actions):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
