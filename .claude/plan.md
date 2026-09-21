# .claude/plan.md — 현재 플랜만 (in-flight)

> 이 파일은 **진행 중인 플랜 하나**만 담는다. `/wook-plan`이 새 플랜을 쓸 때 **덮어쓴다**(누적 X).
> 완료된 플랜의 영구 기록은 `docs/build-log.md`(결정 로그·기능 섹션)에 있다.

---

# SPEC — Claude-only 정렬 1/4: Codex 어댑터 삭제 (#30, 승인: 2026-09-21)

형욱: "Claude Code만 사용하니 Claude 쪽으로 맞춰도 된다 — 전부 진행, 하나씩." 4단계 중 첫 단계.
기능 손실 0인 **순수 제거**. 이어질 단계: 2) guard_paths→`permissions` 규칙·포인터 훅→`.claude/rules`,
3) `claude plugin eval`·`/skill-doctor` 측정, 4) SessionStart 게이트 자동설치·deploy 드리프트 종식.

## Scope — IN
1. `deploy.py`: `codex_text`·`build_codex_hooks_json`·`build_agents_md`·`build_evaluator_toml`·
   `_strip_frontmatter`·`deploy_codex`·`TARGETS`·`--target` 제거, `copy_tree`의 `transform` 분기 제거, 독스트링 정정
2. 훅/하네스: `guard_paths.py`(`.codex` 세그먼트·`tool_input["path"]` 폴백), `format_py.py`(`path` 폴백),
   `install_gate.py`(`~/.codex` 폴백), `gate_runner.py` 독스트링의 Codex 언급
3. 문서: README §"멀티 에이전트 — Codex도 지원" 삭제, `core-rules.README.md` Codex 운반체 문장 삭제
4. `tools/test_codex_adapter.py` **삭제**하되, 그 안의 Claude 쪽 단언은 **이동**(삭제 금지):
   - `copy_tree` write_bytes 회귀(2026-06-15 버그) + `build_user_claude_md` 4성질 → `tools/test_deploy.py`
   - `guard_paths` deny(.pem)/allow(app.py)/ask(evaluate.recipe)/ask(evaluate-off) → `tools/test_guard_paths.py`
5. build-log #30 행 + §3 인벤토리(deploy 타깃 문구)

## Scope — OUT
2~4단계 내용 일체(권한 규칙·rules·plugin.json·SessionStart) ✗ / AGENTS.md 지원 추가 ✗(CLAUDE.md 있으면 무시됨) /
`copy_tree` 외 deploy 리팩터 ✗ / build-log 과거 행의 Codex 서술 수정 ✗(결정 로그는 불변, supersede만)

## Edge cases
- 테스트 파일 삭제 = 게이트 자기보호 발동 → 그 커밋만 `GATE_EDIT_OK=1`(형욱 승인 = 이 플랜)
- `~/.claude`가 main보다 뒤면 `deploy --check`가 drift로 exit 1 → 구현 전 `deploy.py` 1회 실행
- `.toml` 문자열은 `pyproject.toml` 등 정상 참조가 있으므로 판정 grep은 `codex|\.codex`만
- `run_tests.py`는 `tools/test_*.py` 글롭이라 새 파일 자동 발견 → recipe 불변

## 수용 기준 (Acceptance criteria)
recipe 불변(`selfcheck`/`tests`/`deploy --check` 전부 exit 0). 추가 기준은 전부 테스트/원샷 명령:
- `git grep -ilE 'codex|\.codex' -- ':!docs/' ':!.claude/plan.md'` → 출력 없음(exit 1) *(plan.md는 이 삭제를 서술하므로 제외)*
- `python deploy.py --help` 출력에 `--target` 없음; `python deploy.py --check` exit 0
- `python -B tools/run_tests.py` → 전 파일 PASS, 파일 수 **10**(9 − codex_adapter + deploy + guard_paths)
- `tools/test_deploy.py`: bytes copy가 파일을 실제로 씀 / CLAUDE.md 렌더 마커+규칙 포함·H1 제거·멱등·블록 밖 보존
- `tools/test_guard_paths.py`: `secret.pem`→deny, `app.py`→무출력, `.claude/evaluate.recipe`→ask, `.claude/evaluate-off`→ask
- 실거래(이 클론에 게이트 설치 후): 테스트 삭제 커밋이 `GATE_EDIT_OK` 없이 **차단**(exit≠0), 있으면 통과
- 독립 평가자(`wook-evaluator`)가 위 항목을 재실행해 PASS
