#!/usr/bin/env python3
"""Behavioral tests for the arm_gate SessionStart hook (#32).

The hook installs the commit gate in a repo that declares `.claude/evaluate.recipe` but
has no gate installed — the case a fresh clone always hits, because `.git/hooks/` is never
cloned. Self-contained throwaway repos. Exit 0 = all pass.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # gate-executed script contract: our own output must survive a cp949 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
HOOK = str(REPO / "claude" / "hooks" / "arm_gate.py")
MARKER = "wook-harness commit gate"
results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def clean_env(**extra):
    """os.environ minus GIT_* — see test_gate_runner.clean_env (#30 root cause)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra)
    return env


def repo(recipe=True, git=True):
    d = Path(tempfile.mkdtemp(prefix="armgate_"))
    if git:
        subprocess.run(["git", "init", "-q"], cwd=d, check=True, env=clean_env())
    (d / ".claude").mkdir()
    if recipe:
        (d / ".claude" / "evaluate.recipe").write_text("ok: true\n", encoding="utf-8")
    return d


def run_hook(d):
    p = subprocess.run(
        [sys.executable, "-B", HOOK],
        input=json.dumps({"cwd": str(d), "hook_event_name": "SessionStart"}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=clean_env(),
        timeout=60,
    )
    return p.returncode, p.stdout.strip()


def pre_commit(d):
    return d / ".git" / "hooks" / "pre-commit"


print("Test A — recipe present, no gate -> installs it")
d = repo()
rc, out = run_hook(d)
check("A exit 0", rc, 0)
check("A hook file created", pre_commit(d).is_file(), True)
check(
    "A shim is ours",
    MARKER in pre_commit(d).read_text(encoding="utf-8"),
    True,
)
check("A reports the install", "커밋 게이트를 설치" in out, True)

print("Test B — already ours -> silent (success is silent)")
rc, out = run_hook(d)  # same repo, gate now installed
check("B exit 0", rc, 0)
check("B no output", out, "")

print("Test C — no recipe -> does nothing")
d = repo(recipe=False)
rc, out = run_hook(d)
check("C exit 0", rc, 0)
check("C no output", out, "")
check("C no hook installed", pre_commit(d).exists(), False)

print("Test D — foreign pre-commit -> never overwritten")
d = repo()
foreign = "#!/bin/sh\necho someone elses hook\n"
pre_commit(d).parent.mkdir(parents=True, exist_ok=True)
pre_commit(d).write_text(foreign, encoding="utf-8")
rc, out = run_hook(d)
check("D exit 0 (never blocks the session)", rc, 0)
check("D foreign hook preserved", pre_commit(d).read_text(encoding="utf-8"), foreign)
check("D surfaces the refusal", "설치하지 못했" in out, True)

print("Test E — not a git repo -> silent")
d = repo(git=False)
rc, out = run_hook(d)
check("E exit 0", rc, 0)
check("E no output", out, "")

print("Test F — finds the recipe from a subdirectory")
d = repo()
sub = d / "src" / "deep"
sub.mkdir(parents=True)
rc, out = run_hook(sub)
check("F exit 0", rc, 0)
check("F installed from the repo root", pre_commit(d).is_file(), True)

print("Test G — malformed event -> silent, never raises")
p = subprocess.run(
    [sys.executable, "-B", HOOK],
    input="not json",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=clean_env(),
    timeout=30,
)
check("G exit 0", p.returncode, 0)
check("G no output", p.stdout.strip(), "")

print("Test H — evaluate-off present -> don't arm it behind their back")
d = repo()
(d / ".claude" / "evaluate-off").write_text("", encoding="utf-8")
rc, out = run_hook(d)
check("H exit 0", rc, 0)
check("H no hook installed", pre_commit(d).exists(), False)

print("Test I — the notice says WHAT was armed (repo-authored shell, shown not hidden)")
d = repo()
(d / ".claude" / "evaluate.recipe").write_text(
    "# comment line\ntests: pytest -q\nlint: ruff check .\n", encoding="utf-8"
)
rc, out = run_hook(d)
msg = json.loads(out)["hookSpecificOutput"]["systemMessage"]
check(
    "I lists each check",
    "tests: pytest -q" in msg and "lint: ruff check ." in msg,
    True,
)
check("I omits comment lines", "# comment line" not in msg, True)
check(
    "I names the escape hatches", "--no-verify" in msg and "evaluate-off" in msg, True
)

print("Test J — end-to-end through a REAL git hook environment")
# The suites scrub GIT_* so throwaway repos stay isolated (#30). That means nothing else
# exercises the environment production actually runs in — git exports GIT_INDEX_FILE,
# GIT_PREFIX, GIT_AUTHOR_* to the hook. This test commits for real, so the gate is invoked
# by git itself with all of that present.
d = repo()
(d / ".claude" / "evaluate.recipe").write_text("boom: false\n", encoding="utf-8")
run_hook(d)  # arm it
(d / "a.txt").write_text("hi\n", encoding="utf-8")
e = clean_env()
subprocess.run(["git", "add", "-A"], cwd=d, check=True, env=e)
p = subprocess.run(
    ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x"],
    cwd=d,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=e,
)
check("J failing recipe blocks a real commit", p.returncode != 0, True)
check("J names the failing check", "boom" in (p.stdout + p.stderr), True)
(d / ".claude" / "evaluate.recipe").write_text("ok: true\n", encoding="utf-8")
subprocess.run(["git", "add", "-A"], cwd=d, check=True, env=e)
p = subprocess.run(
    ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x"],
    cwd=d,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=e,
)
check("J passing recipe allows it", p.returncode, 0)

for p_ in Path(tempfile.gettempdir()).glob("armgate_*"):
    shutil.rmtree(p_, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
