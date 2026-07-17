# .claude/plan.md — 현재 플랜만 (in-flight)

> 이 파일은 **진행 중인 플랜 하나**만 담는다. `/wook-plan`이 새 플랜을 쓸 때 **덮어쓴다**(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`(결정 로그·기능 섹션)에 있다 — plan.md는 히스토리 보관소가 아니다.

---

# SPEC — 디자인 스택 재편: ui-ux-pro-max 메인 + wook 보조 (승인: 2026-07-17, B안)

형욱 결정: **ui-ux-pro-max(서드파티, 107k★, MIT)를 정식 설치해 디자인 메인 브레인으로,
wook-design은 완전 삭제.** 자동 업데이트 유지를 위해 vendoring 안 함(조정 소실 수용).
흐름: **pro-max(발상·추천) → wook-palette(AA 계산 → tokens.css → conventions 포인터) →
wook-sandbox(격리 제작) → wook-evaluator + 커밋 게이트(검증)**.

## Scope — IN
1. `npm install -g ui-ux-pro-max-cli` + `uipro init --ai claude` 설치(위치 실측) +
   **경량 보안 리뷰**(search.py·SKILL.md에 네트워크 호출/이상 실행 없는지)
2. **wook-design 완전 삭제**. presets 12종(INDEX.md·library.json) + `test_presets.py`는
   **wook-palette로 이전**(AA 강제 유지, 테스트는 수정이지 삭제 아님)
3. 역할 경계 명문화(wook-palette·sandbox SKILL.md 재배선): 추천이 어디서 오든(pro-max
   192종은 대비 미검증) **tokens가 되려면 gen_palette AA 계산 통과 필수**
4. 문서: build-log #23, README 스킬 표·흐름

## Scope — OUT
vendoring(형욱 명시 거부) / pro-max 자체 수정(업데이트가 덮음) / Codex 쪽 init(나중) /
**recipe에 pro-max 존재 체크 ✗**(머신-로컬 설치물 — 원격 클론 테스트가 깨지면 안 됨)

## Edge cases
설치물은 deploy 파이프라인 밖 공존(deploy는 여분 파일 안 지움 → drift 없음) ·
~/.claude/skills/wook-design은 deploy가 안 지우므로 **수동 제거** · pro-max 업데이트로
search.py 경로/인자가 바뀔 수 있음 → 우리 문서는 스킬명 기준으로 느슨하게 기술 ·
게임 UI 레퍼런스(references/app/) 소실은 형욱 수용

## 수용 기준 (Acceptance criteria)
recipe 불변(standing set):
- `selfcheck: python tools/selfcheck.py` exit 0 (스킬 md 12→11)
- `tests: python -B tools/run_tests.py` exit 0 — test_presets가 **wook-palette 새 경로**에서
  12종 AA 전수 통과 포함
- `deploy: python deploy.py --check` exit 0 (+ ~/.claude/skills/wook-design 부재 확인)

설치 시 1회 실측(recipe 밖):
- pro-max `search.py "fintech dashboard" --design-system` → exit 0 + 디자인 시스템 출력
- `~/.claude/skills/ui-ux-pro-max/` 존재 + 자동 트리거 description 확인
- 보안 리뷰 이상 없음
- repo 전체에 `wook-design` 잔여 참조 0 (build-log 히스토리 제외)
- MANUAL(다음 세션): web 디자인 요청 시 pro-max 자동 발동 관찰
