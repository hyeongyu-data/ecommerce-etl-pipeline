# Contributing

## 작업 흐름

```
이슈 → 브랜치 → 작업 → Draft PR → 셀프 리뷰 → Ready → 리뷰 → Squash merge
```

`main`에는 직접 push하지 않습니다. 모든 변경은 PR로 병합합니다
(`branch_ruleset_main.json`을 GitHub Ruleset으로 import하면 강제됩니다).

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

## 코드 스타일

`pre-commit install` 후 커밋 시 기본 훅(공백/개행/YAML/시크릿 검사)이 자동
실행됩니다. 언어별 린터/포매터는 `.pre-commit-config.yaml`에 추가하세요.
