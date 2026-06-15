# claude-harness — 빌드 기록 (build log)

> 설계 명세는 `claude-harness-design.md`(= source of truth). 이 문서는 **실제로 무엇을
> 만들었는지** 추적하는 살아있는 기록이다. 스텝마다 갱신한다.
>
> 최종 갱신: 2026-06-11

> **유지 정책 (무한 성장 방지 — 리서치 3각도 수렴 레시피):**
> ① **현재 상태/인덱스**는 맨 위(§3 파일 인벤토리 = 라이브 스냅샷, 항상 최신) · ② **최근** 기능
> 서술은 verbatim · ③ 오래되어 *cold*가 된 기능 서술은 `docs/build-log-archive/`로 이동(삭제 X,
> 검색 가능) · ④ 결정(§1)은 **status로 supersede**(대체/폐기 표시, 삭제 X) · ⑤ 통합하되 *요약을
> 또 요약하지 않음*(드리프트 방지). `tools/selfcheck.py`가 임계(>700줄)에서 "아카이브할 때"를 알린다.

---

## 0. 환경 사실 (검증된 값)

| 항목 | 값 | 비고 |
|------|----|----|
| Claude Code | v2.1.143 | `/goal`(2.1.139+)·`defer`(2.1.89+)·`terminalSequence`(2.1.141+)·`if`(2.1.85+) 전부 가용 |
| OS | Windows_NT | hook은 **Git Bash로 실행**(공식 docs 확인) |
| 셸 | Git Bash (MSYS bash 4.4.23) | shell-form hook 기본 실행기 |
| 설치됨 | node v20.19.0, npm 10.8.2, python 3.12.10, ruff 0.13.1, git 2.34.1 | |
| **없음** | **jq, prettier(global), black** | → hook JSON 파싱은 **Python stdlib**로 통일 |
| config 위치 | `%USERPROFILE%\.claude` (`~/.claude`) | `CLAUDE_CONFIG_DIR` 미설정 |

### 함정 메모 (재발 방지)
- **`/tmp` 경로 함정:** bash의 `/tmp` ≠ 네이티브 Windows python의 `C:\tmp`. 테스트 파일은
  프로젝트 경로(`C:/my-claude-harness/...`)로 둘 것. 실제 hook은 Claude가 진짜 Windows
  경로를 넘기므로 무관.
- **PostToolUse는 `exit 2`로 차단 불가** (도구 이미 실행됨). 루프 차단은 최상위
  `{"decision":"block"}`. 자동 포맷처럼 교정만 하면 그냥 exit 0.
- **`defer`는 `-p`(non-interactive) 전용.** 인터랙티브 우선순위는 `deny > ask > allow`.
- **`additionalContext`는 사실 진술로.** 명령조면 prompt-injection 방어가 발동해 무시됨.
- **exec form(`args` 배열):** `command`를 셸 없이 직접 spawn → Git Bash 프로필 오염/따옴표 문제 회피. 채택.

---

## 1. 결정 로그 (decisions)

> **불변 기록(ADR식).** 결정이 뒤집히면 행을 삭제하지 않고 근거 끝에 `→ **대체됨**(날짜/항목)` 또는
> `→ **폐기**`를 단다 — "왜 예전엔 X였나"를 보존하되 현재 뷰를 흐리지 않게.

| 날짜 | 결정 | 근거 |
|------|------|------|
| 2026-05-31 | hook JSON 파싱 = **Python stdlib** | jq 미설치, Windows에서 가장 안정, 추가 설치 0 |
| 2026-05-31 | 첫 hook 적용 범위 = **Global `~/.claude`** | 설계 §2 "어느 환경에서든 동일" |
| 2026-05-31 | 포매터 = **ruff(.py)부터**, 확장 가능 구조 | 이미 설치됨, 즉시 동작 |
| 2026-05-31 | core-rules 시드 3개 확정(과잉행동·테스트·추측) | 형욱 확인("정확해") |
| 2026-05-31 | git = **별도 깨끗한 repo + 배포** (`~/.claude` 직접 git ✗) | repo에 비밀 0 → 구조적 안전, §7 공개 대비, docs+코드 한 곳 |
| 2026-05-31 | 작업 도메인 = **4개 전부**(일반코드·백엔드·프론트·DB) | Evaluator는 N개 ✗ → 하나 + 도메인별 레시피(§0-3) |
| 2026-05-31 | 첫 Evaluator = **온디맨드 `/wook-evaluate`**(일반코드 레시피부터) | Anthropic "Evaluator 하나부터", 위험 낮음, 신뢰 쌓이면 하드게이트 승격 |
| 2026-05-31 | 자동화 = **Stop hook 게이트**(opt-in 마커, 테스트만, 재시도 3회) | 형욱 진짜 목표="알아서 호출". command형(싸고 결정론)·마커로 침습성 제어 · → **대체됨**(2026-06-01 default-ON by 레시피) |
| 2026-06-01 | 게이트 고도화: **정체(시그니처) 감지 + 게이트 설정화 + `-B`** | 단순 N회 대신 진행/정체 구분(§0-4), 마커로 tests/lint/build 선택 |
| 2026-06-01 | 검증 **레시피 구동**(`.claude/evaluate.recipe`, 폴백 자동탐지) | stack 하드코딩 ✗ → 프로젝트가 `name: 명령` 선언, 갈아끼움(§0-3). #6을 N개 레시피 대신 한 메커니즘으로 |
| 2026-06-01 | #8 Planner = **skill `/wook-plan`**(수용 기준→레시피로 박음) | PGE 통합(generic 플래닝과 차별). 서브에이전트화는 나중 |
| 2026-06-01 | 커스텀 스킬/에이전트 **`wook-` 접두사**(`/wook-plan`·`/wook-evaluate`·`wook-evaluator`) | 네이티브 plan 모드·플러그인과 충돌/혼동 제거(형욱 닉네임 네임스페이스) |
| 2026-06-01 | 게이트 **default-ON by 레시피**(opt-in 마커 폐지, off=`.claude/evaluate-off`) | "켜는 걸 깜빡" 제거 — 레시피 존재=ON, `/wook-plan`이 레시피 보장 |
| 2026-06-01 | **하네스 자기검증**(dogfood): `/wook-plan`으로 `.claude/evaluate.recipe`+`tools/selfcheck.py` 작성 | repo가 자기 무결성 검증. 게이트 통과/차단 둘 다 실증, `deploy --check`는 drift 시 exit 1로 개선 |
| 2026-06-02 | core-rules 4번째 규칙 추가(신규 구현 요청 시 `/wook-plan` 제안) | 매 프롬프트 주입되는 규칙으로 PGE Plan 단계를 자연 유도 — 게이트 default-ON(레시피 존재=ON)과 맞물림. (이후 merge에서 main '하네스 워크플로' 섹션에 흡수) |
| 2026-06-02 | `/wook-brainstorm` 신설(PGE 앞단 발산), plan과 별도 스킬로 분리 | plan=수렴(recipe), brainstorm=발산 — 본질이 달라 분리 가치 有. 크기/도메인별 분할은 호출 결정비용만 키워 회피(plan 내부 흡수) |
| 2026-06-02 | sub-agent를 PGE 너머 *읽기 전용 전문가 풀*로 확장하는 방향 합의 | "쓰기=메인 단일 스레드, 읽기/판정=sub-agent"(§0-3). evaluator가 1번 멤버, brainstorm fan-out이 응용. 대량 신설 대신 필요 시 1개씩(over-build 회피) |
| 2026-06-02 | #7 게이트 커밋 우회 구멍 메움(`verified_head` 추적) | 턴 안 커밋→stop이 테스트 0회로 통과하던 실제 우회로 차단. SessionStart hook 신설 대신 evaluate_gate.py 자체에서 해결(표면 최소화). 7/7 시나리오 테스트 통과 · → **대체됨**(2026-06-15 `verified_sig` 내용 시그니처) |
| 2026-06-02 | 스킬/에이전트 `description`에 **CSO 규칙** 적용(트리거 조건만, 워크플로 요약 제거) | superpowers 차용. description이 워크플로를 담으면 모델이 본문을 안 읽고 지름길 탐 → 트리거만 남겨 호출 신뢰성↑. 신규 스킬도 이 규칙 따름 |
| 2026-06-02 | 신규 skill/agent 추가는 보류(빌트인과 중복 회피) | 코드리뷰=`/code-review`·탐색=`Explore`·리서치=`/deep-research`로 이미 커버. 유일 공백은 디버깅 규율 스킬(선택). over-build 회피(core-rules #1) |
| 2026-06-09 | #9 재사용 카탈로그: **도메인별 2단계(매니페스트+실제소스), Skill.md 미사용** | Snowflake/Databricks 패턴. 포인터 hook(주입)+`/wook-index`(생성). 실제소스=상세라 안 낡음 |
| 2026-06-11 | main(재사용 카탈로그) ← 작업 브랜치 merge | 두 갈래(연구·brainstorm·게이트수정·CSO ↔ 재사용 카탈로그) 통합. core-rules 중복제거(우리 wook-plan 규칙을 main '하네스 워크플로' 섹션에 흡수), Brainstorm 섹션 #9→**#10** 재번호(재사용 카탈로그가 #9) |
| 2026-06-11 | #11 컨벤션 시스템(도메인별 코딩 규칙/스타일) — 재사용 카탈로그의 형제 | 프로젝트별 `.claude/conventions/<domain>.md`, 값은 소스 포인터(안 낡음). 형제 hook 2개(포인터 주입+스테일 검사) — main `check_reuse_pointers` 안 건드림. 게이트 강제는 기존 Stop 게이트 재사용. frontend 슬라이스부터(over-build 회피). test_conventions 6/6 PASS |
| 2026-06-11 | `/wook-conventions` = **bimodal**(greenfield 확정 / brownfield 추출) | 빈 프로젝트는 코딩 전 확정, 진행된 프로젝트는 도메인 코드만 훑어 초안+불일치 플래그 |
| 2026-06-11 | `/wook-conventions` 안내를 **도메인 중립으로 일반화** | 기계장치는 처음부터 도메인 무관이나 스킬 *예시*가 frontend 편향 → "도메인별 무엇을 담는지" 힌트표(front/back/db/infra/data/shared)로 교체, greenfield/brownfield·문서예시 다도메인화. `.frontend.example`은 예시 1개로 유지 |
| 2026-06-11 | #12 독립 평가자: **Playwright MCP + 도메인별 실제 평가 + 망각 제거 리마인더** | 본인 자기평가 ❌·딴 평가자가 화면 직접 봄. MCP는 LLM 평가자 층에만(셸 게이트는 브라우저 못 굴림). 평가자 allowlist에 `mcp__playwright__*`(빌트인 브라우저 배제), Iron law를 관찰사실까지 확장 |
| 2026-06-11 | 평가자 호출 트리거 = **본인 판단 + 결정론 리마인더**(강제 차단 X) | "사소 vs 비사소"는 기계 판단 부적합(1줄도 클 수 있음) → 본인 판단. 단 "큰 변경에도 까먹음" 해결 위해 코드변경 턴에 비차단 알림. frontend 슬라이스부터(over-build 회피) |
| 2026-06-11 | #13 프로젝트 지도 `.claude/project-map.md`(구조+스택+실행법, AI 자동유지) | 평가자가 "어떻게 띄우고 뭘 보나" 즉흥하던 빈 곳 메움. 형식=MD+YAML블록+ASCII tree(JSON 주석불가 ✗, 순수YAML 어색 ✗). **고정 섹션 스키마**(평가자가 어디 볼지 항상 앎) |
| 2026-06-11 | project-map 설계를 **독립 리뷰어(타 에이전트)로 평가** 후 개정 | 제안자(나) 자기평가=편향 → 독립 평가가 run: 신뢰성·env 누락·recipe 중복 등 6개 실약점 적시. smoke→recipe 연결, env/services 추가, run 출처포인터, verified 스탬프 반영 |
| 2026-06-11 | #14 `/wook-onboard` — 기존 repo 한 방 온보딩(오케스트레이터) | 진행중 프로젝트=`.claude` 텅 빔 → map+recipe+conventions+reuse-index 한 번에. 기존 3스킬 재사용+recipe derive만 신규. 제안→승인→작성(대량/게이트ON 가드), 멱등 |
| 2026-06-11 | 스킬 전수 **독립 감사**(타 에이전트) → 트리거 충돌·CSO 정리 | 죽은/중복 스킬 0(자를것·합칠것 없음). 단 `"onboard this repo"`가 map/conventions/onboard 3곳에 걸린 충돌 발견 → map·conventions·index에서 온보딩 트리거 제거(onboard가 유일 front door), plan/index/map description CSO 정리 |
| 2026-06-11 | build-log 무한성장 대책 = **계층화(C)** | 리서치 3각도 수렴: ADR supersede(status) + MemGPT식 아카이브(cold 이동, 삭제 X) + progressive disclosure(인덱스/최근만 읽기) + selfcheck 임계 트리거. B(풀 ADR 분할)는 우리 *서술+결정+스냅샷* 혼합엔 맥락 흩어지고 과설계 → C 채택 |
| 2026-06-11 | #15 멀티에이전트 = **deploy --target(v1)**, 디렉터리 재구조(v2) 보류 | 리서치: Codex가 hooks/skills/MCP를 Claude와 거의 동일 스키마로 미러 → 어댑터 얇음. 한 소스 읽어 도구별 렌더(스크립트 공유). v2 core/adapters 재구조는 cosmetic+위험↑라 보류. Codex 실동작은 머신 검증(컨테이너 불가) |
| 2026-06-11 | Codex 지식파일 = **`.codex/`**(deploy가 `.claude`→`.codex` 치환) | 초기 decision A('`.claude` 공유') → **폐기**. Codex 프로젝트에 `.claude/`가 생기는 건 틀림(형욱 지적). 모든 codex 배포 텍스트에 `.claude`→`.codex` 적용, 배포본에 `.claude` 0 확인 |
| 2026-06-11 | Windows(cp949) UnicodeDecodeError 수정 + selfcheck encoding 가드 | `read_text/write_text`가 로케일 기본 인코딩 써서 UTF-8 한글 소스 못 읽고 죽음. 모든 텍스트 I/O에 `encoding="utf-8"`, 가드가 누락 정적 차단(가드가 실제 1건 추가 적발) |
| 2026-06-15 | #7 게이트 트리거 = **코드 내용 시그니처(`code_sig`)**, `verified_head`/dirty-tree 폐기 | 형욱 피드백: 미커밋 코드가 남아 있으면 *사소한 질문에도* 매 턴 레시피 재실행. 트리거를 "dirty 여부"→"마지막 통과 이후 코드 내용이 실제로 바뀌었나"로. 질문·문서수정엔 스킵, 코드 변경 시만 실행. 커밋 우회는 여전히 차단(HEAD가 시그니처에 포함). test_gate 7/7(C2 스킵 실증) |
| 2026-06-15 | deploy `copy_tree` 실쓰기 버그 수정(`write_bytes()` 인자 누락) | codex 리팩터 때 들어간 버그: bytes 경로가 `writer()`를 인자 없이 호출해 *파일이 실제 변경될 때만* 크래시(–check는 안 써서 못 잡음). 라이브 게이트가 적발. 회귀 테스트 추가(copy_tree 양 경로 실쓰기) → codex_adapter 18/18 |

---

## 2. 만든 것 (hooks 바닥)

### ✅ #1 PostToolUse — 자동 포맷 (ruff)
- **목적:** `.py` 편집 직후 자동 포맷 → 스타일 준수를 모델 의지에 안 맡김(결정론).
- **파일:** `~/.claude/hooks/format_py.py` (stdin JSON 파싱 → `.py`면 `ruff format`, 항상 exit 0)
- **설정:** `~/.claude/settings.json` → `PostToolUse` / matcher `Edit|Write` / exec form
  (`python` + args) / timeout 30 / statusMessage "ruff format"
- **검증:** 파이프 테스트(실제 포맷 확인) → python으로 스키마 검증 → **실 세션 발화 증명**
  (Write로 `x=1+2` 생성 → hook이 `x = 1 + 2` 등으로 교정). ✅ live
- **안전:** ruff 없음/포맷 실패/잘못된 입력 → 전부 조용히 exit 0, 편집 절대 안 막음.

### ✅ #2 UserPromptSubmit — 망각 방지(core-rules 재주입)
- **목적:** 매 프롬프트마다 핵심 지침을 `additionalContext`로 주입 → 대화 길어져도 안 흐려짐.
- **파일:**
  - `~/.claude/harness/core-rules.md` — 주입할 **순수 규칙**(사실 진술체)
  - `~/.claude/harness/core-rules.README.md` — 작성 가이드(hook은 안 읽음)
  - `~/.claude/hooks/inject_core_rules.py` — 주석·H1 제거, 9000자 캡, 항상 exit 0
- **설정:** `settings.json` → `UserPromptSubmit`(matcher 미지원) / exec form / timeout 15
- **검증:** 파이프 테스트(주석제거·H1제거·본문포함·캡 PASS) → **실 세션 발화 증명**
  (다음 턴 system reminder에 규칙 주입 확인). ✅ live
- **현재 규칙(시드 3 + 「하네스 워크플로(기본값)」 섹션):**
  1. 요청 안 한 변경(대량 파일 생성·비요청 리팩터링·스코프 확장)을 선호하지 않음
  2. 테스트 실제 실행 없이 "완료"라 하는 걸 신뢰 안 함(완료=실행 결과로 증명)
  3. 불확실하면 추측 말고 멈추고 확인받기 선호
  - **하네스 워크플로(기본값)** 섹션 3줄: ① 중간+ 구현은 `/wook-plan`으로 시작(`.claude/plan.md` 없으면 코드 전 제안, 단순 수정/탐색/질문 제외) ② 새 코드 전 재사용 카탈로그(`.claude/reuse-index/`) 확인 ③ 새 재사용물 만들면 도메인 매니페스트에 한 줄 추가 (구 "규칙 4"는 merge 때 ①에 흡수)
- **편집법:** `core-rules.md` 고치면 다음 프롬프트부터 자동 반영(재시작 불필요).

### ✅ #3 PreToolUse — 보호 경로 가드(deny)
- **목적:** 절대 손대면 안 되는 파일(VCS 내부·자격증명·개인키)의 Edit/Write를 **실행 전 차단**.
  deny는 권한 모드로도 못 뚫는 하드 게이트.
- **파일:** `~/.claude/hooks/guard_paths.py` (PreToolUse JSON 파싱 → 보호 패턴이면
  `permissionDecision:"deny"` + 이유, 아니면 무출력 exit 0 = 정상 흐름)
- **설정:** `settings.json` → `PreToolUse` / matcher `Edit|Write` / exec form / timeout 15
- **기본 보호 목록(초보수적, 오탐 0):** `.git/` 세그먼트, `*credentials*.json` /
  `.credentials.json` / `secrets.json`, `*.pem` / `*.key` / `id_rsa` / `id_ed25519`
  - `.gitignore`·`.gitattributes`는 차단 안 함(세그먼트 검사). 일반 `.py` 등 정상 통과.
  - opt-in 주석: `.env`·lock 파일은 원하면 PROTECTED에서 주석 해제.
- **검증:** 파이프 테스트 6/6 PASS(오탐 케이스 포함) → **실 세션 차단 증명**
  (`server.pem` Write 시도 → deny로 막힘, 파일 생성 안 됨). ✅ live
- **스코프 메모:** 결정론 deny는 *구체적 패턴*에 적합. "안 시킨 리팩터링/대량 생성" 같은
  **의미 판단형 과잉행동은 여기서 안 다룬다**(오탐 폭발) → 판단 레이어(prompt/agent hook
  또는 PGE)에서 다룰 것.

---

## 2-B. 판단 루프 (PGE) — 시작: Evaluator v1

설계 §0-2/§8-B대로 **Evaluator 하나(컴퓨트 검증)부터.** "테스트 안 돌리고 됐다 함"을 정조준.

### 🟡 #5 Evaluator v1 — 온디맨드 `/wook-evaluate` (배포됨, 서브에이전트는 재시작 후 활성)
- **형태:** `/wook-evaluate`(skill, 진입점) → **독립 컨텍스트의 `wook-evaluator` 서브에이전트** 디스패치.
  코드 쓴 컨텍스트가 자기 코드를 칭찬 못 하도록 **평가자 분리**(§0-2).
- **파일:**
  - `~/.claude/agents/wook-evaluator.md` — 도구 Bash·Read·Grep·Glob(**Edit/Write 없음** = 판정만, 안 고침)
  - `~/.claude/skills/wook-evaluate/SKILL.md` — `/wook-evaluate` 진입점, 서브에이전트 디스패치 + 판정 정직 전달
- **레시피 구동:** 먼저 `.claude/evaluate.recipe`(프로젝트가 선언한 `name: 명령`)를 읽어 실행,
  없으면 자동탐지(python/node) 폴백. **판정은 실제 exit code에 묶음.** stack 하드코딩 안 함.
- **Iron law:** 실제 명령 실행 + exit 0을 본 것만 PASS. 테스트 못 찾으면 INCONCLUSIVE(거짓 PASS 금지).
- **검증:** 레시피를 실제 샘플에 돌려 증명 — 통과 코드 → exit 0 → **PASS**, 버그 주입 →
  exit 1 → **FAIL**(거짓 통과 불가). ✅ 레시피 동작
- **⚠️ 활성화:** 서브에이전트는 세션 시작 시 로드 → **재시작/새 세션부터 디스패치 가능**(스킬은 즉시 등록).
- **다음:** 백엔드/프론트/DB 레시피 추가(#6).

### ✅ #7 자동 게이트 — Stop hook (generate → 자동 evaluate 루프)
- **목적:** 형욱이 원한 핵심 — **수동 `/wook-evaluate` 아니라 harness가 알아서**. 턴이 끝날 때
  자동으로 테스트를 돌려 미통과면 "완료"를 막고 자동으로 계속 작업. (§0-4 반복 루프)
- **파일:** `~/.claude/hooks/evaluate_gate.py` (`type:"command"` Stop hook, exec form, timeout 300)
- **왜 command(스크립트)인가:** 매 턴 발동하니 **싸고 결정론적**이어야. LLM 안 씀. 판정은 실제
  exit code, 실패 시 테스트 출력 그대로 피드백. (깊은 분석은 `/wook-evaluate`의 LLM evaluator)
- **발동 조건(default-ON by 레시피):** ① **`.claude/evaluate.recipe` 존재**(있으면 게이트 ON,
  켜는 별도 단계 없음) ② **마지막 통과 이후 코드가 실제로 바뀜**(아래 ②-트리거) ③ `.claude/evaluate-off`
  없음. 아니면 즉시 통과(거의 공짜) → 일반 대화·계획·레시피 없는 repo엔 영향 0. **"켜는 걸 깜빡" 제거.**
- **②-트리거: 코드 내용 시그니처(`code_sig`)** (2026-06-15, `verified_head`/dirty-tree 폐기):
  - 문제(형욱): 트리거가 "워킹트리가 dirty한가"라, 미커밋 코드가 남아 있으면 **사소한 질문에도 매 턴
    레시피 재실행** → 보류·지연.
  - 수정: `code_sig` = HEAD + 변경/미추적 **코드 파일들의 현재 내용** 해시. *마지막으로 통과한 sig*와
    같으면 **스킵**(레시피 0회). 질문·문서수정엔 안 돎, **코드를 진짜 바꿨을 때만** 실행.
  - 커밋 우회(턴 안 커밋)는 여전히 차단(HEAD가 sig에 포함). 비-git은 항상 검증. 실패 시 sig 미기록 →
    재검사하되 attempt/stuck cap이 루프 한정. 검증: `tools/test_gate.py` 7/7(C2 = 통과 후 코드 불변 → 스킵 실증).
- **검증 레시피(유동적):** `.claude/evaluate.recipe`에 `name: 셸명령` 선언(어떤 stack/도메인이든) →
  게이트가 전부 실행, 미통과면 블로킹. 게이트는 레시피만 봄(무관 repo 안 건드림); 자동탐지 폴백은
  `/wook-evaluate`(온디맨드) 쪽. 템플릿: `~/.claude/harness/evaluate.recipe.example`
- **런어웨이·정체 가드(§0-4, 고도화):**
  - 실패마다 **정규화 시그니처**(숫자·타이밍 제거) 계산.
  - **같은 시그니처 3회 연속(stuck)** → 정체로 판단, 자동 루프 포기(systemMessage).
  - 시그니처 **바뀌면**(진행 중) stuck 리셋 → 더 인내하되 **총 5회(MAX) 상한**.
  - 새 stop(`stop_hook_active` false)이면 에피소드 리셋. Claude Code 내장 8-cap이 2차망.
- **견고성:** 테스트 러너는 `python -B`(stale `.pyc` 무시) → 방금 편집한 코드를 항상 소스에서 재읽음.
- **검증(시뮬레이션 Stop 이벤트):** 레시피 실패→block(실제 출력), 통과→allow, `evaluate-off`→allow(비활성),
  무레시피→allow, 같은실패 1→2→3회=stall give-up, 실패 바뀌면 진행 감지, 임의 셸 체크(api/db) 동작,
  `-B`로 즉시-교체도 정확. 전부 PASS. ✅ live
- **켜는 법:** `.claude/evaluate.recipe` 만들면 끝(보통 `/wook-plan`이 써줌). 끄기 = `.claude/evaluate-off`
  빈 파일. **이 harness repo는 레시피가 없어 게이트 발동 안 함.**

### ✅ #8 Planner — `/wook-plan` (PGE 삼각형 닫음)
- **목적:** 코드 전에 **"올바른 동작이 뭔지"를 실행 가능한 수용 기준으로 정의** → 그걸
  `.claude/evaluate.recipe`로 써서 Evaluator/게이트가 *정확히 그 기준*을 검증(§0-2).
- **차별점:** generic 플래닝(예: superpowers `writing-plans`)과 달리 **PGE 통합** —
  수용 기준 = 머신 체크 가능 형태 → 레시피로 박음. Plan이 기준 정의·기록까지.
- **파일:** `~/.claude/skills/wook-plan/SKILL.md` (`/wook-plan` 진입점)
- **흐름:** 모호하면 질문 → SPEC(범위/엣지/수용기준) 제시 → 기준을 `.claude/evaluate.recipe`로
  번역·제안 → 승인 → 레시피 + `.claude/plan.md` 기록 → **레시피 작성=게이트 자동 ON** → 구현은 통과까지.
- **PGE 완성:** Plan(기준 정의·레시피 작성) → Generate(구현) → Evaluate/게이트(그 레시피로 검증).
- **검증:** 배포·frontmatter 유효 확인. (스킬=프롬프트라 exit code 테스트 불가; 동작은 호출 시 발현)
- **활성화:** 다음 재시작부터 `/wook-plan` 호출 가능(스킬 목록 갱신 시 등록).

### ✅ #10 Brainstorm — `/wook-brainstorm` (PGE 앞단 발산)
- **목적:** plan이 *수렴*(수용기준→recipe)이라면, brainstorm은 *발산* — 문제/접근이 아직
  열린 단계에서 **옵션을 넓히고 트레이드오프를 드러낸다.** 코드·recipe 둘 다 만들지 않음
  (성급한 recipe = 틀린 기준 고착). 방향이 잡히면 `/wook-plan`으로 핸드오프.
- **파일:** `~/.claude/skills/wook-brainstorm/SKILL.md` (`/wook-brainstorm` 진입점)
- **흐름:** 문제 프레이밍(모호하면 질문) → 서로 다른 접근 2~4개(최소 1개는 의외의 것) →
  정직한 비교(축: 단순성·위험·노력·가역성·harness 적합) → 추천(단 결정은 개발자) → plan 핸드오프.
- **sub-agent 확장(형욱 직감 반영):** 발산 단계에서 **읽기 전용 sub-agent로 fan-out** 명시
  — Explore/general-purpose로 기존 코드베이스 매핑, research 에이전트로 외부 prior art.
  "쓰기는 메인 단일 스레드, 읽기/판정은 sub-agent"라는 안전 패턴(§0-3 LangChain)의 적용.
  evaluator(읽기·실행·판정, write 없음)에 이은 *읽기 전용 전문가 풀*의 두 번째 자리.
- **검증:** `python tools/selfcheck.py` exit 0(5 scripts compile, 4 md frontmatter ok —
  brainstorm 포함). `deploy --check`는 이 임시 컨테이너에 미배포라 drift exit 1(변경 무관).
- **활성화:** 다음 재시작부터 `/wook-brainstorm` 호출 가능.

---

## 2-C. 재사용 카탈로그 (reuse catalog)

설계: `docs/reuse-catalog-design.md`. AI가 전체 코드 안 읽고 **도메인별 짧은 인덱스**만 보고 기존
코드 재사용(중복 방지). Snowflake/Databricks "설명목록→관련것만 선택→상세" 패턴, Skill.md 형식엔 안 묶임.

### ✅ #9 재사용 카탈로그 — 포인터 hook + `/wook-index` (live, 검증됨)
- **구조(2단계):** Tier-1 = `.claude/reuse-index/<domain>.md`(항목당 `이름 · 한줄설명 · path:symbol`),
  도메인별 분리(프론트 짤 때 백/DB 안 들어옴). Tier-2 = **포인터가 가리키는 실제 소스**(상세 안 낡음).
- **파일:**
  - `~/.claude/hooks/inject_reuse_pointer.py` — UserPromptSubmit(2번째 핸들러). `.claude/reuse-index/`
    있으면 매 턴 **도메인 목록 포인터만** 주입(본문 아님), 없으면 무출력. "파일 존재=ON" 패턴.
  - `~/.claude/skills/wook-index/SKILL.md` — `/wook-index`: 코드 훑어 도메인별 매니페스트 생성/갱신(semi-auto).
- **동작:** (매 턴) 포인터로 도메인 인지 → AI가 작업 도메인 매니페스트 1개만 Read → 실제 소스 Read → 재사용.
- **검증(실제 실행):** 멀티도메인 샘플로 — 포인터 hook(있으면 도메인 주입/없으면 무출력) ✓,
  매니페스트 **6/6 포인터가 실제 코드로 해석** ✓, **스테일 포인터(없는 심볼) 탐지** ✓, 도메인 분리 ✓.
- **기본값화(완료):** `core-rules.md`에 "하네스 워크플로(기본값)" 추가 — 중간+ 구현은
  `/wook-plan`으로 시작, 새 코드 전 재사용 카탈로그 확인, **새 재사용물 만들면 카탈로그에 추가**.
  매 턴 주입 검증됨. 전역 CLAUDE.md는 중복이라 안 만듦(hook이 게이트·재사용은 이미 자동 강제).
- **카탈로그 유지보수 분담:** *추가*(판단+설명 필요)는 AI 기본값(core-rules), *스테일 탐지*(삭제된
  심볼=결정론)는 hook. `check_reuse_pointers.py`(Stop, 비차단): reuse-index 있고 코드 변경 시
  매니페스트 포인터 해석 검사 → 스테일이면 "/wook-index로 갱신" **알림만**(완료 안 막음).
  검증: 정상→무알림, 스테일(없는 심볼)→알림, reuse-index 없으면 무알림. ✅

---

## 2-D. 코딩 컨벤션 (conventions)

설계: `.claude/plan.md`(2번째 SPEC). 재사용 카탈로그의 **형제** — "뭘 재사용?"이 아니라
"어떤 규칙/스타일로?". 도메인별 컨벤션(테마·색·네이밍·API 형태…)을 AI가 항상 참고/유지.
같은 "파일 존재=ON" + "AI 판단 / hook 결정론" 분담 패턴. **frontend 슬라이스부터** 빌드.

### ✅ #11 컨벤션 시스템 — 포인터 hook + 스테일검사 + `/wook-conventions` (검증됨, frontend 슬라이스)
- **구조:** `.claude/conventions/<domain>.md` — 규칙(판단)은 prose, **값은 실제 소스(`path:symbol`)
  포인터로**(복제 X = 안 낡음). 수직(frontend/backend/db/infra/data)은 도메인별, 횡단(`shared.md`:
  테스트·보안·로깅/에러·git)은 "항상" 적용.
- **파일:**
  - `~/.claude/hooks/inject_convention_pointer.py` — UserPromptSubmit(3번째). conventions 있으면
    매 턴 "shared 항상 + 도메인별 읽어라" 포인터만 주입, 없으면 무출력. (reuse 포인터의 형제)
  - `~/.claude/hooks/check_convention_pointers.py` — Stop(비차단, 형제). 코드 변경 시 컨벤션
    포인터(`path:symbol`) 해석 검사 → 스테일이면 "갱신/`/wook-conventions`" **알림만**.
  - `~/.claude/skills/wook-conventions/SKILL.md` — `/wook-conventions` **bimodal**: greenfield=질문하며
    확정(코딩 전), brownfield=도메인 코드만 훑어 초안+불일치 플래그. 기계검증 규칙은 recipe에 제안.
  - `~/.claude/harness/conventions.frontend.example` — frontend 컨벤션 템플릿(예시).
- **게이트 강제:** 기계검증 가능 규칙(예: raw-hex 금지)은 프로젝트 `evaluate.recipe`에 체크로 박힘
  → **기존 Stop 게이트가 강제**(새 강제 장치 X, 재사용). 문서엔 `[강제: <체크>]` 표기로 문서↔게이트 동기화.
- **유지보수:** *추가/변경/폐기*(판단)=AI 기본값(core-rules에 1줄 추가), *스테일 탐지*(결정론)=hook.
  재사용 카탈로그와 1:1 대칭.
- **검증(실제 실행, `tools/test_conventions.py` **6/6 PASS**):** ① 포인터 hook(있으면 shared+도메인
  주입/없으면 무출력) ② 스테일 탐지(없는 심볼→알림, 유효→무알림) ③ **게이트 강제 데모**(샘플 recipe의
  raw-hex 체크 위반→block, 준수→allow). selfcheck exit 0(9 scripts, 6 frontmatter).
- **OUT(나중 복제):** backend/db/infra/data/shared 실제 컨벤션 파일, 실제 stylelint 설치(프로젝트 책임).
  기계장치는 1회로 끝 — 이후 도메인 추가 = `conventions/<domain>.md` + recipe 한 줄.
- **참고:** `test_conventions.py`는 STATE_DIR을 정리해 repo 게이트와 충돌 가능 → recipe엔 안 넣고 빌드 중 수동 실행.

---

## 2-E. 독립 평가자 — 도메인별 실제 평가 (Playwright MCP)

문제: **본인이 자기 코드 평가 ❌**, 딴 평가자가 객관 평가해야 하는데 — 화면을 볼 수 있는 평가는
LLM 평가자(서브에이전트)만 가능(결정론 셸 게이트는 브라우저 못 굴림). 게다가 그 평가자는 *본인이
부를지 선택*이라 큰 변경에도 자주 까먹음. → "도메인 맞는 실제 평가 + 망각 제거".

### ✅ #12 독립 평가자 강화 — Playwright MCP + 도메인별 평가 + 리마인더 (frontend 슬라이스)
- **도구:** `wook-evaluator` allowlist에 `mcp__playwright__*` 추가, **빌트인 브라우저/WebFetch 제외**
  (MCP만 강제). Edit/Write 제외 유지. (서브에이전트 `tools:` allowlist·MCP 와일드카드 문법은
  `claude-code-guide`로 공식 확인 — 추측 안 함.)
- **평가자 지시:** Iron law를 "exit 0 **또는 실제 관찰 사실**(렌더된 텍스트·응답 바디·콘솔 0에러)"로
  확장 + **"도메인별 평가 방식"** 절(frontend=Playwright MCP 화면검증, backend=엔드포인트 호출,
  db=쿼리, data=파이프라인, infra=plan). 도구/앱/MCP 없으면 **INCONCLUSIVE**(거짓 PASS 금지).
- **망각 제거:** `~/.claude/hooks/remind_evaluator.py`(Stop, 비차단) — `.claude` 있는 프로젝트에서
  코드 변경 턴이면 "사소하지 않으면 독립 평가자 호출" 알림(프론트 변경=Playwright 힌트).
  **사소 판단은 본인 몫**(기계 강제 X), 시스템은 망각만 막음.
- **표준 규칙:** core-rules에 "비사소 변경 → 본인이 평가 말고 독립 평가자, 도메인 맞는 검증" 1줄.
- **두 층 상보:** 결정론 게이트(셸 green=바닥) + 독립 평가자(도메인 맞는 실제 검증=깊이). MCP는
  LLM 평가자 층에만(게이트는 셸 유지).
- **검증(`tools/test_evaluator.py` 6/6 PASS):** 리마인더(프론트→알림+Playwright / 백→알림 /
  변경없음·`.claude`없음→무출력), 평가자 tools에 Playwright MCP 있고 Edit/Write/WebFetch 없음.
  selfcheck exit 0(10 scripts). **한계: 실제 Playwright 화면검증은 MCP·브라우저·앱 필요 → 배포 후 라이브 시험으로만 검증(정직히 표시).**
- **OUT:** backend/db/infra 실제 평가 자동화, Playwright MCP 서버 설치(프로젝트 책임), 강제 차단(지금은 넛지만).

---

## 2-F. 프로젝트 지도 (project map)

평가자(#12)가 "어떻게 띄우고 뭘 보나"를 즉흥으로 알아내던 빈 곳을 메움. AI가 지속 유지하는
살아있는 **구조+스택+실행법** 문서 `.claude/project-map.md`. 평가자가 이걸 읽어 앱을 띄우고 굴림.

### ✅ #13 프로젝트 지도 — 고정 스키마 + `/wook-map` (검증됨)
- **형식 결정:** MD 그릇 + YAML 블록(실행정보, 파싱 가능) + ASCII tree(구조) + 산문(How to exercise).
  JSON ✗(주석 불가), 순수 YAML ✗(tree·산문 어색). 주 독자가 LLM이라 MD가 최적.
- **고정 스키마(모든 프로젝트 동일):** 섹션 4개·순서 `Stack & Run`/`Structure`/`How to exercise`/
  `Entry points`(영어 앵커) + YAML 키 `stack,env,services,run.<d>.{install,dev,url,test,build}`.
- **독립 리뷰(타 에이전트) 반영 6:** ① smoke는 `evaluate.recipe`에 묶고 지도는 가리킴(중복/드리프트 제거)
  ② `env`(필수 변수=자체부팅 최대 누락) ③ run 명령에 `# 출처` 포인터(요약+가리킴, 캐시임을 명시)
  ④ services/포트 ⑤ `verified: 날짜@sha` 스탬프(스테일 가시화) ⑥ 테스트 로그인 / Structure ≤2레벨.
- **파일:** `~/.claude/harness/project-map.example`(템플릿), `~/.claude/skills/wook-map/SKILL.md`
  (`/wook-map`: 코드 훑어 스키마대로 작성, run은 package.json/pyproject/compose에서 derive+출처).
- **연결:** core-rules 1줄(지도 있으면 실행·평가 시 따르고, 구조/스택/실행 바뀌면 갱신).
  `wook-evaluator`가 "굴리기 전 project-map 읽어라"로 즉흥 제거.
- **기존과 경계:** recipe=돌릴 체크(exit code) / conventions=코드 스타일 / **map=구조·실행법(지도)**.
  How to exercise는 recipe를 *가리킴*(복제 X) — 리뷰가 짚은 최대 중복 위험 차단.
- **검증(`tools/test_project_map.py` 11/11 PASS):** 고정 4섹션·순서, YAML 키(stack/env/services/run),
  run에 `#` 출처 포인터, verified 스탬프, recipe 연결, PyYAML 파싱. selfcheck exit 0(7 frontmatter).
- **OUT:** project-map 포인터 스테일 hook(Entry points 소수→v1 제외), 새 inject hook(주입 4번째 회피),
  run 명령 자동검증(셸로 결정론 검증 불가 — 출처 포인터로 완화).

---

## 2-G. 온보딩 (기존 repo 한 방 설정)

진행 중 프로젝트엔 `.claude/`가 텅 비어 harness가 하나도 안 켜짐 → 코드+문서 훑어 세트를 한 번에 생성.

### ✅ #14 `/wook-onboard` — 기존 repo 온보딩 (오케스트레이터)
- **하는 일:** 네 개를 순서대로 생성 — ① `project-map.md`(=wook-map, 토대) → ② `evaluate.recipe`
  (map의 run.test/lint/build에서 **베이스라인 derive** = 유일 신규 로직) → ③ `conventions/<domain>.md`
  (=wook-conventions brownfield) → ④ `reuse-index/<domain>.md`(=wook-index).
- **거의 오케스트레이터:** 기존 3스킬 스키마를 *재사용*(재구현 X). 통째 스캔은 읽기전용 → 읽기전용
  sub-agent fan-out 허용(서로 다른 파일=충돌 없음, 쓰기는 Step3에서 본인이).
- **가드:** **제안→승인→작성**(대량+recipe가 게이트 ON → 자동 대량작성 ✗), 멱등(기존 파일 갱신/스킵, 안 덮음).
- **파일:** `~/.claude/skills/wook-onboard/SKILL.md`. 빌트인 `/init`(CLAUDE.md)과 별개(보완).
- **검증:** selfcheck exit 0(frontmatter). 오케스트레이터=프롬프트라 동작은 라이브 호출로 검증(스킬 공통).

---

## 2-H. 멀티 에이전트 — Codex 어댑터 (v1)

리서치 결과 Codex가 hooks/skills/MCP를 **Claude와 거의 동일 스키마로 미러**(hooks GA v0.124.0) → 어댑터가
얇음. "한 소스 + 도구별 배포"로 확장(디렉터리 재구조 없이 v1).

### ✅ #15 `deploy.py --target=claude|codex` — Codex 지원 (v1)
- **접근:** `claude/` 한 소스를 읽어 도구별 렌더. claude=`~/.claude`(settings.json hooks)·codex=`~/.codex`.
  hook **스크립트는 공유**(stdin JSON 스키마 동일) — 다른 건 *등록 파일/규칙파일/평가자 래퍼*뿐.
- **Codex 렌더(순수 함수, 테스트 가능):**
  - `hooks.json` ← settings.hooks.json 변환(편집 matcher에 `apply_patch` 추가, command=단일 문자열)
  - `AGENTS.md` ← core-rules(항상 로드=망각방지 등가). `agents/wook-evaluator.toml` ← 평가자(.md→.toml, sandbox read-only + Playwright MCP)
  - hooks/skills/harness는 그대로 복사(SKILL.md 컨벤션 동일).
- **필드명 관용:** hook 스크립트가 `tool_input.file_path`(Claude)·`path`(Codex) 둘 다 읽음(guard_paths·format_py).
- **결정(승인):** A **지식파일 도구별**(`.claude`↔`.codex`, deploy가 `.claude`→`.codex` 치환) · B core-rules→AGENTS.md · C 평가자=custom agent `.toml` · v1=deploy --target(재구조 X, v2 보류). *(초기 'A: `.claude` 공유'는 오류 — Codex 프로젝트에 `.claude/`가 생기는 건 틀림. 형욱 지적으로 정정.)*
- **`.claude`→`.codex` 치환:** codex 배포 시 복사/렌더되는 모든 텍스트에 적용 — hook 스크립트(프로젝트 `.codex/conventions`·글로벌 `~/.codex/cache`)·skills·AGENTS.md·evaluator.toml. `.claude`(점)는 우리 파일에서 항상 디렉터리라 안전(제품명 "Claude Code"는 점 없음). 검증: 배포된 `~/.codex`에 `.claude` 흔적 0.
- **검증(`tools/test_codex_adapter.py` 12/12):** 변환 hooks.json 유효·4이벤트·apply_patch·스크립트 보존,
  AGENTS.md H1제거+규칙, evaluator.toml tomllib 파싱, 필드 관용(file_path/path). 회귀 6/6·6/6·11/11, selfcheck exit 0.
  실제 렌더 확인(~/.codex/{hooks.json,AGENTS.md,agents/wook-evaluator.toml}).
- **⚠️ 한계(정직):** Codex `apply_patch` hook 실발동·정확한 command/agent.toml 스키마는 **이 컨테이너서 검증 불가**
  → 형욱님 머신(Codex 설치)에서 테스트해야 함. OpenAI 문서 403로 일부 스니펫 검증.
- **OUT:** core/adapters 디렉터리 재구조(v2) · 지식파일 중립화 · `codex exec` 강격리 평가자.

---

## 3. 파일 인벤토리 (`~/.claude`)

```
~/.claude/
├─ settings.json                     # hooks 등록(PreToolUse, PostToolUse, UserPromptSubmit, Stop)
├─ hooks/
│  ├─ guard_paths.py                  # #3 보호 경로 가드(deny)
│  ├─ format_py.py                    # #1 자동 포맷
│  ├─ inject_core_rules.py            # #2 망각 방지 주입
│  ├─ inject_reuse_pointer.py         # #9 재사용 카탈로그 포인터
│  ├─ inject_convention_pointer.py    # #11 컨벤션 포인터
│  ├─ evaluate_gate.py                # #7 자동 게이트(Stop hook)
│  ├─ check_reuse_pointers.py         # #9 스테일 포인터 알림(Stop hook, 비차단)
│  ├─ check_convention_pointers.py    # #11 컨벤션 스테일 알림(Stop hook, 비차단)
│  └─ remind_evaluator.py             # #12 독립 평가자 리마인더(Stop hook, 비차단)
├─ harness/
│  ├─ core-rules.md                   # 주입되는 규칙(편집 대상)
│  ├─ core-rules.README.md            # 규칙 작성 가이드
│  ├─ evaluate.recipe.example         # 검증 레시피 템플릿(프로젝트로 복사)
│  ├─ conventions.frontend.example    # #11 frontend 컨벤션 템플릿
│  └─ project-map.example             # #13 프로젝트 지도 템플릿(고정 스키마)
├─ agents/
│  └─ wook-evaluator.md               # #5 독립 Evaluator 서브에이전트
└─ skills/
   ├─ wook-evaluate/SKILL.md          # /wook-evaluate 진입점
   ├─ wook-plan/SKILL.md              # #8 /wook-plan (Planner)
   ├─ wook-brainstorm/SKILL.md        # #10 /wook-brainstorm (발산, PGE 앞단)
   ├─ wook-index/SKILL.md             # #9 /wook-index (재사용 카탈로그 생성)
   ├─ wook-conventions/SKILL.md       # #11 /wook-conventions (컨벤션 생성, bimodal)
   ├─ wook-map/SKILL.md               # #13 /wook-map (프로젝트 지도 생성)
   └─ wook-onboard/SKILL.md           # #14 /wook-onboard (기존 repo 한 방 온보딩)
```

---

## 4. git repo & 배포 구조

**구조 결정:** `~/.claude`를 직접 git하지 않는다(비밀 잔뜩). 대신 **이 프로젝트 repo가
source of truth**이고, 산출물을 `~/.claude`로 *배포*한다. repo 폴더엔 비밀이 0이라
`.gitignore` 실수해도 샐 게 없다(구조적 안전).

```
my-claude-harness/                  # git repo (비밀 0, 단순 blacklist .gitignore)
├─ README.md                        # 사용법(최초 설정/계속 사용/원리)
├─ CLAUDE.md                        # 이 repo 작업 시 컨벤션(build-log 갱신 등)
├─ docs/{claude-harness-design, build-log}.md
├─ claude/                          # ~/.claude 산출물의 source of truth
│  ├─ hooks/{guard_paths, format_py, inject_core_rules, inject_reuse_pointer, inject_convention_pointer, evaluate_gate, check_reuse_pointers, check_convention_pointers, remind_evaluator}.py
│  ├─ harness/{core-rules.md, core-rules.README.md, evaluate.recipe.example, conventions.frontend.example, project-map.example}
│  ├─ agents/wook-evaluator.md       # #5 Evaluator 서브에이전트
│  ├─ skills/{wook-evaluate, wook-plan, wook-brainstorm, wook-index, wook-conventions, wook-map, wook-onboard}/SKILL.md  # 진입점
│  └─ settings.hooks.json           # 우리가 소유한 hooks 블록({HOOKS_DIR} placeholder)
├─ deploy.py                        # claude/ -> ~/.claude 배포 (--check drift시 exit 1)
├─ tools/{selfcheck.py, test_gate.py, test_conventions.py, test_evaluator.py, test_project_map.py, test_codex_adapter.py}  # 자기검증 + #7·#11~#13·#15 테스트
├─ deploy.py                        # claude/ → ~/.claude|~/.codex 멱등 배포 (--target)
├─ .claude/{evaluate.recipe, plan.md}  # 이 repo 자신의 게이트 설정(자기검증 ON)
└─ .gitignore
```

**배포(`deploy.py`):**
- `claude/{hooks,harness,agents,skills}/**` → `~/.claude/`로 (중첩 구조 보존) 복사
- `settings.hooks.json`의 `{HOOKS_DIR}`를 **현재 머신의 실제 경로**로 치환 → `hooks` 키만
  `~/.claude/settings.json`에 병합(다른 키 보존). → **다른 PC에서 clone해도 경로 자동 정확.**
- **멱등**: `python deploy.py` 반복해도 동일. `python deploy.py --check`는 dry-run(미기록).
- 검증: dry-run·배포·재확인 모두 `up-to-date`, settings.json 무변경(클로버 없음).

**새 환경 복원:** clone → `python deploy.py` → `~/.claude`에 harness 깔림.

> 원격: https://github.com/sleepy-wook/my-claude-harness (**public** — repo에 비밀 0이라
> 구조적으로 안전, 설계 §7 공개 포트폴리오와 부합). 일상 동기화: `git pull` / `git push`.

## 5. 다음 스텝 (설계 §8)

**A. 결정론 바닥 (hooks) — 진행 중**
- [x] #1 PostToolUse 자동 포맷
- [x] #2 UserPromptSubmit 망각 방지
- [x] git repo 구조 확립(별도 클린 repo + `deploy.py` 배포) + 로컬 첫 커밋
- [x] public 원격 연결 + push → https://github.com/sleepy-wook/my-claude-harness
- [x] #3 PreToolUse 보호 경로 가드(deny) — 구체적 패턴만 차단(오탐 0)
- [ ] (#3 확장 후보) 위험 bash 명령 가드(`rm -rf`, `git push --force` 등) — 의논
- [ ] (#3 의미형) "안 시킨 행동" 판단 차단 — 판단 레이어(PGE)에서, 결정론 deny ✗

> **step A(결정론 바닥) 사실상 완료.** 다음은 B(판단 루프/PGE) — 형욱과 의논하며.

**B. 판단 루프 (PGE) — 진행 중, 형욱과 의논하며**
- [x] #5 Evaluator v1 (온디맨드 `/wook-evaluate`, 일반코드 레시피) — 레시피 검증됨, 재시작 후 서브에이전트 활성
- [x] #7 자동 게이트(Stop hook, opt-in 마커, 테스트만, 재시도 3회) — 시뮬레이션 4종 검증, live
- [x] #6 도메인 레시피 = **유동적 레시피 구동**(`.claude/evaluate.recipe`, 하드코딩 ✗) — 어떤 stack/도메인이든 선언으로 갈아끼움. 실제 프로젝트에서 레시피 채우며 검증 예정
- [x] #7-확장 정체 감지(시그니처 stuck/progress) + 게이트 설정화(tests/lint/build) + `-B` 견고성
- [x] #8 Planner `/wook-plan` — 수용 기준→`.claude/evaluate.recipe`로 박아 PGE 삼각형 닫음

> **PGE 루프 1차 완성**: Plan(`/wook-plan`, 기준 정의·레시피 작성) → Generate(구현) →
> Evaluate(`/wook-evaluate` + Stop 게이트, 레시피로 검증). 전부 유동적 레시피로 연결됨.
> 이후 고도화(정체 감지 튜닝, Planner 서브에이전트화 등)는 실전 쓰며 형욱과 조정.
