#!/usr/bin/env python3
"""Commit gate runner — executed by `.git/hooks/pre-commit` (see install_gate.py).

v2 of the commit gate: it moved from a PreToolUse hook that string-matched Bash
commands into git's own pre-commit hook, so it fires identically for Claude Code,
Codex, any other agent, AND a human committing from a terminal — and `--no-verify`
is git-native instead of reimplemented. Exit non-zero blocks the commit; the failure
output flows back to whoever ran `git commit` (for an agent, via the Bash tool result).

Checks, in order:
  1. SELF-PROTECTION — if the STAGED diff modifies/deletes `.claude/evaluate.recipe`
     or deletes test files, fail unless GATE_EDIT_OK=1. An agent under gate pressure
     tends to fix the check instead of the code (CI-gaming); weakening the bar must be
     a conscious human act. Adding a recipe (status A) is arming the gate, not
     weakening it, so it passes.
  2. RECIPE — every `name: command` line must exit 0. Commands run via `bash -c`
     where available so POSIX syntax behaves the same on Windows (Git Bash).
  3. STALL DETECTION — the same normalized failure signature 3 commits in a row
     switches the message from "fix and retry" to "stop iterating, summarize the
     blocker, ask the developer". State: `<git-dir>/wook-gate-state.json`.
  4. POINTER FRESHNESS (warning only, never blocks) — reuse-index / conventions
     `path:symbol` pointers that no longer resolve are listed for /wook-index /
     /wook-conventions. Commit time is when these should be fresh.

Activation: `.claude/evaluate.recipe` exists at the repo root. `.claude/evaluate-off`
disables. Any internal error => allow (never trap the developer).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

STALL_LIMIT = 3
CHECK_TIMEOUT = 280

TEST_FILE_RE = re.compile(r"(^|[/\\])(test_[^/\\]+|[^/\\]+_test\.[^/\\]+|tests[/\\])")


def _utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def git(root, *args):
    """Run git and decode as UTF-8 — git emits UTF-8 paths/messages, and the Windows
    locale (cp949) would raise on any Korean filename, which used to leave
    staged_weakening() with no diff and silently disarm self-protection."""
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        return p.returncode, p.stdout
    except Exception:
        return 1, ""


def find_root(start: Path) -> Path:
    """Repo root: prefer git's answer; fall back to walking up for `.claude/`."""
    rc, out = git(start, "rev-parse", "--show-toplevel")
    if rc == 0 and out.strip():
        return Path(out.strip())
    cur = start
    for _ in range(40):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start


def load_recipe(root: Path):
    f = root / ".claude" / "evaluate.recipe"
    if not f.exists():
        return None
    checks = []
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        name, cmd = s.split(":", 1)
        name, cmd = name.strip(), re.split(r"\s+#", cmd.strip(), maxsplit=1)[0].strip()
        if name and cmd:
            checks.append((name, cmd))
    return checks or None


def find_bash() -> str | None:
    """Locate a Git Bash / MSYS bash — NOT the WSL launcher.

    On Windows with WSL installed, `shutil.which("bash")` returns
    `C:\\Windows\\System32\\bash.exe`, the WSL entry point. Running the recipe
    through it executes the checks inside a *different* (Linux) filesystem where the
    project path (`C:\\...` -> `/mnt/c/...`) and the Windows `python` don't exist, so
    every check fails and the commit is wrongly denied (this also let a Windows
    `--no-verify`-less commit slip through when the gate errored). Skip anything under
    `%WINDIR%` and prefer real Git Bash; None => caller falls back to the OS shell."""
    windir = os.environ.get("WINDIR", r"C:\Windows").lower()
    found = shutil.which("bash")
    if found and not found.lower().startswith(windir):
        return found  # Linux/Mac (/usr/bin/bash) or Git Bash earlier on PATH
    for cand in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if os.path.exists(cand):
            return cand
    try:  # derive from the active git install (handles non-default drives)
        ep = subprocess.run(
            ["git", "--exec-path"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        ).stdout.strip()
        if ep:
            for up in Path(ep).parents:
                cand = up / "bin" / "bash.exe"
                if cand.exists():
                    return str(cand)
    except Exception:
        pass
    return None  # no Git Bash -> run via the OS shell (cmd.exe on Windows)


def run(cmd: str, cwd: Path):
    """Run a recipe command via Git Bash where available so POSIX syntax (`!`, globs,
    pipes) behaves the same on every OS. The WSL bash is deliberately avoided (see
    find_bash); without bash we fall back to the OS shell (cmd.exe on Windows)."""
    try:
        bash = find_bash()
        argv, shell = ([bash, "-c", cmd], False) if bash else (cmd, True)
        p = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",  # NOT the locale default: cp949 crashes on any — or 한글
            errors="replace",  # in a check's output, and the crash used to pass the gate
            timeout=CHECK_TIMEOUT,
            shell=shell,
        )
        return p.returncode, (p.stdout + p.stderr)
    except Exception as e:
        # "could not verify" is NOT "verified ok" — same iron law the evaluator follows
        # (INCONCLUSIVE never becomes PASS). A crashed/timed-out check fails the gate; the
        # escape hatches are the explicit ones (--no-verify / .claude/evaluate-off), not a
        # silent pass. This used to `return 0` and hid a real UnicodeDecodeError (2026-07-17).
        return 1, f"(check could not be run: {e})"


# ---- 1. self-protection ------------------------------------------------------


def staged_weakening(root: Path):
    """Return reasons the staged diff weakens the gate itself, or [] if clean."""
    rc, out = git(root, "diff", "--cached", "--name-status")
    if rc != 0:
        return []  # no git / no staging info -> nothing to judge, never trap
    reasons = []
    for ln in out.splitlines():
        parts = ln.split("\t")
        if len(parts) < 2:
            continue
        status, paths = parts[0], [p.replace("\\", "/") for p in parts[1:]]
        path = paths[-1]  # rename: judge the destination; deletion: the old path
        if (
            path.endswith(".claude/evaluate.recipe")
            or path == ".claude/evaluate.recipe"
        ):
            if not status.startswith("A"):  # adding a recipe arms the gate: fine
                reasons.append(f"{status}\t{path} (커밋 게이트의 기준 파일)")
        elif status.startswith("D") and TEST_FILE_RE.search(path):
            reasons.append(f"{status}\t{path} (테스트 파일 삭제)")
    return reasons


# ---- 3. stall detection ------------------------------------------------------


def state_file(root: Path) -> Path | None:
    rc, out = git(root, "rev-parse", "--git-dir")
    if rc != 0 or not out.strip():
        return None
    gd = Path(out.strip())
    if not gd.is_absolute():
        gd = root / gd
    return gd / "wook-gate-state.json"


def failure_signature(failures) -> str:
    parts = []
    for name, _cmd, out in failures:
        first = next((l for l in out.strip().splitlines() if l.strip()), "")
        parts.append(name + "|" + re.sub(r"[0-9]+|0x[0-9a-fA-F]+", "#", first).lower())
    return hashlib.sha1("\n".join(sorted(parts)).encode("utf-8")).hexdigest()


def bump_stall(root: Path, sig: str) -> int:
    sf = state_file(root)
    if sf is None:
        return 1
    count = 1
    try:
        prev = json.loads(sf.read_text(encoding="utf-8"))
        if prev.get("sig") == sig:
            count = int(prev.get("count", 0)) + 1
    except Exception:
        pass
    try:
        sf.write_text(json.dumps({"sig": sig, "count": count}), encoding="utf-8")
    except Exception:
        pass
    return count


def clear_stall(root: Path):
    sf = state_file(root)
    try:
        if sf is not None and sf.exists():
            sf.unlink()
    except Exception:
        pass


# ---- 4. pointer freshness (warnings) ------------------------------------------


def stale_pointers(root: Path) -> list[str]:
    """`- name · desc · path:symbol` lines in reuse-index/ and conventions/ whose
    pointer no longer resolves. Same format as /wook-index and /wook-conventions."""
    stale = []
    for sub in ("reuse-index", "conventions"):
        d = root / ".claude" / sub
        if not d.is_dir():
            continue
        for doc in sorted(d.glob("*.md")):
            try:
                lines = doc.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue
            for line in lines:
                line = line.strip()
                if not line.startswith("- ") or "·" not in line or ":" not in line:
                    continue
                ptr = line.split("·")[-1].strip()
                path, _, sym = ptr.rpartition(":")
                if not path or not sym:
                    continue
                f = root / path
                try:
                    ok = f.is_file() and re.search(
                        rf"\b{re.escape(sym)}\b", f.read_text(encoding="utf-8")
                    )
                except Exception:
                    ok = False
                if not ok:
                    stale.append(f"{sub}/{doc.name}: {ptr}")
    return stale


# ---- main ---------------------------------------------------------------------


def main() -> int:
    _utf8_stdout()
    cwd = Path(os.getcwd())
    root = find_root(cwd)

    if (root / ".claude" / "evaluate-off").exists():
        return 0
    checks = load_recipe(root)
    if checks is None:
        return 0  # no recipe => gate not active here

    # 1. self-protection: the gate refuses commits that quietly disarm the gate.
    if os.environ.get("GATE_EDIT_OK") != "1":
        weakening = staged_weakening(root)
        if weakening:
            print("COMMIT GATE: 이 커밋은 게이트 자체를 약화시키는 변경을 포함합니다:")
            for r in weakening:
                print("  -", r)
            print(
                "\n의도한 변경이면 사람이 확인했다는 표시로 다음 중 하나로 커밋하세요:\n"
                "  GATE_EDIT_OK=1 git commit ...   (기준 변경을 승인)\n"
                "  git commit --no-verify ...      (게이트 전체 우회)"
            )
            return 1

    # 2. recipe checks.
    failures = []
    for name, cmd in checks:
        rc, out = run(cmd, root)
        if rc != 0:
            failures.append((name, cmd, out))

    if not failures:
        clear_stall(root)
        stale = stale_pointers(root)
        if stale:
            listed = "\n".join(f"  - {s}" for s in stale[:10])
            more = f"\n  …(+{len(stale) - 10} more)" if len(stale) > 10 else ""
            print(
                f"⚠️  (경고, 커밋은 진행됨) stale pointer {len(stale)}건 — 가리키는 코드가 "
                f"더 이상 없음. /wook-index 또는 /wook-conventions로 갱신:\n{listed}{more}"
            )
        return 0

    # 3. failing: report, with stall escalation.
    count = bump_stall(root, failure_signature(failures))
    failed = ", ".join(n for n, *_ in failures)
    combined = "\n\n".join(f"[{n}] {c}\n{o}" for n, c, o in failures)
    tail = "\n".join(combined.strip().splitlines()[-30:])

    if count >= STALL_LIMIT:
        print(
            f"COMMIT GATE — STALLED: 같은 실패가 {count}회 연속입니다 [{failed}].\n"
            "같은 수정을 반복하지 말고, 지금까지의 시도와 블로커를 요약해서 개발자에게 "
            "물어보세요. (우회가 정당하면 --no-verify)\n"
        )
    else:
        print(
            f"COMMIT GATE: 실패한 체크 [{failed}] — 고친 뒤 다시 커밋하세요. "
            f"(우회: git commit --no-verify)\n"
        )
    print(tail)
    return 1


if __name__ == "__main__":
    sys.exit(main())
