# 2026 AI Agent Harness 트렌드 — 심층 리서치 리포트 (Part 2: 확장 축)

> **조사일:** 2026-06-02
> **관계:** [`research-2026-agent-harness-trends.md`](./research-2026-agent-harness-trends.md)(Part 1)의 후속·확장.
> **신규 5축:** ④ 보안·안전 ⑤ 관측성·AgentOps ⑥ 경제성·지연·토큰효율 ⑦ 자율·장기실행·컴퓨터유즈 ⑧ 메모리 아키텍처(비-Anthropic·학술)
> **목적:** Part 1과 동일 — 이 repo(개인 Claude Code harness)의 **PGE(Plan-Generate-Evaluate) 루프** 설계 시사점.

---

## 0. 방법론·한계 (Part 1과 동일, 재확인)

- 5개 신규 각도로 병렬 리서치 에이전트 가동.
- **⚠️ WebFetch 거의 전면 차단(403):** 이번에도 1차 원문 직접 검증 실패. **유일한 예외**는 보안 각도에서 `raw.githubusercontent.com`의 **CoSAI/OASIS MCP 보안 문서 1건**(직접 fetch 성공, verbatim 인용 가능).
- **⚠️ 신뢰 보류 패턴 반복:** 미래날짜 arxiv ID(2601~2606), 벤더/에이전시 마케팅 수치(달러 비용, CAGR, 벤치마크 자체보고)는 *낮은 신뢰도*.
- **신뢰도 표기:** 🟢 높음 / 🟡 중간(복수 2차 일치) / 🔴 낮음(단일·미래날짜·마케팅·환각 의심).

---

## 1. Executive Summary (Part 2 핵심 6가지)

1. **프롬프트 인젝션은 "고칠 수 없고 가둬야 하는" 문제.** OWASP LLM01(최상위 위험), Simon Willison의 **"lethal trifecta"**(개인데이터 + 비신뢰 콘텐츠 + 유출경로 동시 = 취약)가 2026 보안 설계의 중심 프레임. 🟢
2. **에이전트 관측은 단일 호출 모니터링과 질적으로 다르다.** 실패가 **다단계 인과 사슬**에 나타나므로 trajectory(전 궤적) 캡처 필요. OpenTelemetry GenAI semconv(`invoke_agent`)가 표준화 중. 🟢
3. **컴퓨트 수확체감은 반복된 정량 발견.** 멀티에이전트는 ~15배 토큰, 테스트타임 스케일링은 ~3스텝 후 포화. → **반복·확장에 상한을 둬라.** 🟡
4. **장기 자율성의 적은 "복리 오류".** 스텝당 95% 신뢰도라도 20스텝이면 0.95²⁰≈36% 성공. METR: 자율 수행 가능 태스크 길이가 ~7개월마다 2배(단, 신뢰성은 능력보다 느리게 향상). 🟢/🟡
5. **프로덕션 합의: 결정론적 안티-런어웨이 가드 + 체크포인팅 + "durable execution".** max-turn/시간 상한, 반복 감지, 디스크 상태 저장 — 분산시스템 신뢰성 관행의 재발견. 🟡
6. **메모리는 파일/계층/그래프로 분화.** MemGPT/Letta(OS형 계층), Generative Agents(recency·importance·relevance), 시간형 지식그래프(Zep/Graphiti), 그리고 **벡터 vs 그래프 → 하이브리드 수렴**. 단, 벤더 벤치마크는 누가 돌리냐에 따라 승자가 뒤집힘. 🟡

---

## 2. 축 ④ — 보안 · 안전 harness

### 2.1 프롬프트 인젝션 & Lethal Trifecta
- **Lethal trifecta**(Simon Willison, 2025-06-16): ⓐ개인데이터 접근 + ⓑ비신뢰 콘텐츠 노출 + ⓒ유출 벡터를 *동시에* 가진 에이전트는, 모델 하드닝과 무관하게 인젝션으로 악용 가능. 🟢
  - https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- **OWASP 2025 LLM Top 10**: 프롬프트 인젝션이 **LLM01(최상위)**, 그중 *간접(indirect)* 인젝션이 가장 위험(공격면이 앱 경계 밖). 🟢
  - https://genai.owasp.org/llm-top-10/
- 주요 벤더(OpenAI·Anthropic·Google DeepMind)는 2025년 *"현 아키텍처에서 프롬프트 인젝션을 완전히 풀 수 없다 → 봉쇄(containment) 문제"*로 입장 정리. 🟡
- **CaMeL**(Google DeepMind, 2025-03): 도구 호출 가능한 *권한(privileged) LLM*과 비신뢰 콘텐츠만 처리하고 도구는 못 부르는 *격리(quarantined) LLM*으로 분리해 설계 차원 방어. 🟡
- 실제 사고: **EchoLeak(CVE-2025-32711)** — M365 Copilot 제로클릭 데이터 유출(간접 인젝션). 🟡(인용 전 NVD 확인 권장)
  - https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks

### 2.2 MCP / 도구 중독(tool poisoning)
- **MCP tool poisoning**: 도구 설명/메타데이터(`tools/list`로 전달)에 악성 지시를 심어 모델은 읽지만 사용자는 못 본다. **MCP 스펙 자체**가 "도구 동작 설명은 신뢰된 서버에서 온 게 아니면 *비신뢰로 간주*해야 한다"고 명시. 🟢 **(CoSAI/OASIS 문서 직접 fetch로 verbatim 검증 — 이번 2차 조사에서 유일하게 1차 확인된 출처)**
  - https://raw.githubusercontent.com/cosai-oasis/ws4-secure-design-agentic-systems/main/model-context-protocol-security.md
- Invariant Labs 데모: 악성 MCP 서버가 정상 whatsapp-mcp와 같은 세션에서 WhatsApp 전체 이력 유출. 🟡
- 완화책(CoSAI 문서, 검증됨): SPIFFE/SPIRE 신원, OAuth 세분 스코프, TEE/원격증명, stdio 전송(DNS rebinding 회피), 코드서명+SBOM, **HITL(단, 승인 피로 주의)**.

### 2.3 샌드박싱 & HITL
- OWASP Agentic AI: *"엄격한 샌드박싱·입력검증·allowlisting 없이 에이전트 생성 코드를 실행하지 말라"* — 격리 컨테이너 + 네트워크 차단 + 최소 권한. 🟡
- 실무 합의: **컨테이너(plain Docker)만으로는 비신뢰 코드에 불충분** → microVM(Firecracker)·gVisor 등 하드웨어급 격리 + **deny-by-default 이그레스 + API allowlist** 추가(defense-in-depth). 🟡(단 벤더 블로그 다수)
  - ⚠️ **이견:** "Docker로 충분한가"는 출처별 충돌. microVM 판매사는 부족하다, OWASP는 "네트워크 없는 격리 컨테이너"면 수용 가능.
- **HITL 규율**: 승인 게이트는 *고위험·저신뢰·되돌릴 수 없는* 행동(금융거래·데이터삭제·프로덕션 설정변경)에만 한정. LangGraph `interrupt()`, OpenAI Agents SDK가 pause/resume 승인 네이티브 지원. 🟢
  - ⚠️ **내장 긴장:** 게이트↑ = 안전↑ 그러나 **승인 피로** → 주의력↓ (CoSAI 문서가 명시적으로 경고).
- 가드레일 프레임워크: Meta **LlamaFirewall**(2025-05, PromptGuard/AlignmentCheck/CodeShield), NVIDIA **NeMo Guardrails**(Colang DSL로 허용 흐름을 상태머신화). 🟡

> 💡 **이 repo 연결:** ① **#3 PreToolUse deny 가드 = 최소권한·보호경로 봉쇄**의 경량 구현 — lethal trifecta의 'ⓒ유출 벡터' 차단 관점에서 정합. ② 이 harness는 **로컬 단일 사용자**라 trifecta 위험은 제한적이나, MCP 서버(이 세션에도 다수 연결)를 붙일 때 *tool poisoning*이 실질 위협 → 신뢰된 MCP만, 도구 설명 비신뢰 간주. ③ HITL 규율은 이 repo 철학("불확실하면 멈추고 확인")과 동형 — 단 "승인 피로"를 피하려 *결정론 게이트(테스트)는 자동, 사람 승인은 고위험에만*으로 계층화하는 게 정답.

---

## 3. 축 ⑤ — 관측성 · AgentOps

- **OpenTelemetry GenAI semconv**: 에이전트 스팬 `gen_ai.operation.name` = `invoke_agent`/`create_agent`(아직 Experimental). 주요 클라우드/벤더(Google·AWS·Azure·Datadog) 채택. 🟢
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/
- **오픈소스 셀프호스트 관측**: Arize **Phoenix**(OTLP 네이티브, OpenInference), **Langfuse**(Docker/K8s 셀프호스트). 🟢
- **에이전트 관측 ≠ 단일 호출 모니터링**: 실패가 다단계 인과 사슬에 나타나 **전 세션/궤적 캡처** 필요. 🟢
- **Trajectory 평가**: 도구호출 전 시퀀스에 LLM-as-judge 적용해 루프·불필요 스텝 탐지. 🟡 (단 §4.2 judge 신뢰성 한계와 충돌)
- **Eval-in-the-loop**: 프로덕션 트래픽을 *지속 확장 테스트셋*으로 취급 — 실패 트레이스를 회귀/eval 데이터셋으로 자동 큐레이션, CI/CD에서 실행. 🟡(벤더 자기서술)
- **2026 지배적 실패 모드 = 런타임 입력 드리프트**(사용자 행동·도구생태계·상류 데이터 변화) — 스팬은 200 OK인데 **조용히 성능 저하**. 🟡
- **MAST**(UC Berkeley/IBM) 멀티에이전트 실패 분류: **14개 실패모드 / 3범주**(≈41.8% 명세·설계, 36.9% 에이전트 간 불일치, **23.5% 검증**), 7개 프레임워크 트레이스, κ=0.88. 🟢(구조)/🟡(정확 수치·트레이스 수 150 vs 200 출처 불일치)
  - https://arxiv.org/abs/2503.13657
- **복리/연쇄 오류**가 핵심 난제 → 모듈 단위 근본원인 귀속(AgentDebug: memory/reflection/planning/action 4모듈). 🟡

> 💡 **이 repo 연결:** ① `docs/build-log.md`는 사실상 *수작업 trajectory/결정 로그* — 관측성의 원시 형태. 향후 hook으로 **세션 이벤트 구조화 로깅**(OTel 스타일)을 추가하면 자기관측 강화 가능. ② **MAST의 '검증(verification)' 범주 23.5%**는 이 repo의 evaluate 게이트 존재 이유를 정량적으로 뒷받침 — 실패의 1/4이 검증 부재에서 옴. ③ "조용한 성능 저하"는 *결정론 게이트가 통과해도* 발생 가능 → 레시피를 주기적으로 갱신/강화해야(테스트 약화 주의, Part 1 §4.4의 'SWE-bench 1/5 가짜 통과'와 연결).

---

## 4. 축 ⑥ — 경제성 · 지연 · 토큰효율

- 멀티에이전트 ~**15배 토큰**(Part 1 재확인), 토큰 사용량이 성능 분산의 ~80% 설명 → "더 똑똑함"이 아니라 "더 많은 컴퓨트". 🟡
- **프롬프트 캐싱**: 입력비용 ~90%·지연 ~85% 절감(긴 프롬프트), 캐시 읽기 ≈ $0.30/M vs $3.00/M(Sonnet급). OpenAI는 ~50% 절감·자동 on. 🟡
- **모델 라우팅/캐스케이드**("작은 모델 먼저, 필요시 큰 모델로"): 비용 45~85% 절감하며 품질 ~95% 유지(업계 rule-of-thumb, 정밀 수치는 🔴). 🟡
- **병렬 도구 호출**: 지연이 *가장 느린 단일 호출* 수준으로 수렴(정성적으로 견고 🟢). 구체 배수(3.7배/6.7배/9%)는 🔴.
- **테스트타임 스케일링 수확체감**: 정확도가 ~**3 검색/스텝 후 포화**, 이후는 대부분 비용만 증가. 🟡
  - https://arxiv.org/html/2506.04301v1 ("The Cost of Dynamic Reasoning")
- **예산 인지(budget-aware) 스케일링**: Google 등이 "Budget Tracker"로 컴퓨트·도구 예산을 현명하게 소비. 🟡
- 엔터프라이즈 달러 수치($400~$13,000/월 등)는 에이전시 마케팅 — 🔴.
  - ⚠️ **경계조건(모순 아님):** 멀티에이전트(비싸지만 권장) vs 라우팅/반복상한(아껴라)은 **"태스크 가치 > 토큰 비용일 때만 비싸게"**로 화해.

> 💡 **이 repo 연결:** ① **수확체감(~3스텝 포화, Part 1의 검증 1~2라운드=75%)**이 또 확인 → #7 게이트 **재시도 3회 상한은 이론적으로도 적정**, 늘리지 말 것. ② 단일 스레드 harness는 멀티에이전트 대비 토큰 경제적 — 코딩(쓰기)엔 옳은 선택. ③ 프롬프트 캐싱은 이 repo가 직접 만들 건 아니지만, core-rules 재주입(#2)·CLAUDE.md 같은 **안정적 프리픽스는 캐시 친화적**으로 유지하면 비용 이득.

---

## 5. 축 ⑦ — 자율 · 장기실행 · 컴퓨터유즈

- **METR 시간지평(time horizon)**: 50% 신뢰도로 자율 수행 가능한 태스크 길이가 ~6년간 **~7개월마다 2배**. 🟢(주장·근사치)/🟡(정확 표현) — 단 도메인별 편차 큼.
  - https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/
- **에이전트 "반감기"**: 성공확률이 태스크 길이에 따라 *일정 스텝당 실패 위험률*로 감쇠. 🟡
- **복리 오류(검증 가능한 수학)**: 스텝당 95% × 20스텝 = 0.95²⁰ ≈ **36% 성공** → 장기 자율이 어려운 표준 논거. 🟢
- **신뢰성 < 능력**(Kapoor & Narayanan, "Towards a Science of AI Agent Reliability"): 신뢰성이 원raw 정확도보다 ~절반 속도로 향상. 🟡(Princeton CITP·Berkman Klein·Fortune 교차, 단 arxiv 2602 미래날짜)
- **컴퓨터유즈**: OpenAI CUA/Operator(2025-01, WebArena ~58.1%), OSWorld 인간 베이스라인 ~72.36%를 2025말~2026초 다수 에이전트가 근접/돌파. 🟡(모델명·구체점수는 🔴)
- **프로덕션 실패**: 파일럿 다수가 지속 운영에 도달 못함(수치는 12% vs 88% vs 95%로 출처별 충돌 🔴). **데모-투-프로덕션 격차**(깨끗한 입력·협조적 사용자가 실패모드 은폐)가 최대 이탈 원인. 🟡(정성)
- **안티-런어웨이 가드(프로덕션 표준)**: max-turn 상한, max-time 킬, **반복 감지(같은 행동 N회 시 중단)** — "유한 재시도 예산이 '무한 루프'를 '결정론적 실패'로 바꾼다." 🟡(패턴)/🔴(구체 임계치)
- **체크포인팅 + Durable Execution**: 중간 상태를 디스크에 저장(스텝 N 실패 시 처음부터 재시작 방지), 에이전트 워크플로를 *장기 서버 프로세스*처럼(멱등성 키, 유한 재시도) — 분산시스템 신뢰성의 재발견. 🟡

> 💡 **이 repo 연결(강함):** ① **#7 게이트의 '정체(stuck/progress) 감지'는 위 '반복 감지 안티-런어웨이 가드'와 정확히 동형** — 이 repo는 프로덕션 표준 패턴을 이미 구현. ② **복리 오류**는 강한 결정론 게이트의 정당성: 긴 세션일수록 끝의 검증(테스트 통과)이 누적 오류를 잡는 유일한 닻. ③ `build-log.md`/`plan.md`는 **체크포인트/상태 영속화**의 수작업 버전 — 컨텍스트 리셋·세션 재개를 견디게 함(Part 1 §2.3과 연결). ④ "데모-투-프로덕션 격차"의 교훈 = core-rules의 "완료=실행 결과로 증명"이 바로 그 격차를 메우는 규율.

---

## 6. 축 ⑧ — 메모리 아키텍처 (비-Anthropic · 학술)

- **MemGPT/Letta**: OS형 계층 메모리 — in-context "core" + out-of-context "recall"/"archival", LLM이 도구 호출로 계층 간 데이터 이동. 🟢
  - https://www.letta.com/blog/agent-memory (원논문 MemGPT arxiv 2310.08560)
- **Generative Agents**(Stanford, 2304.03442): 메모리 검색 = **recency + importance + relevance** 가중합, 주기적 **reflection**으로 상위 추론 합성·재저장. 🟢
- **Mem0**: LOCOMO에서 OpenAI 내장 메모리 대비 정확도 ↑·지연 ↓·토큰 ↓ 주장(벤더 자기보고 🟡).
- **Zep/Graphiti**: *시간형 지식그래프* — 시간이 1급 차원, 사실을 덮어쓰지 않고 타임스탬프로 무효화(옛 주소가 더는 안 뜸). 🟢(아키텍처)
- **벡터 vs 그래프 → 하이브리드 수렴**: 벡터만으로는 멀티홉/인과 질문 실패 → 벡터(시맨틱 진입점)+그래프(관계 깊이). 🟡(서술), "35% 향상"류 수치는 🔴.
  - ⚠️ **이견:** Mem0(LOCOMO) vs Zep(LongMemEval)는 **벤치마크에 따라 승자가 뒤집힘** — 둘 다 일부 자체평가. 신뢰 보류.
- **학술 분류 수렴**: episodic / semantic / procedural × (단기 vs 장기). ACT-R/SOAR 인지구조 영감(활성 감쇠·연상 확산·인간형 망각). 🟡
- **메모리 벤치마크 비판**: LOCOMO/LongMemEval이 *진짜 누적*이 아닌 얕은 교차세션 검색을 测정(예: LOCOMO 질문 94%가 ≤2 세션 근거 — 🔴 단일출처). 제안 역량: 정확 검색·테스트타임 학습·장거리 이해·선택적 망각. 🟡

> 💡 **이 repo 연결:** ① `CLAUDE.md`(인덱스) + `build-log.md`(서술 기억) = **파일 기반 메모리**(Anthropic memory tool 철학과 동형, Part 1 §2.3). Letta의 "filesystem is all you need" 류 입장과 부합 — 개인 harness엔 그래프/벡터 메모리는 과설계. ② 향후 확장 시 **procedural memory**(반복되는 작업 절차를 스킬/레시피로 추상화)가 자연스러운 방향 — 이미 `wook-` 스킬·`.claude/evaluate.recipe`가 그 맹아. ③ "선택적 망각/무효화"(Zep) 개념은 build-log가 비대해질 때 *오래된 결정 압축/아카이브* 규칙으로 차용 가능(Part 1 compaction과 연결).

---

## 7. 교차 종합 — Part 1+2 통합 원리

Part 1의 5원리에 Part 2가 더하는 것:

6. **봉쇄 > 완치(보안).** 인젝션은 못 고치니 trifecta를 깨고(최소권한·이그레스 차단·HITL), 비신뢰 입력(도구 설명 포함)을 격리하라.
7. **관측 없이는 신뢰 없음.** trajectory 캡처·eval-in-the-loop로 *조용한 저하*를 잡아라. 실패의 ~1/4은 검증 부재(MAST).
8. **컴퓨트엔 상한을, 상태엔 영속을.** 수확체감(~3스텝/1~2라운드)을 인정해 반복을 캡하고, 체크포인트로 복리 오류·리셋을 견뎌라.
9. **신뢰성은 능력과 별개로, 더 느리게 온다.** 데모-투-프로덕션 격차는 결정론 가드·실행 증명으로만 메운다.

---

## 8. 이 repo(PGE harness) 통합 시사점 — Part 2 추가 권고

| 신규 트렌드 | 이 repo 현황 | 권고(우선순위) |
|------------|--------------|----------------|
| 안티-런어웨이(반복/시간 상한) | #7 게이트 **정체 감지** 보유 | ✅ 이미 프로덕션 표준. 시간/턴 상한도 명시했는지 점검 |
| 컴퓨트 수확체감 | 재시도 3회 | ✅ 이론적 적정. **늘리지 말 것** |
| 검증 부재가 실패의 1/4(MAST) | evaluate 레시피 게이트 | ✅ 존재 정당성 입증. judge 자기채점만 회피 |
| MCP tool poisoning | MCP 서버 다수 연결 | ⚠️ **신뢰된 MCP만, 도구 설명 비신뢰 간주** — 새 권고 |
| HITL 고위험 한정 + 승인 피로 | "불확실하면 확인" 규칙 | 🔧 **계층화**: 결정론 게이트는 자동, 사람 승인은 고위험에만 |
| 구조화 관측/trajectory | build-log 수작업 | 🔧 (선택) 세션 이벤트 구조화 로깅 hook 검토 |
| procedural memory | wook-스킬·레시피 | ✅ 맹아 존재. 반복 절차를 스킬로 추상화 지속 |
| 캐시 친화 프리픽스 | core-rules 재주입·CLAUDE.md | 🔧 안정적 프리픽스 유지로 캐시 이득(저비용 개선) |

**새로 추가된 핵심 권고 2가지:**
1. **MCP 신뢰 경계 명문화** — 이 세션에도 다수 MCP 서버가 붙는 만큼, 도구 설명/메타데이터를 비신뢰로 간주하고 신뢰된 서버만 사용하는 규칙을 harness/문서에 박을 것. (§2.2, CoSAI 직접검증)
2. **승인 계층화** — 결정론 검증(테스트/lint/build)은 자동 게이트로, *사람 승인은 되돌릴 수 없는 고위험 행동에만* 한정해 승인 피로 방지. (§2.3)

---

## 9. 신뢰도·한계 요약 (Part 2)

- **🟢 직접검증(이번 2차 유일):** CoSAI/OASIS MCP 보안 문서(tool poisoning·완화책).
- **🟢 잘 정립(컷오프 이전/널리 교차):** lethal trifecta, OWASP LLM01, OTel GenAI semconv, MemGPT/Generative Agents/Zep 아키텍처, METR 시간지평·복리오류 수학, MAST 구조.
- **🟡 신중 인용:** 캐싱/라우팅 절감폭, OSWorld/CUA 점수, Kapoor&Narayanan 논지, eval-in-the-loop·입력드리프트.
- **🔴 신뢰 보류(재확인 필수):** 미래날짜 arxiv(2601~2606), 엔터프라이즈 달러/CAGR, 파일럿 실패율 충돌 수치, 구체 모델명("GPT-5.x", "Claude Cowork/Mythos"), 메모리 벤더 자체 벤치마크 단일수치.
- **공통:** WebFetch 403로 1차 검증 1건 외 불가 → 후속은 WebFetch 가능 환경에서 🟡/🔴 원문 대조 권장.

---

## 부록 — Part 2 주요 출처

**직접검증(🟢):**
- https://raw.githubusercontent.com/cosai-oasis/ws4-secure-design-agentic-systems/main/model-context-protocol-security.md

**잘 정립(🟢, 스니펫 경유):**
- https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- https://genai.owasp.org/llm-top-10/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/
- https://arxiv.org/abs/2503.13657 (MAST)
- https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/
- https://arxiv.org/abs/2304.03442 (Generative Agents) ; https://www.letta.com/blog/agent-memory (MemGPT)
- https://openai.github.io/openai-agents-python/human_in_the_loop/

**신중·보조(🟡):**
- https://arxiv.org/html/2506.04301v1 ; https://github.com/Arize-ai/phoenix ; https://langfuse.com/docs/observability/overview
- https://www.microsoft.com/.../how-microsoft-defends-against-indirect-prompt-injection-attacks
- https://arxiv.org/abs/2504.19413 (Mem0) ; https://vectorize.io/articles/mem0-vs-zep

**신뢰 보류(🔴, 재확인 필요):** 미래날짜 arxiv(2601~2606), 벤더 달러/벤치마크 수치, 파일럿 실패율, 구체 모델명.
</content>
