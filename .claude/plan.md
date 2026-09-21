# .claude/plan.md — 현재 플랜만 (in-flight)

> 진행 중인 플랜 하나만 담는다. `/wook-plan`이 새 플랜을 쓸 때 덮어쓴다(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`.

---

# SPEC — Claude-only 정렬 2/4: 포인터 훅 2개 → `.claude/rules/` (#31, 승인: 2026-09-21)

## 이 단계에서 **하지 않기로 한 것** (조사 결과에 따른 계획 수정)
원래 2-a였던 "`guard_paths` 훅 → `permissions` 규칙 교체"는 **취소**. 근거였던 "네이티브 deny가
bypass에서도 유지된다"가 내 오독이었고(그 문장은 샌드박싱 절), 공식 문서는 반대다:
- 훅: "`PreToolUse` hooks fire before any permission-mode check, in every permission mode…
  deny **blocks the tool even in `bypassPermissions` mode or with `--dangerously-skip-permissions`**"
- bypass 모드: "skips permission prompts, **including for writes to protected paths such as
  `.git` and `.claude`**"
→ 훅이 더 단단한 바닥이고, Bash(`cat`/`sed`/`tee`/리다이렉트) 경로로 키·`.git`을 건드린 실패는
**관측된 적 없음** → Ratchet(실패 뒤에만 규칙 추가) 위반 회피. `guard_paths`·`guard_bash` 불변.

## Scope — IN
1. `claude/hooks/inject_reuse_pointer.py`·`inject_convention_pointer.py` **삭제** +
   `claude/settings.hooks.json`의 `UserPromptSubmit` 등록 제거(→ `inject_plan_pointer` 1개만)
2. 대체 운반체: `claude/harness/rules.catalog.example` 신설 — 프로젝트의
   `.claude/rules/harness-catalog.md`로 복사될 템플릿(도메인 목록 포함).
   `paths:` 프런트매터 없음 → **세션 시작 시 1회 로드**(`.claude/CLAUDE.md`와 동일 우선순위)
3. 카탈로그를 만드는 스킬 3개가 그 파일도 쓰도록: `wook-conventions`·`wook-index`·`wook-onboard`
4. `tools/test_conventions.py`: "Test 2 — pointer inject hook" 제거(훅이 사라짐), `INJECT` 상수 제거.
   Test 3(스테일 포인터 = 게이트 경고)·Test 4(컨벤션 규칙 = 게이트 강제)는 **유지**
5. 문서: README §4 "읽는 곳" 열, §5 훅 표에서 2행 제거 / build-log #31

## Scope — OUT
`guard_paths`·`guard_bash`·`permissions` 일체 ✗(위 사유) / `inject_plan_pointer` ✗(in-flight 내용은
동적이라 rules로 못 나름) / `paths:` 스코프 rules ✗(실패 관측 전엔 과설계) / deploy의 stale 파일
정리(prune) ✗(별건 — 삭제 로직은 위험, 후속 판단) / 3·4단계 ✗

## 근거 (왜 이건 해도 되나)
`claude/harness/core-rules.md`(→ `~/.claude/CLAUDE.md`, 모든 세션 상시 로드)가 **이미**
"재사용 카탈로그가 있으면 먼저 확인" / "컨벤션 도메인 문서를 따르고 최신 유지"를 담고 있다.
두 훅이 매 턴 추가로 주는 정보는 **도메인 목록 + 상대경로뿐** → 세션당 1회 로드되는 rules 파일로
동일 정보를 0 비용에 전달 가능. 매 턴 파이썬 프로세스 2개 spawn 제거.

## Edge cases
- 훅 파일 삭제는 게이트 자기보호 대상 아님(`D` + 테스트 파일만) → `GATE_EDIT_OK` 불필요.
  `test_conventions.py`는 **편집(M)**이라 역시 불필요
- `selfcheck`는 "등록된 훅의 스크립트가 실재하는가"를 보므로 등록·파일을 **같이** 지워야 통과
- 배포된 `~/.claude/hooks/inject_*_pointer.py`는 deploy가 지우지 않아 잔류하지만 **미등록 = 비활성**
  (무해). 기존 프로젝트는 rules 파일이 없어도 CLAUDE.md 규칙으로 graceful degrade
- rules 파일은 **프로젝트 스코프**(`.claude/rules/`) — 사용자 스코프(`~/.claude/rules/`) 아님

## 수용 기준 (Acceptance criteria)
recipe 불변(`selfcheck`/`tests`/`deploy --check` 전부 exit 0). 나머지는 전부 원샷 명령:
- `git grep -l 'inject_reuse_pointer\|inject_convention_pointer' -- ':!docs/' ':!.claude/plan.md'` → 출력 없음(exit 1)
- `claude/hooks/` 에 `inject_plan_pointer.py`만 남고 두 파일 부재(`test -e` 실패)
- `settings.hooks.json`의 `UserPromptSubmit` 훅 수 = **1**, 그 args가 `inject_plan_pointer.py`
- `python -B tools/run_tests.py` → 10/10 파일 PASS (test_conventions 포함, Test 3·4 유지)
- `claude/harness/rules.catalog.example` 존재 + `python deploy.py --check` exit 0(배포 후 동기)
- 스킬 3개(`wook-conventions`/`wook-index`/`wook-onboard`) 본문에 `.claude/rules/harness-catalog.md` 등장
- 독립 평가자(`wook-evaluator`)가 위 항목 재실행해 PASS — **실거래는 worktree 금지, scratchpad `git clone` 사본에서**(#30 사고 재발 방지)
