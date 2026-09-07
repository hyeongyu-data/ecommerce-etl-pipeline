# AI 코딩 에이전트 작업 지침

> Version: 0.1.0 | Last Updated: 2026-07-15

이 문서는 Claude Code 등 AI 코딩 에이전트가 이 저장소에서 작업할 때의 기본
진입점입니다. 필수 규칙은 짧게 유지하고, 상세 가이드는 `.claude/docs/`를
참조합니다. `AGENTS.md`는 이 파일의 symlink이며, `.agents`는 `.claude`의
symlink입니다.

## 언어 원칙

에이전트 응답, PR 코멘트, 리뷰 요약, 구현 노트는 한국어 격식체를 사용합니다.
사용자가 명시적으로 요청하는 경우에만 다른 언어를 사용합니다.

## 규칙 우선순위

규칙이 충돌하면 다음 순서로 적용합니다:

1. 사용자의 명시적 요청
2. `CLAUDE.md` 및 `AGENTS.md`
3. `.claude/docs/` 하위 가이드
4. `CONTRIBUTING.md`, `README.md`, 기타 저장소 문서

같은 수준이면 더 구체적이고 더 최근에 갱신된 규칙을 우선합니다.

## 문서 탐색 기준

비자명한 변경을 하기 전에 가장 관련 있는 가이드를 먼저 확인합니다:

| 요청 유형 | 먼저 볼 문서 |
| --- | --- |
| 워크플로우, 커밋, PR | `.claude/docs/agent-workflow-reference.md` |
| 보안, 시크릿, 권한 | `.claude/docs/agent-security-guidelines.md` |
| 코드/diff 리뷰 | `.claude/docs/agent-peer-review.md` |
| 계획 리뷰 | `.claude/docs/agent-plan-review.md` |
| 해서는 안 되는 일 | `.claude/docs/agent-prohibitions.md` |

## 프로젝트 맥락

- <프로젝트 한 줄 설명을 여기에 적으세요.>
- 소스·테스트 위치는 언어에 맞게 정하세요. 문서: `README.md` / `.claude/docs/`.
- 상세 워크플로(브랜치·커밋·PR): `.claude/docs/agent-workflow-reference.md`.

## 핵심 규칙

- 코드가 변경되는 작업은 이슈를 먼저 발행하고, 그 이슈의 `Create a branch`로
  브랜치를 만듭니다(이슈-브랜치 자동 연결).
- 새 추상화보다 기존 저장소 패턴을 우선합니다. 필요 없는 코드는 만들지
  않습니다(YAGNI).
- 구조 변경(리팩터링)과 동작 변경은 분리된 커밋/PR로 나눕니다.
- GitHub 원격에 영향을 주는 작업(issue/PR 생성·수정, push, label, Ruleset)은
  실행 전에 사용자에게 먼저 확인받습니다.
- secret, `.env`, 자격 증명, 키는 커밋하지 않습니다. 커밋 전 diff에서 노출을
  확인합니다.
- 동작·명령어·설정이 바뀌면 관련 `.md` 문서(README 등)를 같은 PR에서 갱신합니다.
- 커밋 메시지·PR·이슈 본문은 `.github/`의 템플릿과 `CONTRIBUTING.md` 컨벤션을
  그대로 따릅니다.

## 로컬 개발 / 검증

변경을 증명하는 가장 좁은 검증부터 수행합니다.

```bash
pre-commit run --all-files   # 기본 훅 (공백/개행/YAML/시크릿)
git diff --check             # 공백/충돌 마커
# 언어별 린트·테스트 명령을 여기에 추가하세요 (npm test / go test / pytest 등)
```

## 리뷰 기준

PR 리뷰 시 심각도 순으로 구체적 발견 사항을 먼저 제시합니다:

- 정확성 버그, 기존 동작의 의도치 않은 변경
- 시크릿/자격 증명 노출
- 불필요한 복잡도·중복 (기존 코드로 대체 가능한지)
- 테스트 누락

구체적 이슈는 인라인 코멘트로, 요약은 짧게 유지합니다.
