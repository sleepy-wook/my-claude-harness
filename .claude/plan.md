# .claude/plan.md — 현재 플랜만 (in-flight)

> 진행 중인 플랜 하나만 담는다. `/wook-plan`이 새 플랜을 쓸 때 덮어쓴다(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`.

---

# SPEC — Claude-only 정렬 4/4: 마찰 제거 + #30 사고 근본원인 (#32, 승인: 2026-09-21)

3단계(측정 = `claude plugin eval`)는 **보류**(형욱 결정): CLI v2.1.269+ 필요 + 실행이 실제 모델
호출이라 형욱 머신/과금 몫. 여기서는 컨테이너에서 완결 가능한 4단계만 한다.

## Scope — IN
1. **`test_gate_runner.py`·`test_evaluator.py`가 `GIT_*`를 스크럽** — #30 사고의 진짜 원인.
   훅 환경에서 돌면 git이 `GIT_DIR`/`GIT_INDEX_FILE`을 export하는데, 테스트의 `git init`·게이트
   실행이 그걸 상속해 **임시 repo가 아니라 실제 repo를 조작**했다(→ `core.bare=true`, `[user] t@t`
   주입, 세션 stop-hook 파손). `clean_env()` 헬퍼로 `GIT_`로 시작하는 키를 전부 제거.
   **회귀 테스트 동반**: `GIT_DIR`을 심어둔 채 `repo()`가 여전히 자기 임시 repo를 만드는지 단언.
2. **`install_gate.py` → `--git-common-dir`** — linked worktree에서 `--git-dir`은
   `.git/worktrees/<n>`을 주고 git은 **그 위치의 훅을 실행하지 않는다**(평가자가 실증: 설치는
   성공했는데 발동한 건 메인 클론의 기존 훅이었음). 구 git 대비 `--git-dir` 폴백 유지.
3. **`SessionStart` 훅 `arm_gate.py` 신설** — recipe가 있는데 게이트가 없으면 자동 설치.
   관측된 실패: 이 컨테이너 클론에 `.claude/evaluate.recipe`가 **커밋돼 있는데도** 게이트가 없어
   초반 커밋들이 무검증으로 지나갔다(내가 수동 설치). "recipe 존재 = 게이트 ON" 원칙의 구멍.
   이미 우리 훅이면 **침묵**, 남의 pre-commit이면 install_gate가 거부(덮어쓰지 않음).
4. **`/wook-plan` 6단계에 `/goal` 한 줄** — 장기 작업이면 네이티브 `/goal <수용 기준>` 제안.
   게이트=커밋 시 결정론, `/goal`=매 턴 별도 소형 모델이 조건 판정·진전 없으면 정지. 보완 관계.

## Scope — OUT
- **junction/symlink 배포(원래 4-b) ✗** — 스킬 호출명이 `/wook:plan`류로 바뀌고 Windows 동작을
  여기서 검증 불가. drift는 `python deploy.py` 한 번으로 해소되는 문제라 이득 < 위험.
- `wook-evaluator`에 `maxTurns` ✗ — 관측된 실패 없음(Ratchet).
- deploy의 stale 파일 prune ✗ (삭제 로직 위험, 미등록 파일은 무해).
- 3단계(plugin eval / skill-doctor) ✗ — 보류.
- `guard_paths`/`guard_bash`/`permissions` ✗ — #31에서 확정한 대로 불변.

## Edge cases
- `arm_gate`는 **어떤 경우에도 세션을 막지 않는다**: 예외·git 없음·repo 아님 → 조용히 exit 0
- recipe 없는 프로젝트에선 완전 무출력(파일 존재 = ON 패턴)
- 남의 pre-commit 존재 → install_gate가 거부 메시지 반환 → 훅은 그 사유를 1회 알리고 exit 0
- `--git-common-dir`는 상대 경로(`.git`)를 줄 수 있음 → cwd 기준 resolve
- 새 훅은 `selfcheck`의 "등록된 훅 스크립트 실재" 검사 대상 → 등록·파일 동시 추가
- 새 테스트 파일은 인코딩 가드 대상 → `sys.stdout.reconfigure` 동반

## 수용 기준 (Acceptance criteria)
recipe 불변(`selfcheck`/`tests`/`deploy --check` 전부 exit 0). 나머지는 테스트/원샷 명령:
- `python -B tools/run_tests.py` → **11/11** 파일 PASS (신규 `test_arm_gate.py` 포함)
- `test_gate_runner.py`: `GIT_DIR`을 환경에 심은 채 `repo()`가 **자기 임시 repo**를 만든다(`<tmp>/.git` 존재)
- **스크럽이 한 파일에 반만 적용되는 걸 기계가 잡는다**(1차 평가 FAIL의 교훈 — 기준이 `test_gate_runner`만
  점검해 반쪽 수정이 통과했다): `selfcheck`의 `git-env` 가드가 `tools/test_*.py`에서 `env=` 없는 git
  spawn을 전부 적발. 검증법 = 아무 테스트의 `env=e`를 하나 지우면 `selfcheck`가 exit 1
- `env GIT_DIR=/tmp/bogus python -B tools/test_evaluator.py` → exit 0 이고 `/tmp/bogus`가 **생성되지 않음**
- `test_arm_gate.py`에 **실제 git 훅 환경 end-to-end**(실제 `git commit`으로 실패 recipe→차단, 통과 recipe→커밋)
- `grep -c 'git-common-dir' claude/harness/install_gate.py` ≥ 1
- `test_arm_gate.py`: ① recipe 있고 훅 없음 → 설치되고 `.git/hooks/pre-commit`에 마커 존재
  ② 이미 우리 훅 → 무출력(침묵) ③ recipe 없음 → 무출력 ④ 남의 훅 → 덮어쓰지 않음(내용 보존)
- `settings.hooks.json`에 `SessionStart` 등록 1개(`arm_gate.py`), 기존 4 이벤트 불변
- `grep -c '/goal' claude/skills/wook-plan/SKILL.md` ≥ 1
- 독립 평가자 PASS — **실거래는 worktree 금지, scratchpad `git clone` 사본에서**(#30 재발 방지)
