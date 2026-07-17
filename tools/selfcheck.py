#!/usr/bin/env python3
"""Self-verification for the claude-harness repo. Exit 0 = all checks pass.

Wired into `.claude/evaluate.recipe` so the harness verifies its OWN integrity —
i.e. it dogfoods its own commit gate / /wook-evaluate. Checks (static, no runtime):
  1. all hook + harness scripts + deploy.py compile
  2. settings.hooks.json is valid JSON, declares the core hook events, and every
     registered hook references a script that actually exists
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

# Our messages (and the paths/errors we echo) contain non-ascii; a cp949 console would
# raise while PRINTING the violation, hiding which file was at fault. Fix stdout first.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

errors: list[str] = []

# 1. Scripts compile (everything we deploy and later execute).
#    skills/*/scripts/ MUST be here: the commit gate runs those via evaluate.recipe, so a
#    crash there blocks commits. They were outside this list until 2026-07-17, which is
#    exactly why gen_palette.py's cp949 stdout bug reached a user-facing gate unflagged.
scripts = (
    sorted(glob.glob(str(REPO / "claude" / "hooks" / "*.py")))
    + sorted(glob.glob(str(REPO / "claude" / "harness" / "*.py")))
    + sorted(glob.glob(str(REPO / "claude" / "skills" / "*" / "scripts" / "*.py")))
    + [str(REPO / "deploy.py")]
)
for s in scripts:
    try:
        py_compile.compile(s, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"compile: {e}")

# 2. settings.hooks.json valid + has the core events + references only real scripts.
#    Stop is optional (v2 folded the pointer checks into the commit gate and moved the
#    evaluator reminder to PostToolUse, so there may be no Stop hook at all).
try:
    hooks = json.loads(
        (REPO / "claude" / "settings.hooks.json").read_text(encoding="utf-8")
    )["hooks"]
    missing = {"PreToolUse", "PostToolUse", "UserPromptSubmit"} - set(hooks)
    if missing:
        errors.append(f"settings: missing hook events {sorted(missing)}")
    for entries in hooks.values():
        for e in entries:
            for h in e.get("hooks", []):
                for a in h.get("args", []):
                    if (
                        a.startswith("{HOOKS_DIR}/")
                        and not (
                            REPO / "claude" / "hooks" / a.split("/", 1)[1]
                        ).exists()
                    ):
                        errors.append(f"settings: references missing hook script {a}")
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
#     Windows defaults to cp949; decoding our UTF-8 (Korean, em-dash) text without
#     encoding="utf-8" crashes there. Enforce it on everything we deploy/run.
#     Covers BOTH file I/O and subprocess text capture — the latter was added after the
#     gate itself shipped a `subprocess.run(text=True)` whose cp949 crash silently passed
#     a failing commit (2026-07-17). The guard must see every decode site, not just files.
def _io_missing_encoding(src: str) -> str | None:
    """Return the offending call kind if any text-decoding call omits encoding=.

    Balanced-paren scan, so multi-line calls and nested parens are handled."""
    sites = [(r"\.(?:read_text|write_text)\(", "read_text/write_text")]
    sites.append((r"subprocess\.(?:run|check_output|Popen)\(", "subprocess"))
    for pat, kind in sites:
        for m in re.finditer(pat, src):
            depth, j = 1, m.end()
            while j < len(src) and depth:
                depth += {"(": 1, ")": -1}.get(src[j], 0)
                j += 1
            body = src[m.end() : j]
            # subprocess only decodes when text=True / universal_newlines=True
            if kind == "subprocess" and not re.search(
                r"text\s*=\s*True|universal_newlines\s*=\s*True", body
            ):
                continue
            if "encoding" not in body:
                return kind
    return None


def _prints_nonascii_unguarded(src: str) -> bool:
    """True if the script writes a NON-ASCII literal to stdout/stderr without first
    reconfiguring them to UTF-8.

    The third face of the same cp949 trap (2026-07-17): decoding was guarded, but ENCODING
    our own output wasn't. `gen_palette.py` printed an em-dash, the cp949 console raised
    UnicodeEncodeError, and — since the gate is fail-closed — every commit was blocked.

    Exempt: text handed to json.dumps() with the default ensure_ascii=True, which escapes
    non-ascii to \\uXXXX before it ever reaches stdout. Our hooks legitimately put Korean
    reasons in JSON decisions this way.
    """
    if re.search(r"sys\.std(?:out|err)\.reconfigure\(", src):
        return False
    for m in re.finditer(r"\b(?:print|sys\.std(?:out|err)\.write)\(", src):
        depth, j = 1, m.end()
        while j < len(src) and depth:
            depth += {"(": 1, ")": -1}.get(src[j], 0)
            j += 1
        body = src[m.end() : j]
        if not any(ord(c) > 127 for c in body):
            continue
        if "json.dumps(" in body and "ensure_ascii=False" not in body:
            continue  # escaped to ascii before it reaches the stream
        return True
    return False


for s in scripts:
    src = Path(s).read_text(encoding="utf-8")
    kind = _io_missing_encoding(src)
    if kind:
        errors.append(
            f"encoding: {os.path.relpath(s, REPO)} — a {kind} call decodes text without "
            "encoding= (breaks on Windows cp949)"
        )
    if _prints_nonascii_unguarded(src):
        errors.append(
            f"encoding: {os.path.relpath(s, REPO)} — prints non-ascii without "
            "sys.stdout.reconfigure(encoding='utf-8') (raises on a cp949 console; with a "
            "fail-closed gate that blocks every commit)"
        )

# 5. non-failing nudges.
warnings: list[str] = []
# 5a. commit gate installed in THIS repo? (warning only — a fresh/remote clone
#     legitimately lacks it until install_gate.py runs; must not fail CI there.)
try:
    _pc = REPO / ".git" / "hooks" / "pre-commit"
    if not (
        _pc.exists() and "wook-harness commit gate" in _pc.read_text(encoding="utf-8")
    ):
        warnings.append(
            "commit gate not installed here — run: python claude/harness/install_gate.py"
        )
except Exception:
    pass
# 5b. build-log growth nudge: tiered-log policy says archive when large.
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
    f"SELFCHECK OK: {len(scripts)} scripts compile, settings events ok, "
    f"{len(mds)} md frontmatter ok, no tracked secrets"
)
for w in warnings:
    print("  ⚠ ", w)
sys.exit(0)
