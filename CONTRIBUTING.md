# Contributing

## 개발 환경 준비

**전제**: Python 3.12, Docker(Desktop 또는 Engine + compose v2).

```shell
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                             # pre-commit, ruff, pytest
pre-commit install
git config commit.template .gitmessage
```

로컬 Airflow는 `cp .env.example .env` 후 `docker compose up -d`
(웹 UI `http://localhost:8080`, 계정 `airflow`/`airflow`). 정리는 `docker compose down -v`.
`uv` 등 개별 도구 없이 표준 `venv` + `pip` + `docker compose` 만으로 동작해야 합니다.

## 작업 흐름

```
이슈 → 브랜치 → 작업 → Draft PR → 셀프 리뷰 → Ready → 리뷰 → Squash merge
```

`main`에는 직접 push하지 않습니다. 모든 변경은 PR로 병합합니다
(`.github/branch_ruleset_main.json`을 GitHub Ruleset으로 import하면 강제됩니다).

## 브랜치 규칙

이슈의 `Create a branch`로 만들고, 이름은 소문자·하이픈으로:

```
<type>/<issue#>-설명      # 예: feat/42-add-login, fix/31-null-check
```

## 커밋 메시지

`<type>: <설명>` (한국어, 50자 내외). type:
`feat`, `fix`, `refactor`, `docs`, `test`, `chore`

커밋 템플릿(`.gitmessage`)이 제공됩니다. 클론 후 한 번 설정하면 `git commit` 시
자동으로 채워집니다:

```shell
git config commit.template .gitmessage
```

## PR

1. 본문에 `Closes #<issue>` 포함.
2. Draft로 열어 모든 diff를 셀프 리뷰한 뒤 Ready로 전환.
3. CI(`lint-test`) 통과 + 리뷰 승인 + 모든 대화 resolved 후 **squash merge**.

PR을 열거나 Ready로 전환하면 Claude가 리뷰 요약 + "이해도 확인" inline 코멘트를 자동으로 답니다
(`GUDOKPIN_API_KEY` 시크릿 필요, 없으면 skip — 자세한 내용은 [README](README.md#ai-리뷰)).
필수 체크는 아니며, 재리뷰는 `/ai-review` 코멘트로 실행합니다.

## 코드 스타일

`pre-commit install` 후 커밋 시 기본 훅(공백/개행/YAML/JSON/시크릿)과 `ruff`
(린트·포맷)가 자동 실행됩니다. 설정은 `pyproject.toml`, 훅 목록은
`.pre-commit-config.yaml`에 있습니다.
