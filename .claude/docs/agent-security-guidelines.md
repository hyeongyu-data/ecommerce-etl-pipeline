# 에이전트 보안 가이드

시크릿, 자격 증명, 워크플로 권한을 다룰 때 사용하는 문서입니다.

## Secrets

- 다음을 절대 커밋하지 않습니다:
  - `.env` (로컬 환경 변수)
  - 키 파일, 토큰, `*.pem`, `*.key`, credential JSON
- 시크릿 값은 코드, 로그, PR 본문, 커밋 메시지에 포함하지 않습니다.
- 새 환경 변수가 필요하면 값이 비어 있는 항목을 `.env.example`에 추가하고
  용도를 주석으로 남깁니다.
- 커밋 전 `git status`와 diff에서 시크릿·자격 증명이 포함되지 않았는지
  확인합니다. `.pre-commit-config.yaml`의 `detect-private-key` 훅이
  1차 방어선입니다.

## 자격 증명 / 권한

- 최소 권한 원칙을 적용합니다. 광범위한 권한을 기본으로 부여하지 않습니다.
- 로컬 개발용 자격 증명과 CI/프로덕션 자격 증명을 분리합니다.
- 권한 확대 변경은 PR에 사유와 롤백 방법을 명시합니다.

## 입력 검증

- 신뢰 경계(외부 입력, 사용자 입력, 네트워크 응답)에서 검증을 생략하지
  않습니다.
- 외부에서 제어 가능한 입력을 shell·SQL·경로에 직접 보간하지 않습니다.

## GitHub Actions

- workflow의 `permissions`는 필요한 최소 권한만 부여합니다
  (기본 `contents: read`).
- 시크릿은 GitHub Secrets로 참조하고 workflow 파일에 하드코딩하지
  않습니다.
- 외부에서 제어 가능한 입력(PR 제목, 코멘트 본문)을 shell에 직접
  보간하지 않습니다.

## Review Triggers

다음이 바뀌면 PR 리뷰에 Security 관점을 반드시 포함합니다:

- 인증·권한 로직, 시크릿·환경 변수 처리
- 외부 입력 처리, 네트워크 노출
- GitHub Actions workflow와 `permissions`
