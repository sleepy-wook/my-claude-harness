# claude-harness — 프로젝트 지침

- 이 repo는 형욱의 개인 Claude Code harness(hooks/skills/agents)를 만드는 곳이다.
- 설계 명세는 `docs/claude-harness-design.md`(source of truth)이고, **실제로 만든 것은
  `docs/build-log.md`에 기록**한다.
- harness 구성요소(hook·스크립트·설정·규칙)를 추가/변경하면 같은 작업 안에서
  `docs/build-log.md`를 갱신한다(만든 것·파일 경로·검증 결과·결정을 반영).
- 실제 harness 파일은 global `~/.claude/`(hooks/, harness/, settings.json)에 산다.
