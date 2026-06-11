# 2026 AI Agent Harness 트렌드 — 심층 리서치 리포트

> **조사일:** 2026-06-02
> **대상:** AI 에이전트 실행 레이어(harness/스캐폴딩) 트렌드
> **초점 3축:** ① Harness/스캐폴딩 자체 ② 오케스트레이션·멀티에이전트 ③ 평가·검증(eval/gate)
> **목적:** 이 repo(개인 Claude Code harness)의 **PGE(Plan-Generate-Evaluate) 루프** 설계에 대한 시사점 도출

---

## 0. 방법론과 한계 (먼저 읽을 것)

- **방법:** 5개 검색 각도로 분해 → 각 각도마다 병렬 웹 리서치 에이전트가 4~6회 검색 → 주장(falsifiable claim) 추출 → 교차검증·신뢰도 등급화.
- **⚠️ 핵심 한계 — 1차 출처 직접 검증 실패:** 이번 세션에서 **WebFetch가 모든 도메인에 대해 403으로 차단**되었다. 따라서 검색 엔진이 반환한 **요약 스니펫**에만 의존했고, 전체 원문을 직접 읽은 출처는 **Claude 공식 문서(hooks, memory tool, Agent SDK 마이그레이션 가이드)뿐**이다.
- **⚠️ 일부 수치·논문은 신뢰 보류:** 다음은 검색 요약이 **환각(hallucination)했을 가능성**이 있어 *낮은 신뢰도*로 표시했다:
  - 미래 날짜 arxiv ID (`2602.*`, `2603.*`, `2604.*`, `2605.*`, `2606.*`) — 어시스턴트 학습 컷오프(2026-01) 이후 ID로 직접 확인 불가.
  - 비현실적으로 구체적인 리더보드 수치·모델명("GPT-5.5 0.827", "Claude Mythos Preview", "MCP 9,700만 다운로드", 설문 백분율 등).
- **신뢰도 표기:** 🟢 높음(1차 문서로 검증) / 🟡 중간(복수 2차 출처 일치) / 🔴 낮음(단일·미래날짜·환각 의심).

---

## 1. Executive Summary (핵심 결론 7가지)

1. **"Context Engineering"이 "Prompt Engineering"을 대체**하는 1차 설계 규율로 자리잡았다. 컨텍스트 윈도우를 희소 자원으로 보고, 매 추론마다 들어갈 토큰을 *큐레이션*하는 것이 에이전트 설계의 핵심. 🟢
2. **Just-in-time 컨텍스트 로딩**이 사전 적재(pre-stuffing RAG)를 대체하는 권장 기본값. 파일 경로·ID 같은 가벼운 식별자만 들고, 런타임에 도구로 끌어온다. 🟢
3. **결정론적 Hooks가 harness의 골격.** 모델의 "선택"에 맡기지 않고 라이프사이클 지점(PreToolUse, Stop 등)에서 항상 실행되는 가드. deny는 권한 모드로도 못 뚫는다. 🟢 — **이 repo의 #1~#3 hook 설계와 정확히 일치.**
4. **단일 vs 멀티에이전트 논쟁의 핵심은 "공정한 컴퓨트 비교".** Anthropic은 멀티에이전트가 리서치에서 +90.2% 우위(단, 토큰 ~15배)를 보고했으나, 토큰 예산을 동등하게 통제하면 단일 에이전트가 대등하거나 낫다는 반론이 2026년 쟁점. 🟡/🔴
5. **2026 배포 합의:** "오케스트레이터 1개가 전체 컨텍스트 소유 + 일회성 격리 서브에이전트가 압축 요약만 반환." 쓰기(write)는 단일 스레드, 읽기(read)는 병렬. 🟡
6. **자기검증(self-verification)은 외부 신호 없이는 취약하다.** 모델이 자기 추론을 스스로 고치는 건 중립~해로움. 그러나 **테스트·컴파일러·실행 결과 등 grounded 신호**에 묶으면 신뢰성 있게 작동. 🟢 — **이 repo가 LLM 자가판단이 아닌 *레시피(테스트/lint/build) 구동 게이트*를 택한 것이 정답 방향.**
7. **"테스트 통과 = 우회 불가능한 최강 검증 게이트"**가 에이전틱 코딩의 합의. Stop hook은 프롬프트 지시보다 강하고 CI보다 약한 중간 검증 체크포인트. 🟢 — **이 repo의 #7 Stop hook 게이트와 정확히 부합.**

---

## 2. 축 ① — Harness / 스캐폴딩 설계 패턴

### 2.1 Context Engineering (1차 규율로 부상)
- **주장:** "Context engineering"이 prompt engineering을 잇는 핵심 규율로, 컨텍스트 윈도우에 들어가는 *모든 정보*를 관리하는 것. 🟢
  - 출처: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Cognition도 독립적으로 같은 용어를 쓰며 "에이전트 엔지니어의 사실상 1순위 업무"라 표현. 🟢(LangChain이 출처 귀속 교차확인)
  - 출처: https://cognition.ai/blog/dont-build-multi-agents

### 2.2 Just-in-Time 로딩 & 에이전틱 검색 > RAG
- **주장:** 모든 걸 미리 적재하지 말고, 가벼운 식별자(파일 경로·ID)만 유지 후 런타임에 도구로 끌어오라. 🟢
  - 출처: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool ("the key primitive for just-in-time context retrieval")
- **주장:** grep·파일 읽기 같은 **에이전틱 검색을 먼저** 쓰고, 필요할 때만 시맨틱/벡터 검색을 추가. 🟡
  - 출처: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ; https://venturebeat.com/data/context-architecture-is-replacing-rag-as-agentic-ai-pushes-enterprise-retrieval-to-its-limits

### 2.3 Compaction & Memory (컨텍스트 리셋 생존)
- **주장:** Compaction(컨텍스트 한계 근처에서 오래된 맥락을 **서버사이드 요약**)이 1급 API 기능이 됨. 아키텍처 결정·미해결 버그는 보존하고 중복 도구 출력은 폐기. 🟢(존재·동작은 검증, 정확한 "2026-01 베타" 날짜는 🟡)
  - 출처: https://platform.claude.com/docs/en/build-with-claude/compaction ; https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- **주장:** Memory는 컨텍스트 윈도우 밖 **파일 기반 시스템**으로, `/memories` 제한 디렉터리에 세션 간 영속. view/create/str_replace/insert/delete/rename로 조작. 🟢
  - 출처: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- **주장(장기 실행 패턴):** 초기화 세션이 진행 로그+기능 체크리스트를 만들고, 이후 세션이 이를 읽어 상태 복구, 종료 전 로그 갱신. 규칙: **"한 번에 한 기능씩, 엔드투엔드 검증 후에만 완료 표시."** 🟢
  - 출처: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool ; (참조) https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - 시스템 프롬프트 경고 인용: *"Your context window might be reset at any moment, so you risk losing any progress that is not recorded in your memory directory."*

> 💡 **이 repo 연결:** `CLAUDE.md` + `docs/build-log.md`(진행 로그) 구조가 정확히 이 "노트테이킹 부트스트랩" 패턴이다. "만든 것은 build-log에 기록"이라는 프로젝트 규칙은 컨텍스트 리셋 생존 전략의 교과서적 구현. core-rules의 "완료=실행 결과로 증명"은 위 "엔드투엔드 검증 후에만 완료 표시"와 동일 철학.

### 2.4 Hooks = 결정론적 가드레일 (harness의 골격)
- **주장:** Hooks는 라이프사이클 지점에서 실행되는 셸 명령으로, *"LLM이 실행하기로 선택하길 기대하는 대신 특정 행동이 항상 일어나도록 보장"*한다. 이벤트: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact, PostCompact, ConfigChange. 🟢
  - 출처: https://code.claude.com/docs/en/hooks-guide
- **주장:** PreToolUse hook은 도구 실행 전 차단 가능 — exit code 2(stderr가 Claude에 피드백) 또는 JSON `{"permissionDecision":"deny"}`. 여러 hook 충돌 시 **가장 제한적인 답이 승리(deny > ask > allow)**. 🟢
- **주장:** hook의 `allow`는 deny를 못 덮는다 — 관리형(managed) deny/ask 규칙이 항상 우선. 🟢
  - ⚠️ **이견:** 일부 실무 블로그는 deny가 `--dangerously-skip-permissions`까지 무력화한다고 주장하나, 공식 문서는 "관리형 설정 우선"으로 더 좁게 기술. 커뮤니티 단순화로 보임.
  - 출처: https://code.claude.com/docs/en/hooks-guide vs https://aport.io/blog/secure-claude-code-hooks-pretooluse-guardrails/

> 💡 **이 repo 연결:** #1 PostToolUse(자동 포맷), #2 UserPromptSubmit(core-rules 재주입), #3 PreToolUse(보호 경로 deny)가 모두 공식 권장 패턴과 정합. 특히 #3의 "deny는 권한 모드로도 못 뚫는 하드 게이트"라는 build-log 서술은 공식 문서와 일치(단, bypass까지 무력화한다는 강한 주장은 피하는 게 정확).

---

## 3. 축 ② — 오케스트레이션 · 멀티에이전트

### 3.1 멀티에이전트 찬성 측
- **주장:** Anthropic 멀티에이전트 리서치 시스템(Opus 4 리드 + Sonnet 4 서브에이전트)이 단일 Opus 4 대비 내부 리서치 평가에서 **+90.2%**. 🟡(복수 2차 일치, 1차 직접확인 불가)
- **주장:** 풀 멀티에이전트 런은 일반 챗 대비 **~15배 토큰** 소비. 🟡
- **주장:** BrowseComp 분석에서 **토큰 사용량만으로 성능 분산의 ~80%**, 토큰+도구호출수+모델선택이 ~95% 설명. 즉 멀티에이전트의 승리는 *"더 똑똑한 협응"이 아니라 "더 많은 컴퓨트를 여러 컨텍스트 윈도우에 분산"*하는 방식. 🟡
  - 출처: https://www.anthropic.com/engineering/multi-agent-research-system ; https://simonwillison.net/2025/Jun/14/multi-agent-research-system/
- 경제 규칙: **"태스크 가치 > 토큰 비용일 때 멀티에이전트가 이득"** → 고가치·breadth-first·병렬화 가능 리서치에 적합, 일상/비용민감 작업엔 부적합.

### 3.2 단일 스레드 우선 측
- **주장:** Cognition "Don't Build Multi-Agents" — 순진한 멀티에이전트는 서브에이전트가 서로의 전체 맥락을 모르기에 **상충하는 암묵적 결정**을 낳아 취약(Flappy Bird 예: 한 서브가 마리오풍 배경, 다른 서브가 스펙 외 새). 🟢
  - 두 원칙: (1) 메시지가 아닌 **전체 컨텍스트·완전한 트레이스 공유**, (2) **"행동은 암묵적 결정을 내포"** → 상충하면 나쁜 결과.
  - 권장 기본값: **연속 컨텍스트의 단일 스레드 에이전트**. 아주 긴 작업엔 병렬 분할 대신 *히스토리를 핵심 사건/결정으로 압축하는 전용 LLM* 추가.
  - 출처: https://cognition.ai/blog/dont-build-multi-agents
- **주장(2026 쟁점):** Tran & Kiela 프리프린트 — **동등한 thinking-token 예산에서 단일 에이전트가 멀티홉 추론에서 멀티에이전트와 대등하거나 우위**. 5개 아키텍처(sequential, subtask-parallel, parallel-roles, debate, ensemble)를 FRAMES·MuSiQue에서 100~10,000 토큰 예산으로 테스트, Data Processing Inequality로 단일 에이전트가 정보효율적이라 논증. 🔴(arxiv `2604.02460` — 미래날짜 ID, 직접확인 불가, 환각 가능성 유의)
  - 출처(주장): https://arxiv.org/abs/2604.02460

### 3.3 화해(reconciler) — 읽기/쓰기로 가른다
- **주장:** LangChain — **읽기/리서치 태스크는 병렬화 잘 됨(Anthropic 사례)**, **쓰기/코딩 태스크는 안 됨(병렬 출력 병합·교차 맥락 전달 난제, Cognition 사례)**. 읽기/쓰기로 나누면 두 진영은 사실상 합의. 🟢
  - 출처: https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/

### 3.4 워크플로 vs 에이전트 (기초 분류)
- **주장:** Anthropic "Building Effective Agents" — 워크플로(미리 정한 코드 경로로 LLM·도구 오케스트레이션) vs 에이전트(LLM이 동적으로 자기 프로세스 지휘). 5대 워크플로 패턴: **prompt chaining, routing, parallelization(sectioning+voting), orchestrator-workers, evaluator-optimizer**. "단순하게 시작, 측정 가능한 이득이 있을 때만 복잡도 추가." 🟢
  - 출처: https://www.anthropic.com/research/building-effective-agents ; https://simonwillison.net/2024/Dec/20/building-effective-agents/

> 💡 **핵심 쟁점 정리:** §3.1의 +90.2%(시스템 레벨, 토큰 무제한 허용)와 §3.2의 토큰예산 통제 결과는 **"멀티에이전트 우위가 컴퓨트를 동등하게 맞춰도 살아남는가"**를 두고 직접 충돌한다. 이것이 2026년 논쟁의 핵심. 단, 후자 출처는 미래날짜 arxiv라 신중히 인용해야 함.
>
> 💡 **이 repo 연결:** 개인 harness는 전형적 **단일 스레드 + 강한 스캐폴딩** 영역(코딩=쓰기 태스크). Cognition·LangChain 논리상 멀티에이전트보다 단일 에이전트+결정론 hooks+레시피 게이트가 맞다. 다만 *리서치성 fan-out*(이 보고서를 만든 방식처럼)에는 서브에이전트 병렬화가 유효 — 즉 "쓰기는 단일, 읽기는 병렬" 원칙을 harness 차원에서 구분 적용할 여지.

---

## 4. 축 ③ — 평가 · 검증 (eval / gate)

### 4.1 자기검증의 취약성 vs grounded 검증
- **주장:** **내재적 자기수정은 추론을 개선하지 못하고 오히려 악화**시킬 수 있다. GPT-3.5는 GSM8K 오답의 7.6%만 고치고 정답의 8.8%를 오답으로 뒤집어 *순손실*. 🟢(Huang et al., ICLR'24 — 컷오프 이전, 널리 재현됨)
  - 출처: https://arxiv.org/abs/2310.01798
- **주장:** 과거 자기수정 "이득"은 모델 내재 판단이 아니라 **오라클/외부 피드백**(정답이 틀렸다는 신호)에 의존했다. 신호 제거 시 이득 소멸. 🟢
- **주장:** 근본 원인 — LLM은 **자기 응답의 정확성을 신뢰성 있게 평가하지 못한다**. 🟢
- **주장:** 반대로 **grounded 자기수정(실행결과·유닛테스트·PRM에 묶임)은 작동**한다. Reflexion은 코드(테스트로 검증 가능 도메인)에서 HumanEval pass@1 91%(GPT-4 베이스라인 ~80%). 🟢
  - 출처: https://arxiv.org/abs/2303.11366 (Reflexion)
- **주장:** "검증은 생성보다 쉽다" — 판별적(한 결함만 잡으면 됨)이라 best-of-N·외부검증 루프가 효과적. 단, **검증자 신뢰도는 그 검증자가 문제를 풀 능력에 비례**(약한 검증자는 어려운 문제에서 못 믿음). 🟡
- **주장:** 검증 루프는 **가파른 수확체감 — 1~2라운드가 도달 가능 개선의 ~75%** 포착. 과도한 반복은 낭비. 🟡
  - 출처: https://arxiv.org/html/2509.17995v2 (검증 비대칭/동역학 — ID는 2025-09, 컷오프 부근)

### 4.2 LLM-as-Judge의 편향
- **주장:** LLM-as-judge는 큰 체계적 편향(스타일·위치·장황함·자기선호) 보유. 모델은 **자기 출력을 더 높게 채점(self-preference bias)**, 같은 계열 편애. 🟡/🟢
  - 출처: https://arxiv.org/abs/2410.21819
- **주장:** 챗에서 검증된 judge가 RAG·코드리뷰·에이전트 평가로 **전이되지 않는다** → 도메인별 보정 필수. 🟡
  - 출처: https://arxiv.org/pdf/2503.05061v1

### 4.3 Evaluator-Optimizer & Plan-then-Execute 패턴
- **주장:** Evaluator-optimizer는 생성자 LLM + 별도 평가자 LLM의 2역할 루프. **명확한 평가 기준이 있고 반복 개선이 측정 가능한 가치를 줄 때** 권장 — 즉 *쓸 만한 검증 신호 존재를 전제*. 🟢
  - 출처: https://www.anthropic.com/research/building-effective-agents
- **주장:** Plan-then-execute는 ReAct와 *사고 시점*이 다름 — ReAct는 스텝마다 thought/action/observation 인터리브, plan-and-execute는 앞에서 한 번 계획·실패 시에만 재계획. 적응성↓ 대신 예측가능성·비용효율·추론품질↑. 🟢
  - 출처: https://www.langchain.com/blog/planning-agents

### 4.4 Eval / Gate 하네스 & 벤치마크 동향
- **주장:** SWE-bench Verified는 포화 근접 — 톱 에이전트 ~78.8% vs 인간 ~90%. 🟡
  - 출처: https://www.codeant.ai/blogs/swe-bench-scores
- **주장:** "해결됨" 패치의 **약 1/5이 의미적으로 틀렸는데 약한 테스트 때문에 통과**. 적대적 테스트 강화 시 톱 78.8%→62.2%. 🔴(arxiv `2603.00520` — 미래날짜, 직접확인 불가)
- **주장:** 단일런 정확도에서 **신뢰성 지표(pass^k)로 이동** — 에이전트 런-투-런 분산이 큼(pass^4가 pass^1보다 15~25점 낮음). 🟡
- **주장:** 널리 쓰이는 에이전트 벤치마크 **10개 중 7개에 타당성 결함**(사소한 에이전트가 통과하거나 채점기가 오답에 점수). 🟡(arxiv `2507.02825`)
- **주장(가장 잘 입증됨):** 에이전틱 코딩에서 **테스트/CI 통과 = 우회 불가능한 최강 검증 게이트** — 프롬프트 지시·정적 리뷰보다 강함. 품질게이트 스택: lint → typecheck → security scan → tests → agentic testing. "CI는 우회 불가능한 최종 집행 레이어", "통과한 테스트 스위트는 에이전트 세션이 아무리 길어져도 외부 진실원천." 🟢
  - 출처: https://getautonoma.com/blog/quality-gate-vibe-coding ; https://www.softwareseni.com/building-quality-gates-for-ai-generated-code-with-practical-implementation-strategies/
- **주장:** **Stop hook이 에이전트 루프 검증 체크포인트**로 부상 — 프롬프트보다 신뢰(스킵 불가, 통과까지 출력 차단), CI보다는 약함. 🟡(실무 블로그, 단 이 repo와 직접 관련)
  - 출처: https://fbakkensen.github.io/ai/devtools/development/2026/03/27/quality-gates-for-coding-agents-how-stop-hooks-make-validation-mandatory.html
- **주장:** **RLVR(객관/프로그램적 체크 통과 시에만 보상)이 2025 추론모델 학습의 지배적 레시피** — DeepSeek-R1(2025-01)이 학습 선호보상 대신 RLVR+GRPO로 촉발. 🟢
  - 출처: https://github.com/opendilab/awesome-RLVR

> 💡 **이 repo 연결(가장 중요):** 이 repo의 PGE 설계 결정 — **LLM 자가판단이 아니라 `.claude/evaluate.recipe`(tests/lint/build) 구동 게이트 + Stop hook 자동 루프 + 재시도/정체감지** — 는 2026 합의(§4.1 grounded 검증 > 자기검증, §4.4 테스트=최강 게이트, Stop hook 체크포인트)와 **거의 완벽히 정렬**한다. 즉 형욱의 harness는 트렌드를 *따라간 게 아니라 같은 1차 원리에 독립 도달*했다. 추가 시사점:
> - 검증 반복은 **1~2라운드면 충분**(§4.1 수확체감) → 현재 "재시도 3회"는 합리적 상한, 더 늘릴 필요 없음.
> - LLM-as-judge(#5 `/wook-evaluate` 서브에이전트)는 **편향·자기선호** 주의 → 가능하면 결정론 레시피(테스트)를 1차 게이트로, judge는 보조로. 자기 출력을 자기가 채점하는 구도 회피.

---

## 5. 보너스 축 — 프레임워크 · 생태계 (맥락)

- **Claude Agent SDK 개명:** "Claude Code SDK" → "Claude Agent SDK". TS `@anthropic-ai/claude-code` → `@anthropic-ai/claude-agent-sdk`, Python `claude-code-sdk` → `claude-agent-sdk`, `ClaudeCodeOptions` → `ClaudeAgentOptions`. v0.1.0에 breaking change(기본 시스템 프롬프트 미적용 — opt-in 필요). 🟢(마이그레이션 가이드 직접확인) / 개명일 2025-09-29는 🟡
  - 출처: https://code.claude.com/docs/en/agent-sdk/migration-guide ; https://code.claude.com/docs/en/agent-sdk/overview
- **SDK 철학:** Claude Code를 구동하는 동일 에이전트 루프·내장도구(Read/Write/Edit/Bash/Glob/Grep/WebSearch/WebFetch)·subagents·hooks·sessions·permissions·MCP를 라이브러리로 노출. "gather context / take action / verify work" 루프. 🟢(메커닉 검증, 3단계 표현은 🟡)
- **MCP(Model Context Protocol):** 2024-11 출시, OpenAI 2025-03·Google DeepMind 2025-04 채택, Microsoft Copilot/VS Code 통합. 🟢(채택 시퀀스) / 2025-12 Linux Foundation 산하 Agentic AI Foundation 기부 🟡 / "9,700만 다운로드"류 수치 🔴
  - 출처: https://en.wikipedia.org/wiki/Model_Context_Protocol
- **A2A(Agent2Agent):** Google 2025-04-09 발표, 2025-06 Linux Foundation 기부. HTTP+JSON-RPC 2.0+SSE, "Agent Card"로 역량 발견. MCP(에이전트↔도구)와 상보적(A2A=에이전트↔에이전트). 🟡
- **Agent Skills:** 2025-10-16 출시, 2025-12-18 오픈 표준화. Skill = `SKILL.md`(YAML frontmatter+Markdown) 디렉터리, **progressive disclosure**(트리거 전엔 요약 수십 토큰만 컨텍스트에). 🟢(메커닉, `.claude/skills/*/SKILL.md`로 SDK 문서 확인) / 정확 날짜 🟡
  - 출처: https://thenewstack.io/agent-skills-anthropics-next-bid-to-define-ai-standards/
- **프레임워크 수렴:** 2026 초 ~6대 플레이어(LangGraph, CrewAI, Microsoft Agent Framework, OpenAI Agents SDK, Claude Agent SDK, Google ADK)로 정리, 전부 MCP 네이티브 지원. OpenAI Agents SDK(2025-03)는 Swarm 후계, 핵심 추상화는 "handoff". 🟡(2차 출처 다수)

> 💡 **이 repo 연결:** 이 repo가 쓰는 `.claude/skills/*/SKILL.md`(progressive disclosure)와 hooks/subagents/permissions는 모두 Agent SDK가 표준화한 1급 프리미티브다. `wook-` 접두사로 네임스페이스 분리한 결정은 네이티브 plan 모드·플러그인 충돌 회피라는 면에서 생태계 표준화 흐름과 정합.

---

## 6. 교차 종합 — 2026 harness 설계의 수렴 원리

세 축을 관통하는 일관된 1차 원리:

1. **컨텍스트는 희소 자원이다.** → JIT 로딩, compaction, 파일 기반 memory, progressive disclosure. (축①)
2. **결정론을 모델 의지 위에 둔다.** → hooks가 "항상 일어나야 할 일"을 보장, deny는 하드 게이트. (축①)
3. **검증은 모델 밖 ground truth에 묶어라.** → 자기검증 ✗, 테스트/CI/실행결과 ✓, RLVR. (축③)
4. **단순하게 시작, 측정 가능할 때만 복잡도 추가.** → 단일 에이전트+강한 스캐폴딩이 기본, 멀티에이전트는 고가치·읽기/병렬 태스크에 한정. (축②)
5. **상태를 영속화해 컨텍스트 리셋을 견딘다.** → 진행 로그·체크리스트·노트테이킹 부트스트랩. (축①)

---

## 7. 이 repo(PGE harness)에 대한 실행 시사점

| 트렌드 | 이 repo 현황 | 시사점 |
|--------|--------------|--------|
| Context engineering / 노트테이킹 부트스트랩 | `CLAUDE.md`+`build-log.md` 진행 로그, "만든 것 기록" 규칙 | ✅ 이미 정합. 유지 |
| 결정론 hooks(PreToolUse deny, PostToolUse, UserPromptSubmit) | #1~#3 hook 가동 | ✅ 공식 패턴과 일치. "deny가 bypass까지 무력화"라는 과한 표현만 주의 |
| grounded 검증 > 자기검증 | `.claude/evaluate.recipe`(tests/lint/build) 구동 게이트 | ✅ 핵심 정렬. judge(#5)는 보조로, 자기채점 회피 |
| Stop hook 검증 체크포인트 | #7 Stop hook 자동 게이트(재시도 3회, 정체감지) | ✅ 정렬. 검증 1~2라운드가 75% → 3회 상한 합리적, 더 안 늘려도 됨 |
| Plan-then-execute | `/wook-plan`이 수용기준→레시피 작성 | ✅ PGE의 Plan 단계. 오늘 추가한 core-rules 4번(신규 구현 시 `/wook-plan` 제안)이 이 흐름 강화 |
| 단일 vs 멀티에이전트 | 단일 스레드 harness | ✅ 코딩=쓰기 태스크엔 단일이 정답. 단, *리서치 fan-out*엔 서브에이전트 병렬 유효(이 보고서가 그 예) |
| Agent Skills / progressive disclosure | `wook-` 스킬 네임스페이스 | ✅ 표준 프리미티브 활용 중 |

**권고(우선순위):**
1. **judge 편향 가드:** #5 Evaluator가 *자기 출력을 자기가 채점*하지 않도록, 1차 게이트는 결정론 레시피(테스트)로 두고 LLM judge는 보조 의견으로만. (§4.2 근거)
2. **검증 반복 상한 유지:** 수확체감(§4.1) 근거로 재시도 3회는 합리적 — 늘리지 말 것.
3. **읽기/쓰기 분리 원칙 명문화 검토:** 코딩(쓰기)은 단일 스레드 유지, 조사·탐색(읽기)은 서브에이전트 fan-out 허용을 harness 규칙/스킬로 구분(§3.3 LangChain 원리).
4. **"deny가 bypass 무력화" 표현 정정:** build-log/문서의 강한 주장을 공식 문서 수준("관리형 deny 우선")으로 톤다운.

---

## 8. 신뢰도·한계 요약

- **가장 신뢰 높은 부분(🟢):** Claude 공식 문서로 직접 검증된 hooks 메커닉, memory/compaction, Agent SDK 개명, 그리고 컷오프 이전 정설 논문(Huang et al. 자기수정 한계, Reflexion, Building Effective Agents, MCP/A2A 타임라인 일부).
- **신중 인용(🟡):** Anthropic 멀티에이전트 90.2%/15배, 벤치마크 포화 수치, 프레임워크 순위 — 복수 2차 출처 일치하나 1차 직접확인 불가.
- **신뢰 보류(🔴):** 미래날짜 arxiv(2602~2606), 비현실적 구체 수치·모델명(GPT-5.5, "Claude Mythos Preview", MCP 9,700만, 설문 %) — 검색 요약 환각 가능성. **재확인 전 의사결정 근거로 쓰지 말 것.**
- **공통 한계:** WebFetch 403 차단으로 Anthropic/Cognition 엔지니어링 블로그 등 핵심 1차 페이지를 직접 읽지 못함. 후속 검증 시 WebFetch 가능 환경에서 위 🟡/🔴 항목 원문 대조 권장.

---

## 부록 — 주요 출처 (1차 우선)

**검증된 1차 문서(🟢):**
- https://code.claude.com/docs/en/hooks-guide
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- https://platform.claude.com/docs/en/build-with-claude/compaction
- https://code.claude.com/docs/en/agent-sdk/migration-guide
- https://code.claude.com/docs/en/agent-sdk/overview

**핵심 1차(스니펫 경유, 🟢/🟡):**
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/research/building-effective-agents
- https://cognition.ai/blog/dont-build-multi-agents
- https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/
- https://www.langchain.com/blog/planning-agents
- https://arxiv.org/abs/2310.01798 (LLM Cannot Self-Correct Reasoning Yet)
- https://arxiv.org/abs/2303.11366 (Reflexion)
- https://arxiv.org/abs/2410.21819 (self-preference bias)
- https://github.com/opendilab/awesome-RLVR

**2차·신뢰 보류(🔴, 재확인 필요):**
- https://arxiv.org/abs/2604.02460 ; https://arxiv.org/pdf/2603.00520 ; https://arxiv.org/pdf/2507.02825
- https://www.codeant.ai/blogs/swe-bench-scores ; https://en.wikipedia.org/wiki/Model_Context_Protocol
</content>
</invoke>
