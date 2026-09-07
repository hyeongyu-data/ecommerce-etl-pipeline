# 에이전트 워크플로우 참조

GitHub 워크플로우 전체 가이드: Issue → Branch → Commit → PR → Review →
Merge. 사람용 요약은 `CONTRIBUTING.md`에 있으며, 두 문서의 규칙은 항상
일치해야 합니다.

## 이 문서를 볼 때

- 새 작업을 시작하며 전체 워크플로우가 필요할 때
- 커밋 메시지나 PR 본문을 작성할 때
- PR이 워크플로우를 따르는지 검증할 때

## 워크플로우 개요

```
Issue 생성
    ↓
Branch 생성 (이슈의 Create a branch, <type>/<이슈번호>-설명)
    ↓
작업/검증 (pre-commit run, 언어별 테스트, git diff --check)
    ↓
Draft PR 생성 → 셀프 리뷰 및 설명 보강
    ↓
Ready for review 전환 → 리뷰 요청
    ↓
Approve + 대화 resolve → Squash Merge
    ↓
Issue 자동 close
```

## 에이전트 기본 규칙

- GitHub 원격에 영향을 주는 작업은 항상 사용자에게 먼저 확인받습니다:
  issue 생성·수정·close, label 변경, PR 생성·수정·merge, 원격 branch
  push·삭제, Project·Ruleset·Secrets 변경.
- 로컬 파일 읽기·수정은 진행해도 됩니다. GitHub에 반영하는 순간에만
  확인받습니다.
- 이슈·PR 기본값: Assignee는 생성자로 지정합니다
  (`gh issue create`·`gh pr create`에 `--assignee @me`).

## 자동 담당자 및 라벨

- Feature·Bug Issue Form은 `hyeongyu-data`를 담당자로 자동 지정하고 각각
  `feature`, `bug` 라벨을 붙입니다.
- PR은 생성자를 담당자로 자동 지정합니다. 제목이 커밋 컨벤션의 type으로 시작하면
  다음 라벨을 추가합니다: `feat` → `feature`, `fix` → `bug`, `refactor` →
  `refactor`, `docs` → `documentation`, `test` → `test`, `chore` → `chore`.
- 자동화는 PR 코드를 checkout하거나 실행하지 않습니다. 템플릿을 다른 계정에서
  사용할 때에는 Issue Form의 `assignees` 값을 해당 계정으로 바꿉니다.

## 이슈 생성

Issue Forms(`.github/ISSUE_TEMPLATE/`, 빈 이슈 생성 불가):

| Form | 제목 prefix | 자동 label | 필수 내용 |
|---|---|---|---|
| `feature.yml` | `[FEAT]` | `feature` | 목적, 작업 범위, 완료 조건 |
| `bug.yml` | `[BUG]` | `bug` | 현상, 재현 방법, 기대·실제 동작, 환경·로그 |

아주 작은 오타 수정은 바로 PR로 처리할 수 있습니다.

## 브랜치 이름

코드가 변경되는 작업은 이슈를 먼저 발행하고, 그 이슈의
`Development > Create a branch`로 생성합니다(이슈 자동 연결).

**형식:** `<type>/<이슈번호>-<간략한-설명>` (영어 소문자·숫자·하이픈)
**Type:** `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, `chore/`

```bash
git fetch origin && git switch feat/12-add-login
```

## 커밋 메시지

**형식:** `<type>: <한국어 설명>` (현재형, 50자 이내)

| type | 의미 |
|---|---|
| `feat` | 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 동작 변화 없는 구조 정리 |
| `docs` | 문서 |
| `test` | 테스트 추가·수정 |
| `chore` | 설정·관리 작업 |

한 커밋에는 하나의 논리적 변경만. 포맷 변경과 동작 변경을 섞지 않습니다.

## PR 생성

**PR 생성 전 체크:**
- [ ] `pre-commit run --all-files` 통과
- [ ] 언어별 린트·테스트 통과
- [ ] `git diff --check` 통과
- [ ] secret / `.env` / 키가 포함되지 않았다
- [ ] 커밋 메시지가 컨벤션을 따른다
- [ ] `gh pr create --assignee @me`

본문은 `.github/PULL_REQUEST_TEMPLATE.md`를 그대로 따르고 `Closes #번호`를
포함합니다. Draft로 열어 diff를 처음부터 끝까지 셀프 리뷰한 뒤 Ready로
전환합니다.

## 리뷰와 머지

**머지 조건:** approve + 모든 conversation resolved + CI(`lint-test`)
통과 + Ready 상태. `branch_ruleset_main.json` 기준 `main` 직접 push 금지.

**Squash and merge만 사용합니다.** 머지 커밋 제목은
`<type>: <설명> (#PR번호)`. 머지 시 `Closes #`로 연결된 이슈가 자동
close되고 브랜치가 삭제됩니다.

## Special Cases

- **main과 충돌:** `git fetch origin main && git rebase origin/main`
  후 `git push --force-with-lease`. 재리뷰 요청.
- **리뷰 수정 요청:** 새 커밋으로 수정(amend 금지) 후 push.
- **PR 분리:** 새 이슈를 만들고 커밋을 새 브랜치로 cherry-pick.
