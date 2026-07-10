# .claude/plan.md — 현재 플랜만 (in-flight)

> 이 파일은 **진행 중인 플랜 하나**만 담는다. `/wook-plan`이 새 플랜을 쓸 때 **덮어쓴다**(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`(결정 로그·기능 섹션)에 있다 — plan.md는 히스토리 보관소가 아니다.

---

# SPEC — 하네스 v2: 검증된 메커니즘으로 재배치 (승인: 2026-07-06)

2026 트렌드 감사(에이전트 18개 리서치) 결과 반영. 원칙: **손으로 만든 메커니즘을 같은
목적의 검증된/네이티브 메커니즘으로 교체**한다. 기능(게이트·규칙·가드)은 유지, 운반체 교체.

## Scope — IN

1. **게이트: PreToolUse Bash 파싱 → git 네이티브 pre-commit**
   - `claude/harness/gate_runner.py`(신규): recipe 실행 + 자기보호(staged에 recipe 변경/
     테스트 삭제 → GATE_EDIT_OK=1 없으면 실패) + stall 감지(같은 실패 3연속 → "중단하고
     사용자에게") + reuse/convention 포인터 신선도(경고만)
   - `claude/harness/install_gate.py`(신규): `.git/hooks/pre-commit` 쉼 설치(idempotent,
     남의 훅은 절대 덮지 않음). wook-plan/wook-onboard가 recipe 쓸 때 함께 설치
   - `gate_on_commit.py` 삭제 (모든 Bash 호출마다 돌던 300s 훅 제거)
2. **guard_bash.py**(신규, PreToolUse Bash|PowerShell): 파국 명령 → ask (rm -rf 홈/루트/
   드라이브루트/.., git push --force(-with-lease 제외), git reset --hard, git clean -f*,
   Remove-Item -Recurse -Force 홈/루트, rd /s, mkfs/dd of=/dev, 포크밤) + 게이트 우회 채널
   (pre-commit 삭제/덮어쓰기, evaluate-off 생성, recipe로의 리다이렉트/sed -i/tee) → ask.
   정책 레이어이지 보안 경계 아님(문서화). Windows엔 OS 샌드박스가 없어 hook이 바닥.
3. **core-rules → ~/.claude/CLAUDE.md 이사**: deploy.py가 marked block으로 렌더(블록 밖
   내용 보존). `inject_core_rules.py` 삭제 → 매 턴 ~700토큰 중복 주입 제거
4. **inject_plan_pointer.py**(신규, UserPromptSubmit): `.claude/plan.md` 존재 시 수용 기준
   섹션만 ~1500자 캡 주입 (planning-with-files 검증 패턴; compaction/긴 세션 생존)
5. **Stop 훅 3→1**: check_reuse/convention_pointers 삭제(게이트 러너로 이동),
   remind_evaluator만 유지
6. **guard_paths.py 확장**: `.claude/evaluate.recipe` Edit/Write, `evaluate-off` → **ask**
7. phaser4_reminder: repo 흡수 안 함(한 프로젝트 전용) — deploy 시 글로벌 등록 소실 수용,
   스크립트 파일은 ~/.claude/hooks에 잔존. 해당 프로젝트에서 프로젝트 로컬로 재설치 예정
8. 정비: `tools/run_tests.py`(전체 테스트 러너), selfcheck 갱신(harness/*.py 포함,
   settings→스크립트 존재 대조, pre-commit 미설치는 경고만), 신규 테스트 3벌, 문서 갱신

## Scope — OUT (명시적 제외)

스모크 프로브(probe.mjs)·스코프 glob 게이트(Phase 2) / guard_paths→permissions.deny 포팅,
TOFU 신뢰 스탬프, wook-loop(관찰·필요 시) / 카탈로그·컨벤션·맵 시스템 자체 변경 없음 /
v2.1.187+ 전용 기능(이 머신 2.1.169)

## Edge cases

pre-commit은 amend에도 돌고 merge commit엔 안 돎(수용) · git 없는 디렉토리에서 gate_runner는
cwd 기준 폴백(자기보호는 skip) · stall 카운터는 새 시그니처면 리셋, 성공 시 삭제
(`.git/wook-gate-state.json`) · recipe 신규 추가(A status)는 자기보호 미발동(게이트 켜는 행위)
· 게이트 러너는 ~/.claude 배포본 참조 → deploy 선행 필요 · 원격(클라우드) 세션엔 pre-commit
미설치 → 게이트 안 돎(기존 gate_on_commit도 동일했음, 회귀 아님)

## 수용 기준 (Acceptance criteria)

recipe(커밋 게이트가 강제):
- `selfcheck: python tools/selfcheck.py` exit 0
- `tests: python -B tools/run_tests.py` exit 0 — 아래 전부 tests에 포함:
  - gate_runner: 통과→0 / 실패→비0+체크명 / recipe 없음→0 / evaluate-off→0 /
    staged recipe 변경→차단+GATE_EDIT_OK 안내, GATE_EDIT_OK=1→통과 / 테스트 삭제→차단 /
    동일 실패 3회→stall 메시지 전환 / stale 포인터→경고만(exit 0)
  - guard_bash: 위험 명령→ask JSON, 안전 명령→무출력 exit 0
  - inject_plan_pointer: plan 있음→기준 포함+캡 / 없음→무출력
  - build_user_claude_md: 신규 생성·기존 블록 교체·블록 밖 보존·idempotent
- `deploy: python deploy.py --check` exit 0 (배포 후 동기)
- 실거래: 이 repo에서 실패 recipe로 `git commit` → pre-commit이 실제 차단(exit≠0),
  통과 상태로 커밋 성공 (독립 평가자가 확인)
- MANUAL: 세션 재시작 후 ~/.claude/CLAUDE.md 로드 + 매턴 standing-agreements 주입 소멸 확인
