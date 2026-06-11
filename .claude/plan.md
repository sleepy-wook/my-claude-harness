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

---

# SPEC — 컨벤션 시스템 (frontend 수직 슬라이스)

> 2026-06-11 `/wook-plan`(수동 적용). 승인됨. 도메인별 코딩 컨벤션을 AI가 항상 참고/유지하게.
> 재사용 카탈로그의 형제 — 같은 "파일 존재=ON" + "AI 판단 / hook 결정론" 분담 패턴.

## Scope — IN
1. `inject_convention_pointer.py` (UserPromptSubmit, 형제 hook): `.claude/conventions/` 있으면
   매 턴 안내(공통 `shared.md` 항상 + 도메인별 `<domain>.md` 작업 도메인 확인). 없으면 무출력.
2. `check_convention_pointers.py` (Stop, 비차단 형제 hook): 컨벤션 문서의 `path:symbol`
   포인터가 안 풀리면 알림(스테일 탐지). reuse 검사와 동일 방식, 별도 파일.
3. `/wook-conventions` 스킬 (bimodal): greenfield=질문하며 확정 / brownfield=도메인 코드만
   훑어 초안+불일치 플래그. 값은 실제 토큰/소스 파일 포인터로(복제 X). 기계검증 규칙은
   `evaluate.recipe`에 추가 제안.
4. core-rules: 컨벤션 유지보수 기본값 1줄(정/변경/폐기 시 해당 문서 갱신).
5. `harness/conventions.frontend.example` 템플릿.
6. settings.hooks.json 배선 + build-log.

## Scope — OUT (기계장치 검증 후 복제)
- backend/db/infra/data/shared 실제 컨벤션 파일, 실제 stylelint/도구 설치(프로젝트 책임).

## Edge cases
- 도메인 코드 판별 모호 → 휴리스틱+질문. greenfield인데 소스 파일 없음 → 플래그.
- 문서↔게이트 동기화 → 문서에 `[강제: <체크명>]` 표기. 모든 에러 경로 = 조용히 통과.

## Acceptance criteria (실행 가능 — `tools/test_conventions.py` + selfcheck)
1. `python tools/selfcheck.py` → exit 0 (새 hook 컴파일 + `/wook-conventions` frontmatter).
2. 포인터 hook: conventions 있는 샘플 → "shared 항상 + 도메인" 주입 / 없으면 무출력 exit 0.
3. 스테일 탐지: 없는 `path:symbol` → 알림, 전부 유효 → 무알림.
4. 게이트 강제 데모: 샘플 recipe의 컨벤션 체크(raw-hex) 위반 → Stop block, 고치면 allow.
5. `python deploy.py --check`가 새 파일 인식.

## 산출물(추가)
- `claude/hooks/{inject_convention_pointer, check_convention_pointers}.py`
- `claude/skills/wook-conventions/SKILL.md`, `claude/harness/conventions.frontend.example`
- `tools/test_conventions.py`
