# .claude/plan.md — 현재 플랜만 (in-flight)

> 이 파일은 **진행 중인 플랜 하나**만 담는다. `/wook-plan`이 새 플랜을 쓸 때 **덮어쓴다**(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`(결정 로그·기능 섹션)에 있다 — plan.md는 히스토리 보관소가 아니다.

---

# SPEC — 하네스를 ui-ux-pro-max 스키마에 맞춤 (#25, 승인: 2026-07-17)

형욱 결정: **우리 구조에 pro-max를 맞추지 말고, pro-max에 우리 하네스를 맞춘다.**
지금까지: pro-max 출력 → 우리 어휘로 번역 → 우리 tokens (번역층 = 마찰, 손실)
앞으로: **pro-max 스키마가 표준** → 우리는 걔가 안 하는 **계산·수리·강제**만 얹음

## 실측 근거 (이 플랜의 출발점)
- 걔네 **스키마 16역할 > 우리 10역할** — `On Accent`·`Muted Foreground`·`Card`/`Card Foreground`·
  `On Destructive`까지 있음 → 채택 가치 있음
- 걔네 **렌더러가 16 중 6을 버림**(On Accent 포함) → 에이전트가 못 보고 흰색 추측 = 실제로 당한 함정
  (CTA 2.28:1). 데이터엔 `On Accent=#0F172A`(7.83:1)가 이미 있었음
- 걔네 **값은 1517쌍 중 571쌍(37.6%) AA 실패** — `On Accent/Accent` 113건(CTA!), `Muted Foreground/Muted`
  150건, `Border/Background` 173건, `On Primary/Primary` 50건, `On Secondary` 64, `On Destructive` 21
- **결론**: 올바른 칸을 갖고 있는데 값이 틀렸고, 그나마 그 칸을 화면에 안 보여줌 → 우리 층의 자리

## Scope — IN
1. **`gen_palette.py`를 pro-max 스키마 네이티브로 개편**
   - 16역할 + `--color-*` 네이밍 채택. 우리 `base`/`surface`/`accentInk` 어휘 **폐기**
     (→ 걔네 21스택 코드 생성이 우리 토큰을 그대로 먹음)
   - **CSV 직접 읽기**(`data/colors.csv`) — 렌더러 출력 ✗(6역할 손실)
   - `--check <tokens>`: 의미적 쌍 계산, 미달 시 **exit 1 + 실패 쌍 이름/비율**
   - `--fix`: 실패한 `on-*`만 명암 조정으로 수리(**accent 원본 불변**)
   - `rgba()` 셀 19건 관용 처리(죽지 않고 skip+경고)
2. **`/wook-palette` 재작성 — "pro-max 후처리기"로 축소**
   pro-max `--design-system`(메인) → CSV에서 16역할 회수 → 우리 `--check`/`--fix` →
   `--color-*` tokens 발행 + **recipe에 `tokens-aa:` 자동 심기** → conventions는
   pro-max `design-system/MASTER.md`를 **가리킴**(소유권 안 뺏음)
3. **conventions**: design 도메인은 MASTER.md에 위임, 우리 규칙은 "AA는 계산으로 강제" 하나만
4. **프리셋 12종 폐기**(형욱 결정): `library.json` + `test_presets.py` 제거 → pro-max 192행
   검증 테스트가 대체(훨씬 넓은 회귀 커버리지). wook-design 시절 유물
5. 문서: build-log #25, README 흐름

## Scope — OUT
pro-max 파일 수정 ✗(업데이트가 덮음 — #23 결정) / RN 템플릿 문제 ✗(별건) /
`--fix` 색이론 고도화 ✗(명암 조정만, OKLCH ✗) / sandbox 랜딩 졸업 ✗ /
**Border 3:1 강제 ✗ → 경고만**(형욱 결정: 1.4.11은 'UI 식별에 필요한' 경계만 대상,
장식 divider까지 막으면 오탐 폭발. 강제는 텍스트 쌍만)

## Edge cases
`rgba()` → skip+경고 · `--fix`는 `on-*`만 건드림(브랜드색 불변) · pro-max CSV 헤더가
업데이트로 바뀔 수 있음 → 헤더 이름 기준 읽기, 없으면 스킵 · test_presets 삭제는
게이트 자기보호 발동 → `GATE_EDIT_OK=1` 필요 · 이 repo엔 tokens가 없음 → `tokens-aa`는
*다른* 프로젝트 recipe에 심는 것, 이 repo recipe는 불변

## 수용 기준 (Acceptance criteria) — **전부 통과 (2026-07-17)**
recipe 불변: `selfcheck` / `tests` / `deploy --check` 전부 exit 0 ✅ (8/8 파일)
신규 기준은 전부 **tests**로(recipe 안 늘림) — `tools/test_promax_tokens.py` 13/13 ✅:
- 16역할 파서가 **렌더러가 버리는 6역할을 실제로 회수** ✅ (`on_accent=#0F172A` 확인)
- ~~571건 정확 재현~~ → **불변식 검증으로 변경**(계획 수정): 서드파티 데이터에 숫자를 박으면
  npm 자동 업데이트에 깨지고, pro-max 미설치 원격 클론에서 죽음 → 픽스처로 동작 고정 +
  통합 테스트는 "실패를 찾아내는가"만 단언(현재 398건) + 미설치 시 graceful skip ✅
- AA 통과 → exit 0 / 실패 → exit 1 + 쌍 이름 ✅
- `--fix` → 재검사 통과, `accent` 불변 ✅ (게다가 pro-max 디자이너 정답 `#0F172A`를 독립 재현)
- `rgba()` skip ✅ / Border는 경고이지 exit 1 아님 ✅
- **실거래 ✅**: 임시 repo에서 pro-max 원본 토큰 커밋 → **차단**(on_destructive 3.76:1) →
  `--fix` → **커밋 성공** → 누가 on_accent를 흰색으로 되돌림 → **다시 차단**(2.28:1)

## 이 플랜이 부수적으로 잡은 것 (#26, #27)
- **#26**: 실거래 테스트가 **게이트 fail-open 3건**을 드러냄 — `subprocess(text=True)` encoding
  누락으로 cp949 크래시 → 그 크래시가 "통과"로 처리됨. fail-closed 전환 + 가드를
  `subprocess`까지 확장 → `remind_evaluator`·`gate_runner.git()`·`install_gate` 추가 적발.
- **#27 (독립 평가자 FAIL)**: 위 "실거래 증명"이 **무효**였음 — 내 셸의 `PYTHONIOENCODING`이
  가렸고, `run_tests.py`가 같은 변수를 주입해 테스트 13/13이 **깨진 코드를 통과**시켰다.
  실사용자 환경에선 `gen_palette` stdout 크래시 + #26 fail-closed = **모든 커밋 영구 차단**.
  진짜 원인은 **selfcheck가 `skills/*/scripts/`를 스캔조차 안 한 것**(게이트가 실행하는 스크립트가
  가드 커버리지 밖). 수정 후 env var 없이 전 루프 재실증.

> **이 플랜의 교훈(하네스 일반화)**: 초록색 테스트가 초록색 제품을 뜻하지 않는다. 테스트
> 하네스가 환경을 보정하면 그 결함은 구조적으로 안 보이고, 가드는 **자기가 스캔하는 범위 밖**을
> 절대 못 지킨다. 그리고 **자기평가는 이 세션에서 2번 연속 틀렸다**(#24, #25) — 독립 평가자가
> 둘 다 잡았다.
