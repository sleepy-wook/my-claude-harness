# claude-harness — 빌드 기록 (build log)

> 설계 명세는 `claude-harness-design.md`(= source of truth). 이 문서는 **실제로 무엇을
> 만들었는지** 추적하는 살아있는 기록이다. 스텝마다 갱신한다.
>
> 최종 갱신: 2026-05-31

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
| 2026-05-31 | 첫 Evaluator = **온디맨드 `/evaluate`**(일반코드 레시피부터) | Anthropic "Evaluator 하나부터", 위험 낮음, 신뢰 쌓이면 하드게이트 승격 |

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
- **현재 규칙(시드 3):**
  1. 요청 안 한 변경(대량 파일 생성·비요청 리팩터링·스코프 확장)을 선호하지 않음
  2. 테스트 실제 실행 없이 "완료"라 하는 걸 신뢰 안 함(완료=실행 결과로 증명)
  3. 불확실하면 추측 말고 멈추고 확인받기 선호
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

### 🟡 #5 Evaluator v1 — 온디맨드 `/evaluate` (배포됨, 서브에이전트는 재시작 후 활성)
- **형태:** `/evaluate`(skill, 진입점) → **독립 컨텍스트의 `evaluator` 서브에이전트** 디스패치.
  코드 쓴 컨텍스트가 자기 코드를 칭찬 못 하도록 **평가자 분리**(§0-2).
- **파일:**
  - `~/.claude/agents/evaluator.md` — 도구 Bash·Read·Grep·Glob(**Edit/Write 없음** = 판정만, 안 고침)
  - `~/.claude/skills/evaluate/SKILL.md` — `/evaluate` 진입점, 서브에이전트 디스패치 + 판정 정직 전달
- **레시피(일반코드, 자동탐지):** Python(pytest 있으면 사용, 없으면 `python -m unittest`) +
  `ruff check`; Node(package.json의 test/lint/build 스크립트). **판정은 실제 exit code에 묶음.**
- **Iron law:** 실제 명령 실행 + exit 0을 본 것만 PASS. 테스트 못 찾으면 INCONCLUSIVE(거짓 PASS 금지).
- **검증:** 레시피를 실제 샘플에 돌려 증명 — 통과 코드 → exit 0 → **PASS**, 버그 주입 →
  exit 1 → **FAIL**(거짓 통과 불가). ✅ 레시피 동작
- **⚠️ 활성화:** 서브에이전트는 세션 시작 시 로드 → **재시작/새 세션부터 디스패치 가능**(스킬은 즉시 등록).
- **다음:** 백엔드/프론트/DB 레시피 추가, 그 뒤 하드게이트(Stop hook)나 `/goal` 승격은 의논.

---

## 3. 파일 인벤토리 (`~/.claude`)

```
~/.claude/
├─ settings.json                     # hooks 등록(PreToolUse, PostToolUse, UserPromptSubmit)
├─ hooks/
│  ├─ guard_paths.py                  # #3 보호 경로 가드(deny)
│  ├─ format_py.py                    # #1 자동 포맷
│  └─ inject_core_rules.py            # #2 망각 방지 주입
├─ harness/
│  ├─ core-rules.md                   # 주입되는 규칙(편집 대상)
│  └─ core-rules.README.md            # 규칙 작성 가이드
├─ agents/
│  └─ evaluator.md                    # #5 독립 Evaluator 서브에이전트
└─ skills/
   └─ evaluate/SKILL.md               # /evaluate 진입점
```

---

## 4. git repo & 배포 구조

**구조 결정:** `~/.claude`를 직접 git하지 않는다(비밀 잔뜩). 대신 **이 프로젝트 repo가
source of truth**이고, 산출물을 `~/.claude`로 *배포*한다. repo 폴더엔 비밀이 0이라
`.gitignore` 실수해도 샐 게 없다(구조적 안전).

```
my-claude-harness/                  # git repo (비밀 0, 단순 blacklist .gitignore)
├─ CLAUDE.md                        # 이 repo 작업 시 컨벤션(build-log 갱신 등)
├─ docs/{claude-harness-design, build-log}.md
├─ claude/                          # ~/.claude 산출물의 source of truth
│  ├─ hooks/{guard_paths, format_py, inject_core_rules}.py
│  ├─ harness/{core-rules.md, core-rules.README.md}
│  ├─ agents/evaluator.md            # #5 Evaluator 서브에이전트
│  ├─ skills/evaluate/SKILL.md       # /evaluate 진입점
│  └─ settings.hooks.json           # 우리가 소유한 hooks 블록({HOOKS_DIR} placeholder)
├─ deploy.py                        # claude/ -> ~/.claude 복사 + settings.json hooks 병합
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
- [x] #5 Evaluator v1 (온디맨드 `/evaluate`, 일반코드 레시피) — 레시피 검증됨, 재시작 후 서브에이전트 활성
- [ ] #6 도메인별 레시피 확장(백엔드 API / 프론트 브라우저 / DB 쿼리) — 의논
- [ ] #7 반복 루프 안전장치(최대 횟수·정체 감지·하드 게이트 or `/goal`) — 의논
- [ ] #8 Planner / 풀 PGE (모델 강하면 단순 유지도 선택지)

> 5~8은 확정 설계 아님. 형욱의 실제 작업 환경 물어보고 맞춰 정한다.
