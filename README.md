# claude-harness

형욱의 개인 **Claude Code 하네스(harness)** — hooks · skills · agent 로 Claude Code에
"모델이 어길 수 없는 결정론적 바닥"과 "검증 기반 작업 루프(PGE)"를 입힌다.

> 핵심 철학: **모델이 잘 따라주길 기대하지 말고, 따를 수밖에 없는 구조를 만든다.**
> 제약을 권고(CLAUDE.md 같은 말)가 아니라 강제(hook 코드)로 내린다.

- 설계 명세(source of truth): [`docs/claude-harness-design.md`](docs/claude-harness-design.md)
- 실제 빌드 기록: [`docs/build-log.md`](docs/build-log.md)

---

## 무엇을 해결하나

| 문제 | 해결 |
|------|------|
| 대화가 길어지면 초반 지침을 잊음 | 매 프롬프트마다 핵심 규칙 재주입(hook) |
| 시키지 않은 걸 멋대로 함(과잉행동) | 보호 경로 편집 차단(hook) |
| 스타일/규칙을 안 지킴 | 편집 직후 자동 포맷(hook) |
| "테스트 안 돌리고 됐다고 함" | 작업 끝에 **실제 테스트를 돌려** 통과 전엔 '완료'를 막음(PGE 게이트) |

---

## 1. 최초 설정 (한 번만)

**필요한 것**
- **Python 3** (모든 hook이 Python stdlib로 동작) · **Git**
- 선택: **ruff**(파이썬 자동 포맷/린트), **Node**(JS/TS 프로젝트 검증)

**설치**
```bash
git clone https://github.com/sleepy-wook/my-claude-harness.git
cd my-claude-harness
python deploy.py        # claude/ 의 내용을 ~/.claude 로 배포 + settings.json에 hooks 병합
```
- `deploy.py`는 **멱등**이다(여러 번 돌려도 안전). 미리 보려면 `python deploy.py --check`.
- 배포되는 것: `hooks/` 스크립트, `harness/` 규칙, `agents/`, `skills/` →
  현재 머신의 실제 경로로 `~/.claude/settings.json`의 `hooks` 키에 병합(다른 설정 보존).

**마무리**
- **Claude Code를 재시작**한다 — 에이전트/스킬은 세션 시작 시 로드되므로 첫 배포 후 1회 필요.
  (hook은 재시작 없이도 곧 반영된다.)
- 첫 hook 실행 시 trust(신뢰) 수락 프롬프트가 뜨면 허용한다.

> 새 PC에서 복원: 위 3줄을 그대로 반복하면 된다(`clone → deploy → 재시작`).

---

## 2. 그 다음 — 계속 쓰는 법

설치하면 hook은 **모든 프로젝트에서 자동**으로 돈다. 따로 켤 것 없다.

### 항상 자동으로 도는 것 (hooks)
- **자동 포맷** — `.py` 파일을 편집하면 직후 `ruff format` 적용.
- **망각 방지** — 매 프롬프트에 핵심 규칙을 컨텍스트로 주입.
  - 규칙 편집: `~/.claude/harness/core-rules.md` (다음 프롬프트부터 반영, 재시작 불필요).
    repo에서 관리하려면 `claude/harness/core-rules.md`를 고치고 `python deploy.py`.
- **보호 경로 가드** — `.git/`·자격증명·개인키 파일의 Edit/Write를 실행 전 차단.

### 중간 이상 규모의 구현 (PGE 루프)
```
/wook-plan  →  (구현)  →  자동 게이트가 매 턴 검증
   │                          └ 미통과면 '완료'를 막고 자동으로 계속 고침
   └ 수용 기준을 .claude/evaluate.recipe 로 써둠 = 게이트 자동 ON
```
1. **`/wook-plan`** 으로 시작 — 짧은 요청을 *실행 가능한 수용 기준*이 담긴 스펙으로 확장하고,
   그 기준을 `.claude/evaluate.recipe`(검증 레시피)로 써준다. **레시피가 생기는 순간 게이트가 켜진다.**
2. 구현한다. 턴이 끝날 때마다 게이트가 레시피의 체크를 **실제로 돌려** 판정한다(실제 exit code).
   실패하면 "완료"를 막고 실패 내용을 돌려줘 자동으로 계속 고치게 한다(무한루프 방지 가드 내장).
3. 깊은 점검이 필요하면 언제든 **`/wook-evaluate`** (독립 컨텍스트 평가자)로 온디맨드 검증.

### 검증 레시피 (`.claude/evaluate.recipe`)
프로젝트가 **자기 검증 방법을 데이터로 선언**한다. 어떤 stack/도메인이든 한 줄씩:
```
# name: 셸 명령  (exit 0 = 통과)
tests: pytest -q
lint:  ruff check .
api:   curl -sf http://localhost:8000/health
db:    python scripts/check_db.py
```
- 템플릿: `~/.claude/harness/evaluate.recipe.example` (복사해서 프로젝트에 맞게 수정).
- 보통 `/wook-plan`이 자동으로 써주므로 직접 안 만들어도 된다.
- **게이트 끄기**: 해당 프로젝트에 빈 파일 `.claude/evaluate-off`를 둔다.

### 하네스 자체를 업데이트할 때
```bash
# claude/ 아래 파일을 고친 뒤
python deploy.py        # ~/.claude 에 반영
git add -A && git commit -m "..." && git push   # 백업/동기화
```

---

## 3. 원리 (어떻게 동작하나)

### (a) 결정론 바닥 — hooks
hook은 Claude Code 생명주기의 특정 시점에 **반드시** 실행되는 셸/스크립트다.
프롬프트와 달리 모델이 무시할 수 없다. 그래서 "꼭 일어나야 하는 것"을 여기에 둔다.

| 이벤트 | 하는 일 | 스크립트 |
|--------|---------|----------|
| `PostToolUse` (Edit\|Write) | `.py` 자동 포맷 | `hooks/format_py.py` |
| `UserPromptSubmit` | core-rules 재주입 | `hooks/inject_core_rules.py` |
| `PreToolUse` (Edit\|Write) | 보호 경로 deny | `hooks/guard_paths.py` |
| `Stop` | 자동 검증 게이트 | `hooks/evaluate_gate.py` |

모든 스크립트는 문제가 생겨도 작업을 막지 않도록 안전하게 빠진다(자동 포맷·주입·게이트는
실패 시 그냥 통과). 차단은 의도된 곳(보호 경로 deny, 검증 미통과)에서만 일어난다.

### (b) 판단 루프 — PGE (Planner → Generator → Evaluator)
Anthropic의 하네스 설계에서 온 구조. **"생성하는 자"와 "비판하는 자"를 분리**한다.
코드를 쓴 컨텍스트가 자기 코드를 칭찬하지 못하도록, 평가자는 **독립 컨텍스트**에서 돈다.

- **Planner (`/wook-plan`)** — 코드 전에 "올바른 동작이 무엇인지"를 *실행 가능한 수용 기준*으로
  정의하고 레시피로 박는다.
- **Generator** — 그 기준을 향해 구현(메인 작업).
- **Evaluator** — 합의된 레시피를 **실제로 실행**해 채점.
  - `/wook-evaluate` = 온디맨드 독립 평가자(`wook-evaluator` 서브에이전트).
  - 자동 게이트(`Stop` hook) = 매 턴 싸고 결정론적으로 강제.

핵심 안전장치: **판정을 "말"이 아니라 실제 실행 결과(exit code)에 묶는다.** 그래서
"테스트 안 돌리고 됐다 함"이 구조적으로 불가능하다. 자동 게이트는 §0-4의 안전 종료 조건
(정체 감지·최대 시도·새 stop 리셋)을 갖춰 무한루프/진동을 막는다.

### (c) 검증은 하드코딩이 아니라 레시피
검증 방법은 도메인마다 다르다. 그래서 stack을 추측하지 않고, 프로젝트가
`.claude/evaluate.recipe`에 명령을 선언한다. stack이 바뀌면 그 파일만 고치면 된다.

### (d) source-of-truth + 배포 (왜 repo와 ~/.claude가 분리됐나)
실제 하네스는 `~/.claude`에 사는데, 그곳엔 토큰·대화기록 같은 **비밀이 많다.** 그래서
`~/.claude`를 직접 git하지 않는다. 대신 **이 repo가 원본**이고, `deploy.py`가 `~/.claude`로
복사한다 — repo 폴더엔 비밀이 0이라 구조적으로 안전하다(`.gitignore` 실수해도 샐 게 없음).

---

## repo 구조
```
my-claude-harness/
├─ README.md · CLAUDE.md
├─ docs/
│  ├─ claude-harness-design.md   # 설계 명세 (source of truth)
│  └─ build-log.md               # 실제 빌드 기록
├─ claude/                       # ~/.claude 로 배포되는 원본 (비밀 0)
│  ├─ hooks/                     # 4개 hook 스크립트
│  ├─ harness/                   # core-rules + 레시피 템플릿
│  ├─ agents/wook-evaluator.md   # 독립 Evaluator 서브에이전트
│  └─ skills/{wook-plan, wook-evaluate}/SKILL.md
└─ deploy.py                     # claude/ → ~/.claude 멱등 배포
```

## 구성요소 한눈에
| 이름 | 종류 | 호출/발동 |
|------|------|-----------|
| `/wook-plan` | skill | 직접 호출 — 스펙·수용 기준·레시피 작성 |
| `/wook-evaluate` | skill | 직접 호출 — 온디맨드 독립 검증 |
| `wook-evaluator` | agent | `/wook-evaluate`가 디스패치 |
| 자동 포맷 · 망각 방지 · 보호 가드 · 검증 게이트 | hooks | 자동 |
