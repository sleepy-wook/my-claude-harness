# claude-harness — 설계 명세

> 나만의 Claude Code 스킬 + agent 구조.
> 이 문서는 Claude Code에서 실제 구현을 이어가기 위한 설계 명세다.

---

## ⚠️ STOP — 코드를 짜기 전에 반드시 먼저 할 것 (필독)

**이 문서가 다루는 기능들(hooks, `/goal`, settings 스키마)은 2026년에 빠르게 바뀌었고,
일부는 아주 최근(예: `/goal`은 2026년 5월, Claude Code v2.1.139)에 나왔다.
너의 학습 데이터에 없거나 틀린 내용일 가능성이 높다. 기억에 의존하지 말 것.**

아래를 **전부** 마치기 전에는 한 줄의 코드도 작성하지 마라:

1. **현재 Claude Code 버전 확인.** `claude --version`으로 버전을 확인하고,
   이 문서가 가정하는 기능(`/goal`은 v2.1.139+, `defer`는 v2.1.89+,
   `terminalSequence`는 v2.1.141+)이 실제로 가용한지 점검한다.

2. **공식 문서를 직접 읽고 검증한다.** 아래 페이지를 실제로 열어 확인한다
   (부록 링크 참조). 검색 스니펫이나 블로그가 아니라 공식 docs가 기준:
   - hooks 레퍼런스 — 이벤트 목록, exit code 의미, JSON 출력 스키마, `hookSpecificOutput`
   - `/goal` — 가용 조건, 평가 모델 동작, 제약
   - .claude 디렉터리 — 파일별 위치/스코프
   - settings — 우선순위, hook 설정 키

3. **특히 의심하고 재확인할 함정들:**
   - exit code: **차단은 `exit 2`만** 된다. `exit 1`은 무시되고 진행됨.
     (내 기존 hook이 무시당한 원인일 가능성이 큼 — 반드시 확인)
   - PreToolUse는 상단 `decision`이 아니라 `hookSpecificOutput.permissionDecision` 사용
     (`approve`/`block`은 deprecated → `allow`/`deny`)
   - `additionalContext`는 명령조가 아니라 **사실 진술**로 작성
     (명령조면 prompt-injection 방어 발동)
   - hook 이벤트 이름과 매처 규칙이 버전마다 추가/변경됨 — 현재 목록을 docs에서 확인

4. **불일치가 있으면 멈추고 보고한다.** 이 문서의 내용과 현재 공식 docs/버전이
   어긋나면, 임의로 추측해서 진행하지 말고 차이를 먼저 알린 뒤 결정을 받는다.

> 요약: **버전 확인 → 공식 docs 정독 → 함정 재확인 → 불일치 보고.**
> 이 4단계를 건너뛰고 기억으로 짠 코드는 십중팔구 옛 스키마라 동작하지 않는다.

---

## 0. 핵심 철학

> **모델이 잘 따라주길 기대하지 말고, 따를 수밖에 없는 구조를 만든다.**

내가 Claude Code에서 겪는 문제 세 가지(망각 / 과잉행동 / 규칙 위반)는
전부 "내가 정한 제약을 모델이 벗어난다"는 한 뿌리에서 나온다.
원인은 그 제약을 **모델이 어길 수 있는 곳(말, CLAUDE.md 같은 권고)**에 두고 있기 때문.

해법의 방향: 제약을 **권고(advisory)에서 강제(deterministic)로 옮긴다.**
- CLAUDE.md = 권고. 컨텍스트가 길어지면 흐려지고, 모델이 하드룰로 안 느낌.
- hooks = 결정론적. 모델이 무시할 수 없음.

이건 2026년 에이전트 트렌드의 "deterministic guardrails", "hooks는 보장된 실행,
프롬프트는 아니다"와 정확히 같은 얘기다. 직접 구현하면 그 트렌드를 손으로 이해하는 셈.

---

## 0-1. harness란 무엇인가 (용어 정렬)

> **Agent = Model + Harness.** "네가 모델이 아니라면, 너는 harness다." (LangChain)

harness는 LLM을 감싸는 전체 소프트웨어 인프라 — 오케스트레이션 루프, 도구,
메모리, 컨텍스트 관리, 상태 영속화, 에러 처리, 가드레일까지 전부. 2026년 2월
(Mitchell Hashimoto)에 용어가 정식화됐고, production harness의 표준 구성요소는
**상태·영속화 / 보안·거버넌스 / 오케스트레이션·도구 / 메모리 / 관측성 / 평가(evals)** 6가지.

→ 따라서 이 프로젝트의 hooks와 서브에이전트는 *대립이 아니라* 둘 다 harness의 구성요소다.
- **hooks** = 결정론 바닥 (보안·거버넌스, 컴퓨트 검증)
- **서브에이전트(PGE)** = 판단 루프 (오케스트레이션, 추론적 평가)

---

## 0-1b. 부품별 형태 매핑 (skill? prompt? hook?)

이 harness는 **단일 형태가 아니라 여러 메커니즘의 조합**이다. 부품마다 형태가 다르다.
핵심 원칙: **"단순 prompt"로 만들면 안 된다.** prompt는 모델이 어길 수 있고(=망각·과잉행동),
그걸 막는 게 이 프로젝트의 존재 이유다. 그래서 강제가 필요한 건 prompt가 아니라 코드(hook)로 내린다.

| 부품 | 형태 | 위치 | 비고 |
|------|------|------|------|
| 망각 방지 / 과잉행동 차단 / 테스트 강제 | **hook + 셸 스크립트** | `settings.json` hooks + `~/.claude/hooks/*.sh` | prompt 아님. 모델이 못 어기는 결정론 바닥 |
| Evaluator / Generator / Planner | **서브에이전트** | `~/.claude/agents/*.md` | 각자 프롬프트 + 도구. 별도 컨텍스트에서 실행 |
| `/harness-build` 같은 진입점 | **skill** | `~/.claude/skills/<name>/SKILL.md` | 형욱이 이름으로 호출하는 재사용 프롬프트 (`/goal`처럼) |
| 항상 적용될 지침/컨벤션 | **CLAUDE.md / rules** | `~/.claude/CLAUDE.md`, `rules/*.md` | "파일로 박힌 prompt". 권고성 |

> 이 매핑은 설계상 예측이다. 실제 형태는 Claude Code에서 형욱과 부품별로 확정한다
> (예: "이 검증은 hook으로, 이 평가는 agent로"). 검증 단계 후 Claude Code가 형태를 제안하면 조율할 것.

---

## 0-2. 핵심 구조 — Planner → Generator → Evaluator (PGE)

Anthropic Labs(Prithvi Rajasekaran)가 공식 엔지니어링 블로그에 발표한 구조(2026-03/04).
GAN에서 영감받아 **"생성하는 자"와 "비판하는 자"를 분리**한 것이 핵심.

핵심 발견: **"더 똑똑한 모델 ≠ 더 나은 코드. harness가 결과를 결정한다."**
- 같은 작업: Evaluator 없이 → 20분/$9, 핵심 기능 깨짐.
- 풀 PGE 루프 → 6시간/$200, 기능적으로 올바름.

| 역할 | 하는 일 | 출력 |
|------|---------|------|
| **Planner** | 짧은 프롬프트를 상세 명세로 확장. 범위·엣지케이스·**수용 기준**·**도메인별 검증 방법**을 코드 전에 정의 | 코드가 아니라 "올바른 동작이 무엇인지"의 구조화된 명세 |
| **Generator** | 명세를 구현. 코드·테스트·CI·문서 생산. 역할은 throughput | 코드 |
| **Evaluator** | 출력을 합의된 계약·기준에 대해 **실제 실행하여** 검증·채점. 하드 임계값 강제, 미달 시 실패. 구체적·실행가능한 지적 제공 | 점수 + 반려 피드백 |

**두 가지 실패 모드를 푼다:**
1. 컨텍스트 저하 / "context anxiety"(창이 차면 조기 마무리) → Planner의 분해 + 컨텍스트 리셋.
2. **자기평가 불가**(코드 쓴 모델이 그 코드를 칭찬함) → 독립 Evaluator 분리.

**중요한 후속 교훈:** Anthropic은 이후 3-에이전트를 다시 *단순화*했다.
"모델이 좋아지면 harness도 진화해야 한다." → 처음부터 풀 멀티에이전트로 짓지 말 것.
**Evaluator 하나(컴퓨트 검증)부터 시작**하고 필요할 때 확장.

---

## 0-3. 도메인별 Evaluator — "검증 레시피" 방식

Evaluator의 검증 *방법*은 도메인에 따라 다르다. (Anthropic: "리뷰 방법은 도메인 의존적,
설정 가능해야 한다. 기준은 하드코딩하지 않고 Planner가 도메인에 따라 정의한다.")

→ **설계 결정: 도메인별 Evaluator를 N개 만들지 않는다.**
Evaluator는 하나, **도메인별 "검증 레시피"를 갈아끼우는** 방식. (lean, 저유지보수)
Planner가 작업의 도메인을 판별 → 해당 레시피 + 기댓값 + 통과 기준을 명세에 박음 →
Evaluator가 그 레시피를 *실제 실행*해서 채점.

| 도메인 | 검증 레시피(실제 실행) | 통과 기준 예시 |
|--------|----------------------|----------------|
| 프론트엔드 | Playwright MCP로 페이지 탐색·스크린샷 | 요소 렌더, 인터랙션 동작 |
| 백엔드 | API 호출 → health check + 응답 JSON 대조 | status 200, 기댓값 JSON 일치 |
| DB | 직접 쿼리 실행 | 행 수/스키마/값이 기댓값과 일치 |
| 일반 코드 | 테스트·린트·빌드 실행 | exit 0, 커버리지 임계값 |

> ⚠️ **이 테이블의 구체값(레시피 디테일, 기댓값, 통과 기준)과 "Evaluator를 몇 개로 둘지"는
> 확정이 아니다. Claude Code에서 형욱과 직접 의논하여 실제 작업 환경에 맞게 정한다.**
> (형욱이 주로 다루는 도메인을 먼저 묻고, 그 위주로 레시피를 구체화할 것.)

---

## 0-4. 반복 루프 — "수렴 또는 안전 중단까지" (무한 아님)

목표: "Evaluator가 통과시킬 때까지 알아서 반복." 사실상 형욱 버전의 `/goal`
(완료 조건 = Evaluator 통과). **단, "무한"으로 만들면 사고 난다.** 막아야 할 3가지:

1. **무한루프(돈/시간 소각)** — 통과 못 하는 작업에서 토큰 무한 소모.
   (`/goal`조차 runaway guard로 최대 500 연속; Anthropic도 생성당 5~15회/최대 ~4시간)
2. **거짓 통과(hallucinated success)** — Evaluator가 LLM이면 "이제 됐다 치자"로 거짓 통과.
   → **방지책: Evaluator 판정을 "말"이 아니라 실제 실행 결과(테스트 exit code, API 응답,
   쿼리 결과)에 묶는다.** ← 형욱의 "테스트 안 돌리고 됐다 함" 문제 해결이 곧 이 안전장치.
3. **진동(oscillation)** — A 고치면 B 깨지고 B 고치면 A 깨지는 무한 왕복.

**안전한 종료 조건(원칙):**
- 최대 반복 횟수 상한 (예: 10~15회)
- 점수 정체 감지: N회 연속 개선 없으면 중단하고 형욱 호출
- 하드 게이트: Evaluator 판정이 실제 실행 결과에 묶임 (거짓 통과 방지)
- 반려 시 구체적·실행가능한 피드백을 Generator에게 전달

> ⚠️ **구체적인 반복 횟수·정체 감지 임계값도 Claude Code에서 형욱과 의논하여 확정.**

---

## 1. 풀어야 할 문제 → 해결 매핑

| # | 문제 | 들어갈 위치 | 메커니즘 |
|---|------|------------|----------|
| 1 | 대화 길어지면 초반 지침을 잊음 | `UserPromptSubmit` hook | `additionalContext`로 매 턴 핵심 지침 재주입 |
| 2 | 시키지 않은 걸 멋대로 함 (과잉행동) | `PreToolUse` hook | `exit 2` 또는 `permissionDecision: "deny"`로 차단 |
| 3 | 코드 스타일/규칙을 안 지킴 | `PostToolUse` hook | Edit/Write 직후 린터·포매터 자동 실행 |

---

## 2. 위치 결정 — global(`~/.claude/`)

"어느 환경에서든 동일하게 동작" 요구사항 → **global에 둔다.**
(공식: 프로젝트 파일은 git 공유용, `~/.claude`는 모든 프로젝트에 적용되는 개인 설정)

| 넣을 것 | 파일 |
|---------|------|
| 항상 적용될 지침/규칙 | `~/.claude/CLAUDE.md`, `~/.claude/rules/*.md` |
| hooks, 권한, 환경변수 | `~/.claude/settings.json` |
| `/이름`으로 부르는 재사용 프롬프트 | `~/.claude/skills/<name>/SKILL.md` |
| 서브에이전트 | `~/.claude/agents/*.md` |

여러 환경 동기화 → `~/.claude`를 git repo로 만들고, 필요시 `CLAUDE_CONFIG_DIR`
환경변수로 clone 위치를 가리키게 한다.

---

## 3. hooks 핵심 원리 (반드시 지킬 것)

### 3-1. exit code — "무시당하는" 문제의 진짜 원인
- **대부분 이벤트에서 오직 `exit 2`만 동작을 차단한다.**
- `exit 1`은 non-blocking 에러로 취급되어 **그냥 진행됨** (유닉스 관습과 반대!).
- → 기존 hook이 무시당했다면 십중팔구 `exit 1`을 쓰고 있었던 것. `exit 2`로 교체.
- (예외: `WorktreeCreate`는 모든 non-zero가 차단)

### 3-2. additionalContext — 사실 진술로 쓸 것
- 매 턴/세션 컨텍스트에 텍스트 주입 가능. 망각 해결의 핵심.
- **명령조("~하지 마")가 아니라 사실 진술("이 repo는 bun을 쓴다")로 작성.**
- 명령조로 쓰면 prompt-injection 방어가 발동 → 모델이 무시하고 사용자에게 보여줄 수 있음.
- 정적·불변 지침은 hook 대신 CLAUDE.md가 적합 (스크립트 없이 로드됨).

### 3-3. PreToolUse 차단 방식
- 최신 권장: 상단 `decision` 대신 `hookSpecificOutput` 사용.
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "이유 (deny일 때 Claude에게 보여짐)"
  }
}
```
- `permissionDecision`: `allow` / `deny` / `ask` / `defer`
- 여러 hook 충돌 시 우선순위: `deny` > `defer` > `ask` > `allow`

### 3-4. JSON vs exit code — 섞지 말 것
- 한 hook당 한 방식만: exit code로 신호 OR `exit 0` + JSON 출력.
- JSON은 `exit 0`에서만 처리됨. `exit 2`면 JSON 무시됨.
- stdout엔 JSON 객체만 있어야 함 (셸 프로파일이 텍스트 찍으면 파싱 깨짐).

### 3-5. 스크립트 경로 참조
- `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}` 플레이스홀더 사용.
- 경로 참조 hook은 **exec form**(`args` 배열) 권장 — 공백·특수문자 따옴표 문제 없음.

---

## 4. 각 문제별 구현 스케치

### 문제 1 — 망각 (UserPromptSubmit)
- 매 프롬프트 제출 시 hook이 핵심 지침을 `additionalContext`로 주입.
- 100턴이 가도 매 턴 다시 넣으니 흐려짐이 구조적으로 불가능.
- 타임아웃 기본 30초(다른 이벤트보다 짧음) 주의 — 무거운 작업 금지.
- 지침 소스는 별도 파일(예: `~/.claude/harness/core-rules.md`)에서 읽어오게 하면 관리 편함.

### 문제 2 — 과잉행동 (PreToolUse + deny)
- 막을 행동 정의 예시:
  - 묻지 않고 새 파일 대량 생성
  - 시키지 않은 리팩터링
  - 특정 보호 디렉터리 수정
- `matcher`로 도구(Write|Edit 등) 좁히고, `if`로 더 좁힘(`if: "Edit(*.ts)"` 등).
- `if`는 규칙 하나만 — `&&`/`||` 없음. 여러 조건은 핸들러를 여러 개로.

### 문제 3 — 스타일 (PostToolUse + 자동 포맷)
- Edit/Write 성공 직후 린터/포매터 강제 실행.
- 모델 준수에 의존하지 않고 뒤에서 교정 → 어겨도 결과가 맞음.
- 예: prettier / black / ruff / eslint 등 프로젝트 도구.

---

## 5. /goal 활용 (이미 만들어진 끈질김)

- v2.1.139+ 기능. 완료 조건 설정 → 매 턴 작은 모델이 충족 여부 평가 →
  안 됐으면 제어 안 돌려주고 다음 턴 계속 → 충족되면 자동 종료.
- 내부 구현이 곧 **Stop hook + 영속 상태 + 평가 모델** — 내가 만들려던 구조와 동일.
- 주의:
  - 평가 모델은 **대화에 드러난 내용으로만 판단** (직접 실행/파일 읽기 안 함).
    → "Claude 자신의 출력으로 증명 가능한 조건"으로 작성.
    좋은 예: "test/auth의 모든 테스트 통과". 나쁜 예: "프로덕션 준비 완료"(검증 불가).
  - hooks 시스템 일부라 trust 수락 필요. `disableAllHooks`/`allowManagedHooksOnly`면 비활성.
  - 세션 스코프(--resume로 여러 날 이어감) — "항상 동일"은 아님.
- 참고 구현: `jthack/claude-goal` (Stop hook으로 goal 활성 동안 멈춤 차단, pause/clear/complete).

---

## 6. git repo 안전 셋업 (비밀 유출 방지)

`~/.claude`엔 비밀이 잔뜩 있다. 그대로 push 금지.

**절대 올리면 안 되는 것:**
- `~/.claude.json` — OAuth 토큰, 인증, 개인 MCP 설정
- `projects/` — 대화 transcript 전체(코드·명령출력·붙여넣기 평문)
- `history.jsonl` — 입력한 모든 프롬프트
- `settings.local.json`, `shell-snapshots/`, `todos/`, 각종 캐시

**올릴 것(내가 작성한 설정만):**
- `CLAUDE.md`, `rules/*.md`, `settings.json`(비밀 없을 때),
  `skills/`, `commands/`, `agents/`, `output-styles/`

**방식: blacklist 말고 화이트리스트** (전부 무시 + 안전한 것만 허용).
새 파일 생겨도 토큰이 새지 않음.

`~/.claude/.gitignore`:
```gitignore
# 전부 무시
*
# 디렉터리는 진입 허용
!*/
# 안전한 설정만 화이트리스트
!CLAUDE.md
!settings.json
!.gitignore
!rules/**
!skills/**
!commands/**
!agents/**
!output-styles/**
# 방어용 재차단 (화이트리스트 뒤)
.claude.json
settings.local.json
**/*.local.json
.env
```

**push 전 필수 확인:**
```bash
cd ~/.claude
git init
git add -A
git status      # .claude.json / projects/ 보이면 멈추고 .gitignore 수정
```
- transcript나 `.claude.json`이 보이면 절대 commit 금지.
- 한 번 올라간 비밀은 히스토리에 남아 제거 까다로움.
- **repo는 private.**
- settings.json에 토큰/키가 박혀 있으면 → 환경변수로 먼저 빼고 push.

**복원(새 환경):** clone → `~/.claude`에 배치 또는 `CLAUDE_CONFIG_DIR`로 지정.

---

## 7. npm / plugin — 지금은 안 함

- 목적이 "개인 설정 동기화"지 "배포"가 아님 → npm은 오버킬.
- 환경 두세 개 동기화엔 git repo면 충분.
- npm/plugin이 의미 있어지는 때 = **나중에 공개하기로 결정했을 때.**
  (잘 빠진 하네스를 "나만의 Claude Code 셋업"으로 공개 → SE 포트폴리오의 "공개된 흔적")
- 순서: **git repo가 토대, npm/plugin은 공개 결정 후 씌우는 포장.**
  repo 구조 그대로 두고 포장만 바꾸면 됨. 거꾸로는 낭비.

---

## 8. 다음 스텝 (Claude Code에서)

전체는 두 층이다: **결정론 바닥(hooks)** 먼저 깔고, 그 위에 **판단 루프(PGE)**.
Anthropic 교훈대로 처음부터 풀 멀티에이전트로 짓지 말고 작게 시작 → 확장.

**A. 결정론 바닥 (hooks) — 먼저**
hook 하나를 제대로 만들면 나머진 같은 패턴이라 빨라진다.
1. **스타일(PostToolUse 자동 포맷)** — 제일 쉽고 효과 즉각적. 워밍업으로 적합.
2. **망각(UserPromptSubmit 주입)** — 형욱이 1번으로 꼽은 핵심. core-rules 파일 분리.
3. **과잉행동(PreToolUse deny)** — 제일 위험하지만 설계 까다로움. 마지막.
4. git repo화 + .gitignore (6번) — 셋업되면 동기화 마무리.

**B. 판단 루프 (PGE) — 그 다음, 형욱과 의논하며**
5. **Evaluator 하나부터** — 가장 단순한 컴퓨트 검증(테스트/린트 실행 → 채점)으로 시작.
   "테스트 안 돌리고 됐다 함" 문제가 여기서 해결됨.
6. **도메인별 검증 레시피** (0-3) — 형욱이 주로 쓰는 도메인부터 구체화. **의논 필요.**
7. **반복 루프 안전장치** (0-4) — 최대 횟수·정체 감지·하드 게이트. **의논 필요.**
8. **Planner / 풀 PGE** — 마지막. 모델이 충분히 강하면 단순하게 유지하는 것도 선택지.

> 5~8(PGE 관련)은 확정 설계가 아님. Claude Code에서 형욱과 직접 의논하며 형욱의 실제
> 작업 환경에 맞춰 정한다. 임의로 풀 구조를 짜놓지 말 것.

각 단계 후 `/hooks` 메뉴로 등록 확인, 설정 안 먹으면 `/debug` 또는
docs의 "Debug your configuration" 참고.

---

## 부록 — 참고 링크
- .claude 디렉터리: https://code.claude.com/docs/en/claude-directory
- hooks 레퍼런스: https://code.claude.com/docs/en/hooks
- /goal: https://code.claude.com/docs/en/goal
- 설정 우선순위: https://code.claude.com/docs/en/settings
- **Anthropic 엔지니어링 블로그 — PGE harness 설계 (1차 소스, 반드시 직접 확인):**
  https://www.anthropic.com/engineering 에서 Prithvi Rajasekaran의 harness 설계 글
  (Planner/Generator/Evaluator, 2026-03/04) 검색해서 원문 검증할 것.
- harness 개념 정리(참고): LangChain "Anatomy of an Agent Harness",
  Martin Fowler "Harness Engineering"
