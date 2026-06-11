# claude-harness — 프로젝트 지침

- 이 repo는 형욱의 개인 Claude Code harness(hooks/skills/agents)를 만드는 곳이다.
- 설계 명세는 `docs/claude-harness-design.md`(source of truth)이고, **실제로 만든 것은
  `docs/build-log.md`에 기록**한다.
- harness 구성요소(hook·스크립트·설정·규칙)를 추가/변경하면 같은 작업 안에서
  `docs/build-log.md`를 갱신한다(만든 것·파일 경로·검증 결과·결정을 반영).
- `docs/build-log.md`는 무한 성장 방지를 위해 **계층 유지**한다(상단 유지 정책 참고): 결정(§1)은
  status로 supersede(대체/폐기 표시, **삭제 금지**), 오래된 기능 서술은 임계 초과 시
  `docs/build-log-archive/`로 이동(삭제 금지·검색 가능), §3 인벤토리는 현재 스냅샷 유지.
  `tools/selfcheck.py`가 임계(>700줄)에서 알리면 그때 아카이브한다(요약을 또 요약하지 말 것).
- 실제 harness 파일은 global `~/.claude/`(hooks/, harness/, settings.json)에 산다.
