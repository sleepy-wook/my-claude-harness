# .claude/plan.md — 현재 플랜만 (in-flight)

> 이 파일은 **진행 중인 플랜 하나**만 담는다. `/wook-plan`이 새 플랜을 쓸 때 **덮어쓴다**(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`(결정 로그·기능 섹션)에 있다 — plan.md는 히스토리 보관소가 아니다.

---

# SPEC — Harness 자기검증 (이 repo의 상시 플랜)

> 이 repo가 자기 자신을 검증하도록 `.claude/evaluate.recipe`에 박은 수용 기준. 레시피가
> 존재하므로 **커밋 시 게이트(`gate_on_commit.py`)가** 이 기준으로 검증한다.

## Scope
- **포함:** repo가 배포하는 하네스 소스의 정적 무결성
  - 모든 hook/deploy 파이썬 스크립트 컴파일
  - `claude/settings.hooks.json` 유효 JSON + 4개 이벤트(Pre/PostToolUse·UserPromptSubmit·Stop)
  - 모든 skill/agent 마크다운에 `name:` frontmatter
  - 텍스트 I/O는 `encoding="utf-8"` 고정(Windows cp949 방지) / git에 비밀 파일 미추적
  - repo ↔ `~/.claude` 일관(소스 고치고 배포 안 한 drift 없음)
- **제외:** Claude Code 런타임 동작/실제 hook 발화(스크립트로 단언 불가).

## Acceptance criteria (각 exit 0 = 통과)
1. 스크립트 컴파일·settings 4이벤트·frontmatter·encoding 가드·비밀 미추적 — `tools/selfcheck.py`
2. 배포 일관 — `python deploy.py --check` (drift면 exit 1)

## 검증 레시피 (`.claude/evaluate.recipe`)
```
selfcheck: python tools/selfcheck.py
deploy:    python deploy.py --check
```
> 커밋 시 `gate_on_commit.py`가 이 레시피를 돌려 통과해야 커밋된다(긴급 시 `git commit --no-verify`로 우회).
