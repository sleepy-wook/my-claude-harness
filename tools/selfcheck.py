#!/usr/bin/env python3
"""Self-verification for the claude-harness repo. Exit 0 = all checks pass.

Wired into `.claude/evaluate.recipe` so the harness verifies its OWN integrity —
i.e. it dogfoods its own Stop-gate / /wook-evaluate. Checks (static, no runtime):
  1. all hook scripts + deploy.py compile
  2. settings.hooks.json is valid JSON and declares the 4 expected hook events
  3. every skill / agent markdown has a `name:` frontmatter
  4. no secret-like files are tracked in git

One portable script (not shell one-liners) so it runs the same under cmd.exe and sh.
"""

import glob
import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
errors: list[str] = []

# 1. Scripts compile.
scripts = sorted(glob.glob(str(REPO / "claude" / "hooks" / "*.py"))) + [
    str(REPO / "deploy.py")
]
for s in scripts:
    try:
        py_compile.compile(s, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"compile: {e}")

# 2. settings.hooks.json valid + has the 4 events.
try:
    hooks = json.loads(
        (REPO / "claude" / "settings.hooks.json").read_text(encoding="utf-8")
    )["hooks"]
    missing = {"PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop"} - set(hooks)
    if missing:
        errors.append(f"settings: missing hook events {sorted(missing)}")
except Exception as e:
    errors.append(f"settings: {e}")

# 3. Every skill/agent markdown has a name: frontmatter.
mds = glob.glob(str(REPO / "claude" / "skills" / "*" / "SKILL.md")) + glob.glob(
    str(REPO / "claude" / "agents" / "*.md")
)
for m in mds:
    if not re.search(r"(?m)^name:\s*\S+", Path(m).read_text(encoding="utf-8")):
        errors.append(f"frontmatter: no `name:` in {os.path.relpath(m, REPO)}")

# 4. No tracked secret-like files.
secret_names = {".credentials.json", "secrets.json", "id_rsa", "id_ed25519", ".env"}


def is_secret(path: str) -> bool:
    b = os.path.basename(path).lower()
    return b in secret_names or b.startswith(".env.") or b.endswith((".pem", ".key"))


try:
    files = subprocess.run(
        ["git", "ls-files"], cwd=str(REPO), capture_output=True, text=True
    ).stdout.split()
    bad = [f for f in files if is_secret(f)]
    if bad:
        errors.append(f"secrets: tracked secret-like files {bad}")
except Exception as e:
    errors.append(f"secrets: {e}")


# 4b. Cross-platform: deployed/runtime scripts must pin text encoding.
#     Windows defaults to cp949; reading our UTF-8 (Korean) sources without
#     encoding="utf-8" crashes there. Enforce it on everything we deploy/run.
def _io_missing_encoding(src: str) -> bool:
    """True if any read_text/write_text call omits encoding= (balanced-paren scan,
    so multi-line calls and nested parens like write_text(json.dumps(x), ...) are ok)."""
    for m in re.finditer(r"\.(?:read_text|write_text)\(", src):
        depth, j = 1, m.end()
        while j < len(src) and depth:
            depth += {"(": 1, ")": -1}.get(src[j], 0)
            j += 1
        if "encoding" not in src[m.end() : j]:
            return True
    return False


for s in scripts:
    if _io_missing_encoding(Path(s).read_text(encoding="utf-8")):
        errors.append(
            f"encoding: {os.path.relpath(s, REPO)} — a read_text/write_text lacks "
            "encoding= (breaks on Windows cp949)"
        )

# 5. build-log growth nudge (non-failing): tiered-log policy says archive when large.
warnings: list[str] = []
try:
    n = len((REPO / "docs" / "build-log.md").read_text(encoding="utf-8").splitlines())
    if n > 700:
        warnings.append(
            f"build-log.md is {n} lines (>700) — archive older feature sections to "
            "docs/build-log-archive/ (keep decisions with status); see its 유지 정책."
        )
except Exception:
    pass

# Verdict.
if errors:
    print("SELFCHECK FAIL:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(
    f"SELFCHECK OK: {len(scripts)} scripts compile, settings has 4 events, "
    f"{len(mds)} md frontmatter ok, no tracked secrets"
)
for w in warnings:
    print("  ⚠ ", w)
sys.exit(0)
