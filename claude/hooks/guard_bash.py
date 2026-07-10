#!/usr/bin/env python3
"""PreToolUse hook: ASK before catastrophic shell commands (deterministic floor).

Windows has no OS-level sandbox for Claude Code (Seatbelt/bubblewrap are
macOS/Linux), so the hook layer is the only deterministic floor here. This guard
matches an ULTRA-conservative list of commands whose blast radius is a home
directory, a repo's history, or the commit gate itself — and returns
`permissionDecision: "ask"` (NOT deny): the human decides, every time.

Two rule families:
  1. Catastrophic commands — rm -rf aimed at home/root/drive-root/parent,
     git push --force (not --force-with-lease), git reset --hard, git clean -f*,
     Remove-Item -Recurse -Force aimed at home/root, rd|rmdir /s, del /s,
     mkfs, dd onto a device, the classic fork bomb.
  2. Gate-bypass channels — deleting/overwriting .git/hooks/pre-commit, creating
     .claude/evaluate-off, or rewriting .claude/evaluate.recipe via shell
     redirection/sed -i/tee (the Edit/Write path is covered by guard_paths.py).
     Removing evaluate-off (re-arming the gate) is deliberately NOT matched.

This is a POLICY layer, not a security boundary: research (Ona, 2026-03) shows
agents can route around string matching via interpreters (`python -c`), linkers,
etc. The goal is stopping the accidental/on-autopilot case, which is where the
documented incidents (2025-12 home-dir deletion) actually happened. Anything not
matched falls through to the normal permission flow. Any error => exit 0.
"""

import json
import re
import sys

RISKY_BASE = {"", "~", "$home", "${home}", "..", "../..", "/*"}


def _risky_target(tok: str) -> bool:
    """True if a deletion target is home/root/drive-root/parent — not a project path."""
    t = tok.strip("'\"")
    if not t or t.startswith("-"):
        return False
    tl = t.lower().replace("\\", "/")
    base = tl.rstrip("/*") or ("/*" if tl.startswith("/") else "")
    if base in RISKY_BASE:
        return True
    if tl == "/" or tl.startswith("/*"):
        return True
    # drive roots: C:  C:/  /c  /c/ — and $HOME with a trailing slash only
    return bool(re.fullmatch(r"[a-z]:|/[a-z]", base)) or base in {"$home/", "${home}/"}


def _rm_reason(cmd: str):
    for m in re.finditer(r"(?:^|[;&|]\s*)rm\s+((?:-\S+\s+)+)([^;&|]+)", cmd):
        flags = m.group(1)
        if not (re.search(r"-\S*r", flags) and re.search(r"-\S*f", flags)):
            continue
        for tok in m.group(2).split():
            if _risky_target(tok):
                return f"rm -rf 대상이 홈/루트/상위 디렉토리입니다: {tok}"
    return None


def guard_reason(cmd: str):
    """Return a human reason to ask, else None. Conservative: no match => silent."""
    # --- 1. catastrophic commands ------------------------------------------
    r = _rm_reason(cmd)
    if r:
        return r
    if re.search(r"\bgit\s+push\b[^;&|]*(\s--force\b(?!-with-lease)|\s-f\b)", cmd):
        return "git push --force (원격 히스토리 덮어쓰기)"
    if re.search(r"\bgit\s+reset\s+[^;&|]*--hard", cmd):
        return "git reset --hard (작업 내용 파기)"
    if re.search(r"\bgit\s+clean\s+-[A-Za-z]*f", cmd):
        return "git clean -f (미추적 파일 일괄 삭제)"
    if re.search(r"\b(rd|rmdir)\s+/s\b", cmd, re.IGNORECASE):
        return "rd /s (디렉토리 트리 삭제)"
    if re.search(r"\bdel\s+/[a-z]*s\b", cmd, re.IGNORECASE):
        return "del /s (재귀 삭제)"
    if re.search(
        r"remove-item\b(?=[^;&|]*-recurse)(?=[^;&|]*-force)", cmd, re.IGNORECASE
    ):
        seg = re.search(r"remove-item\b[^;&|]*", cmd, re.IGNORECASE).group(0)
        if re.search(
            r"\$env:userprofile|\$home\b|[a-z]:[/\\]?(\s|$|['\"])|~[/\\]?(\s|$|['\"])",
            seg,
            re.IGNORECASE,
        ):
            return "Remove-Item -Recurse -Force 대상이 홈/드라이브 루트입니다"
    if re.search(r"\bmkfs(\.\w+)?\b", cmd):
        return "mkfs (파일시스템 포맷)"
    if re.search(r"\bdd\b[^;&|]*\bof=/dev/", cmd):
        return "dd → 디바이스 직접 쓰기"
    if re.search(r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:", cmd):
        return "fork bomb"

    # --- 2. gate-bypass channels --------------------------------------------
    if ".git/hooks/pre-commit" in cmd.replace("\\", "/") and re.search(
        r"\b(rm|mv|del)\b|>{1,2}", cmd
    ):
        return "커밋 게이트(.git/hooks/pre-commit) 제거/변조"
    if re.search(
        r"(touch|New-Item|\bni\b|>{1,2})\s*[^;&|]*evaluate-off", cmd, re.IGNORECASE
    ):
        return "커밋 게이트 비활성화 파일(.claude/evaluate-off) 생성"
    if re.search(
        r"(>{1,2}\s*\S*evaluate\.recipe|(sed\s+-i|tee)\s[^;&|]*evaluate\.recipe)", cmd
    ):
        return "커밋 게이트 기준(evaluate.recipe)을 셸로 재작성"

    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = (event.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    reason = guard_reason(cmd)
    if reason is None:
        return 0  # not matched -> normal permission flow

    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": (
                        f"guard_bash: {reason} — 개발자 확인이 필요한 명령입니다. "
                        f"의도한 작업이면 승인하세요."
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
