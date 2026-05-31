# SPEC — Harness 자기검증 (self-verification)

> `/wook-plan`으로 작성. 이 repo가 자기 자신을 검증하도록 `.claude/evaluate.recipe`에 박은
> 수용 기준의 명세. 레시피가 존재하므로 이 repo의 Stop 게이트는 ON이다.

## Scope
- **포함:** repo가 배포하는 하네스 소스의 정적 무결성
  - 모든 hook/deploy 파이썬 스크립트 컴파일
  - `claude/settings.hooks.json` 유효 JSON + 4개 이벤트(Pre/PostToolUse·UserPromptSubmit·Stop)
  - 모든 skill/agent 마크다운에 `name:` frontmatter
  - git에 비밀 파일 미추적
  - repo ↔ `~/.claude` 일관(소스 고치고 배포 안 한 drift 없음)
- **제외:** Claude Code 런타임 동작/실제 hook 발화(스크립트로 단언 불가), 게이트 정체 로직 재검증.

## Edge cases
- 이 레시피 파일 존재 = 이 repo 게이트 ON(의도). 앞으로 여기 코드 편집도 턴 끝에 검증받음.
- 게이트는 명령을 Windows에선 cmd.exe로 실행(`shell=True`) → 셸 glob 불가 → 단일
  `python tools/selfcheck.py`로 묶어 OS 무관.

## Acceptance criteria (각 exit 0 = 통과)
1. 스크립트 컴파일 — `tools/selfcheck.py` (py_compile)
2. settings 4 이벤트 — `tools/selfcheck.py` (JSON + 키 집합)
3. frontmatter `name:` — `tools/selfcheck.py` (skills/agents)
4. 비밀 미추적 — `tools/selfcheck.py` (`git ls-files` 패턴 검사)
5. 배포 일관 — `python deploy.py --check` (drift면 exit 1)

## 검증 레시피 (`.claude/evaluate.recipe`)
```
selfcheck: python tools/selfcheck.py
deploy:    python deploy.py --check
```

## 산출물
- `tools/selfcheck.py` (기준 1~4)
- `deploy.py` — `--check`가 drift 시 exit 1 (기준 5)
- `.claude/evaluate.recipe`, `.claude/plan.md`
