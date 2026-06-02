# claude-harness — 빌드 기록 (build log)

> 설계 명세는 `claude-harness-design.md`(= source of truth). 이 문서는 **실제로 무엇을
> 만들었는지** 추적하는 살아있는 기록이다. 스텝마다 갱신한다.
>
> 최종 갱신: 2026-06-01

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

| 날짜 | 결정 | 근거 |
|------|------|------|
| 2026-05-31 | hook JSON 파싱 = **Python stdlib** | jq 미설치, Windows에서 가장 안정, 추가 설치 0 |
| 2026-05-31 | 첫 hook 적용 범위 = **Global `~/.claude`** | 설계 §2 "어느 환경에서든 동일" |
| 2026-05-31 | 포매터 = **ruff(.py)부터**, 확장 가능 구조 | 이미 설치됨, 즉시 동작 |
| 2026-05-31 | core-rules 시드 3개 확정(과잉행동·테스트·추측) | 형욱 확인("정확해") |
| 2026-05-31 | git = **별도 깨끗한 repo + 배포** (`~/.claude` 직접 git ✗) | repo에 비밀 0 → 구조적 안전, §7 공개 대비, docs+코드 한 곳 |
| 2026-05-31 | 작업 도메인 = **4개 전부**(일반코드·백엔드·프론트·DB) | Evaluator는 N개 ✗ → 하나 + 도메인별 레시피(§0-3) |
| 2026-05-31 | 첫 Evaluator = **온디맨드 `/wook-evaluate`**(일반코드 레시피부터) | Anthropic "Evaluator 하나부터", 위험 낮음, 신뢰 쌓이면 하드게이트 승격 |
| 2026-05-31 | 자동화 = **Stop hook 게이트**(opt-in 마커, 테스트만, 재시도 3회) | 형욱 진짜 목표="알아서 호출". command형(싸고 결정론)·마커로 침습성 제어 |
| 2026-06-01 | 게이트 고도화: **정체(시그니처) 감지 + 게이트 설정화 + `-B`** | 단순 N회 대신 진행/정체 구분(§0-4), 마커로 tests/lint/build 선택 |
| 2026-06-01 | 검증 **레시피 구동**(`.claude/evaluate.recipe`, 폴백 자동탐지) | stack 하드코딩 ✗ → 프로젝트가 `name: 명령` 선언, 갈아끼움(§0-3). #6을 N개 레시피 대신 한 메커니즘으로 |
| 2026-06-01 | #8 Planner = **skill `/wook-plan`**(수용 기준→레시피로 박음) | PGE 통합(generic 플래닝과 차별). 서브에이전트화는 나중 |
| 2026-06-01 | 커스텀 스킬/에이전트 **`wook-` 접두사**(`/wook-plan`·`/wook-evaluate`·`wook-evaluator`) | 네이티브 plan 모드·플러그인과 충돌/혼동 제거(형욱 닉네임 네임스페이스) |
| 2026-06-01 | 게이트 **default-ON by 레시피**(opt-in 마커 폐지, off=`.claude/evaluate-off`) | "켜는 걸 깜빡" 제거 — 레시피 존재=ON, `/wook-plan`이 레시피 보장 |
| 2026-06-01 | **하네스 자기검증**(dogfood): `/wook-plan`으로 `.claude/evaluate.recipe`+`tools/selfcheck.py` 작성 | repo가 자기 무결성 검증. 게이트 통과/차단 둘 다 실증, `deploy --check`는 drift 시 exit 1로 개선 |
| 2026-06-02 | core-rules 4번째 규칙 추가(신규 구현 요청 시 `/wook-plan` 제안) | 매 프롬프트 주입되는 규칙으로 PGE Plan 단계를 자연 유도 — 게이트 default-ON(레시피 존재=ON)과 맞물림 |

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
- **현재 규칙(4개):**
  1. 요청 안 한 변경(대량 파일 생성·비요청 리팩터링·스코프 확장)을 선호하지 않음
  2. 테스트 실제 실행 없이 "완료"라 하는 걸 신뢰 안 함(완료=실행 결과로 증명)
  3. 불확실하면 추측 말고 멈추고 확인받기 선호
  4. 새 기능/모듈/프로젝트 구현 요청 + `.claude/plan.md` 없으면, 코드 작성 전 `/wook-plan` 호출 제안(단순 수정/탐색/질문 제외) — PGE의 Plan 단계로 자연 유도
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
  켜는 별도 단계 없음) ② **코드 변경**(git status) ③ `.claude/evaluate-off` 없음. 아니면 즉시 통과
  (거의 공짜) → 일반 대화·계획·레시피 없는 repo엔 영향 0. **"켜는 걸 깜빡" 시나리오 제거.**
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

---

## 3. 파일 인벤토리 (`~/.claude`)

```
~/.claude/
├─ settings.json                     # hooks 등록(PreToolUse, PostToolUse, UserPromptSubmit, Stop)
├─ hooks/
│  ├─ guard_paths.py                  # #3 보호 경로 가드(deny)
│  ├─ format_py.py                    # #1 자동 포맷
│  ├─ inject_core_rules.py            # #2 망각 방지 주입
│  └─ evaluate_gate.py                # #7 자동 게이트(Stop hook)
├─ harness/
│  ├─ core-rules.md                   # 주입되는 규칙(편집 대상)
│  ├─ core-rules.README.md            # 규칙 작성 가이드
│  └─ evaluate.recipe.example         # 검증 레시피 템플릿(프로젝트로 복사)
├─ agents/
│  └─ wook-evaluator.md               # #5 독립 Evaluator 서브에이전트
└─ skills/
   ├─ evaluate/SKILL.md               # /wook-evaluate 진입점
   └─ plan/SKILL.md                   # #8 /wook-plan (Planner)
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
│  ├─ hooks/{guard_paths, format_py, inject_core_rules, evaluate_gate}.py
│  ├─ harness/{core-rules.md, core-rules.README.md, evaluate.recipe.example}
│  ├─ agents/wook-evaluator.md       # #5 Evaluator 서브에이전트
│  ├─ skills/{wook-evaluate, wook-plan}/SKILL.md  # 진입점
│  └─ settings.hooks.json           # 우리가 소유한 hooks 블록({HOOKS_DIR} placeholder)
├─ deploy.py                        # claude/ -> ~/.claude 배포 (--check drift시 exit 1)
├─ tools/selfcheck.py               # repo 자기검증(컴파일·settings·frontmatter·비밀)
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
