# core-rules.md 작성 가이드 (이 파일은 배포 도구가 읽지 않음)

`core-rules.md`는 표준 작업 합의(standing rules)의 **소스**다. v2부터는 매 턴 주입이 아니라
`deploy.py`가 두 운반체로 렌더한다:

- **Claude Code** → `~/.claude/CLAUDE.md`의 marked block
  (`<!-- wook-harness:begin/end -->`). CLAUDE.md는 세션당 1회 로드·프롬프트 캐시되고,
  공식 문서상 compaction 후에도 재주입된다 — 매 턴 additionalContext로 중복 주입하던
  구(舊) `inject_core_rules.py` 방식(~700토큰/턴 누적)을 대체한 검증된 운반체다.
- **Codex** → `~/.codex/AGENTS.md` (기존 그대로).

## 작성 규칙

- **사실 진술로 쓴다.** 명령조("~하지 마")보다 "이 개발자는 ~를 선호한다 / ~를 신뢰하지
  않는다" 같은 사실 문장이 지침으로 안정적으로 작동한다.
- **짧게 유지한다.** 항상 로드되는 컨텍스트이므로 길면 토큰 낭비 + 효과 희석.
  업계 가이드는 상시 지침 파일을 ~60줄 이하로 권장한다.
- **행동 규칙을 둔다.** 세션이 길어지면 흐려지는 *행동* 규칙이 여기 적합하다.
  프로젝트별 사실은 각 프로젝트의 CLAUDE.md/AGENTS.md에 두는 게 낫다.

## deploy가 처리하는 방식

- 맨 위 H1 제목(`# core-rules`) 줄은 렌더에서 제외된다.
- `~/.claude/CLAUDE.md`에서 marked block **바깥**의 내용은 그대로 보존된다
  (형욱이 직접 적은 메모와 공존 가능).
- 파일이 없거나 비어 있으면 빈 블록만 쓴다(무해).

## 편집하면 언제 반영되나

- `python deploy.py` 실행 후, **다음 세션 시작부터** 반영된다
  (CLAUDE.md는 세션 시작 시 로드되므로 현재 세션엔 소급 적용되지 않음).
