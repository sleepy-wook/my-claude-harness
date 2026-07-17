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
import io
import json
import os
import py_compile
import re
import subprocess
import sys
import tokenize
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

# 1. Scripts compile — EVERYTHING the gate can execute, not just what we deploy.
#    The rule that earns a directory a place here: if a crash in it blocks a commit, it
#    must be scanned. Both skills/*/scripts/ and tools/ were missing on 2026-07-17 —
#    gen_palette.py's cp949 stdout bug shipped through the first gap, and an independent
#    evaluator then proved the second: 2 of this repo's own 3 recipe lines ARE tools/
#    scripts, so leaving tools/ unscanned was the same hole one directory over.
scripts = (
    sorted(glob.glob(str(REPO / "claude" / "hooks" / "*.py")))
    + sorted(glob.glob(str(REPO / "claude" / "harness" / "*.py")))
    + sorted(glob.glob(str(REPO / "claude" / "skills" / "*" / "scripts" / "*.py")))
    + sorted(glob.glob(str(REPO / "tools" / "*.py")))
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
        ["git", "ls-files"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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
def _strip_prose(src: str) -> str:
    """Source minus comments AND docstrings — the parts that are documentation, not code.

    Both guards need it. Prose that merely *mentions* a decode site (this very file
    explains the bug using `_sp.run(text=` in a comment and a docstring) is not one, and
    the guard flagged itself until this existed. Same class of mistake as a blind
    search/replace: never treat prose as code.

    A docstring = a STRING that is the whole statement (its own expression), which is what
    the INDENT/NEWLINE-preceded check below approximates; ordinary string literals stay,
    because those are exactly the text that can reach a stream.
    """
    try:
        out, prev_meaningful = [], tokenize.INDENT
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type == tokenize.COMMENT:
                continue
            if t.type == tokenize.STRING and prev_meaningful in (
                tokenize.INDENT,
                tokenize.NEWLINE,
                tokenize.NL,
                tokenize.DEDENT,
            ):
                continue  # bare string statement => docstring
            out.append(t.string)
            if t.type not in (tokenize.NL, tokenize.COMMENT):
                prev_meaningful = t.type
        return "".join(out)
    except Exception:
        return src  # unparseable -> be strict rather than silently permissive


def _io_missing_encoding(src: str) -> str | None:
    """Return the offending call kind if any text-decoding call omits encoding=.

    Balanced-paren scan, so multi-line calls and nested parens are handled."""
    src = _strip_prose(src)
    # Match ANY module alias, not a literal `subprocess.` — `import subprocess as _sp`
    # decodes identically, and an evaluator slipped `_sp.run(text=True)` straight past the
    # narrow pattern (2026-07-17). We never call a non-subprocess `x.run(text=True)`, so
    # widening this costs no false positives.
    sites = [(r"\.(?:read_text|write_text)\(", "read_text/write_text")]
    sites.append((r"\b\w+\.(?:run|check_output|Popen)\(", "subprocess"))
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


def _stream_writes(src: str) -> list:
    """Every print()/sys.stdout|stderr.write() call, as (match, argument-text)."""
    out = []
    for m in re.finditer(r"\b(?:print|sys\.std(?:out|err)\.write)\(", src):
        depth, j = 1, m.end()
        while j < len(src) and depth:
            depth += {"(": 1, ")": -1}.get(src[j], 0)
            j += 1
        out.append((m, src[m.end() : j]))
    return out


def _prints_nonascii_unguarded(src: str) -> bool:
    """True if a script that CAN emit non-ascii to a stream never reconfigures it.

    The third face of the same cp949 trap (2026-07-17): decoding was guarded, but ENCODING
    our own output wasn't. `gen_palette.py` printed an em-dash, the cp949 console raised
    UnicodeEncodeError, and — since the gate is fail-closed — every commit was blocked.

    NOT "does a print() call hold a non-ascii literal": that sees only inline text, so
    `msg = "한글 — em"; print(msg)` sailed through (an evaluator proved it). Data flow isn't
    statically tractable, so we ask a question that is: strip comments (they never reach a
    stream), then look for any non-ascii left in a file that writes to one.

    Exempt: files whose stream writes ALL go through json.dumps() at its ensure_ascii=True
    default — non-ascii is escaped to \\uXXXX before it reaches the stream. That is exactly
    our hooks' shape (Korean reasons inside a JSON decision) and is genuinely safe; flagging
    them would be noise, and a guard people learn to ignore protects nothing.
    """
    if re.search(r"sys\.std(?:out|err)\.reconfigure\(", src):
        return False
    writes = _stream_writes(src)
    if not writes:
        return False
    if all("json.dumps(" in a and "ensure_ascii=False" not in a for _, a in writes):
        return False
    return any(ord(c) > 127 for c in _strip_prose(src))


# A guard-test file legitimately holds bad-code FIXTURES as string literals, and no static
# scan can tell those from real decode sites. One narrow, greppable opt-out — not a general
# escape hatch: it must be this exact phrase, and it is used by exactly one file.
FIXTURE_MARKER = "selfcheck-exempt: bad-code fixtures, not real call sites"

for s in scripts:
    src = Path(s).read_text(encoding="utf-8")
    if FIXTURE_MARKER in src:
        continue
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
