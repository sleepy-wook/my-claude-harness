# .claude/plan.md — 현재 플랜만 (in-flight)

> 진행 중인 플랜 하나만 담는다. `/wook-plan`이 새 플랜을 쓸 때 덮어쓴다(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`.

---

# SPEC — 감축: 안 쓰는 것 삭제 + Ratchet에 감산 규칙 (#33, 승인: 2026-09-21)

형욱: "불필요한 파일·스크립트가 많아지고 매번 오래 걸리는 게 싫다. 정리를 안 해서 복잡해진다."
측정해보니 맞는 지적이었다 — **자기검증 1,848줄 : 런타임 1,340줄 = 1.38배**, 참조 0인 파일 2개,
고아 스킬 1개. 그리고 근본 원인: **Ratchet 원칙에 감산이 없다**(추가만 있고 제거 규칙이 없음).

## Scope — IN
1. **삭제**(형욱 확인): `wook-audit` 스킬(90줄, 다른 문서에서 2번만 언급된 고아) ·
   `core-rules.README.md`(30줄, 참조 0) · `conventions.frontend.example`(30줄, 참조 0)
2. **레시피에서 `deploy --check` 제거** — `~/.claude`가 repo와 동기인지는 **머신 상태**지
   커밋의 속성이 아니다. 이번 세션 **정상 커밋 2번 차단 / 진짜 결함 0건**. 대체물 없음(드리프트는
   `python deploy.py` 한 번으로 해소). 게이트 3줄 → 2줄
3. **core-rules 개정(줄 수 순증 최소, 기존 줄을 고쳐 씀)**:
   - 평가자 = **3단 계층**: 안전장치(훅·게이트·가드·deploy) 변경=항상 / 테스트가 못 잡는 체감
     동작=보통 / 문서·기계적 리팩터=생략. 회당 7~12분이므로 범위를 좁게 준다
   - **감산 규칙 신설**: 코드를 지우면 그 가드·테스트도 같은 커밋에서 지운다. 새 파일은
     "무엇을 대체하나 / 왜 기존 걸로 안 되나"에 답할 수 있을 때만 만든다
4. README 정합화(wook-audit 행 제거, 게이트 설치가 이제 자동임을 반영 — #32 후속 누락분)

## Scope — OUT
- `wook-sandbox`·`wook-brainstorm` 삭제 ✗(형욱: 유지) · `test_promax_tokens.py` 축소 ✗(형욱: pro-max 계속 사용 → 유지)
- 새 가드/스크립트 추가 ✗ — "스크립트가 늘어서 싫다"는데 감시 스크립트를 더하면 자기모순. 규칙으로만
- `tools/` 테스트 축소 ✗ — 테스트는 런타임의 그림자다. 줄이려면 런타임을 줄여야 하고, 지금 런타임에
  덜어낼 곳이 없다(훅 6개 전부 관측된 실패에서 나옴). 별건

## Edge cases
- 레시피 편집 = `guard_paths` ask + 게이트 자기보호 → 커밋에 `GATE_EDIT_OK=1` 필요(= 사람 승인)
- 스킬 삭제로 `selfcheck`의 md frontmatter 개수가 11→10 (정상)
- 삭제 파일이 `~/.claude`엔 잔류(deploy는 prune 안 함) — 미등록/미참조라 무해

## 수용 기준 (Acceptance criteria)
- `python tools/selfcheck.py` exit 0 (md 10개) · `python -B tools/run_tests.py` **11/11** exit 0
- `git grep -l 'wook-audit\|core-rules.README\|conventions.frontend.example' -- ':!docs/' ':!.claude/plan.md'` → 출력 없음
- `.claude/evaluate.recipe`의 실행 줄 = **2개**(`selfcheck`, `tests`), 게이트 여전히 exit 0
- `core-rules.md`에 평가자 3단 계층 + 감산 규칙이 있고, 전체 길이는 17줄 이하 유지(상시 로드 비용)
- **독립 평가자 생략** — 이 변경 자체가 새 3단 계층의 첫 적용 사례다(삭제 + 문서 정합화, 스위트가
  전부 덮음). 대신 위 명령들을 실제 실행한 출력으로 대체한다
