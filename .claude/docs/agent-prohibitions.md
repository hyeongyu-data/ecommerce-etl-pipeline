# 에이전트 금지 사항

이 저장소에서 에이전트가 해서는 안 되는 일의 목록입니다.

## Git / GitHub

- `main`에 직접 push하지 않습니다. 모든 변경은 PR을 거칩니다.
- 사용자 확인 없이 GitHub 원격에 영향을 주는 작업을 하지 않습니다:
  issue 생성·수정·close, label 변경, PR 생성·수정·merge, 원격 branch
  push·삭제, Project·Ruleset·Secrets 변경.
- 시크릿(`.env`, 키 파일, 토큰)을 커밋하지 않습니다.
- 컨벤션 외 커밋 type을 사용하지 않습니다. 허용:
  `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- 이미 push된 브랜치를 사용자 동의 없이 force push하지 않습니다
  (rebase 후 `--force-with-lease`는 예외).

## 코드

- 요청된 변경에 필요하지 않은 광범위한 리팩터링을 하지 않습니다.
- 동작 변경과 구조 변경(파일 이동, 이름 변경)을 한 커밋에 섞지 않습니다.
- 자격 증명, API 키, 비밀 값을 코드에 하드코딩하지 않습니다. 환경 변수와
  Secret을 사용합니다.
- 필요 없는 추상화·의존성을 추가하지 않습니다 (YAGNI).

## Docs

- 동작, 명령어, 설정이 바뀌었는데 문서를 갱신하지 않은 채 작업을 끝내지
  않습니다.
- 규칙 문서(`CLAUDE.md`, `CONTRIBUTING.md`, `.claude/docs/`) 간에
  충돌하는 내용을 새로 만들지 않습니다. 충돌을 발견하면 사용자에게
  보고합니다.
