# ecommerce-etl-pipeline

> 이종 데이터소스(PG 주문·오픈마켓 주문·GA4 이벤트)를 Airflow로 수집·정제해 BigQuery에 통합
> 적재하고 대시보드로 보여주는 미니 ETL 파이프라인.

<!-- ![CI](https://github.com/hyeongyu-data/ecommerce-etl-pipeline/actions/workflows/ci.yml/badge.svg) -->

## 배경

이커머스 현장에서 결제(PG)·오픈마켓 주문 데이터를 수작업으로 대조·정산하던 경험을, 자동화된
파이프라인으로 축소 재현하는 개인 프로젝트입니다. 서로 스키마가 다른 3개 소스를 하나의 통합
주문 테이블로 모으고, 적재 과정에서 데이터 품질(누락·중복·이상치)을 검증합니다.

## 아키텍처

```
[PG 주문 CSV]  ─┐
[오픈마켓 API] ─┼─▶ Airflow DAG (수집)  ─▶  staging  ─▶  정제·통합  ─▶  BigQuery  ─▶  대시보드
[GA4 이벤트]   ─┘        (소스별 1개)                  (통합 스키마)   orders_unified   (Streamlit)
```

- **수집**: 소스마다 DAG 1개. PG는 날짜 파티션 CSV를 일별 배치처럼 읽고, 오픈마켓은 목업 API를
  호출하며, GA4는 Data API로 이벤트를 가져옵니다(시간 부족 시 목업 JSON 대체).
- **정제·통합**: 소스별 원본 필드를 [`docs/SCHEMA.md`](docs/SCHEMA.md)의 통합 주문 스키마로 매핑합니다.
- **적재**: BigQuery `orders_unified`(날짜 파티션 + `source` 클러스터). 적재 전 품질 체크.
- **대시보드**: 소스별 주문 수·매출 추이(대안: Looker Studio).

설계 판단 근거(왜 BigQuery인지, 왜 이 스키마인지)와 DDL 초안은 [`docs/SCHEMA.md`](docs/SCHEMA.md)에 있습니다.

## 빠른 시작

**전제**: Python 3.12, Docker(Desktop 또는 Engine + compose v2).

```shell
# 1) 개발 도구 (가상환경 권장)
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                              # pre-commit, ruff, pytest
pre-commit install
git config commit.template .gitmessage

# 2) 로컬 Airflow 기동
cp .env.example .env                                 # Linux는 .env에 AIRFLOW_UID=$(id -u) 설정
docker compose up -d                                 # 첫 실행은 이미지 빌드로 수 분
# → http://localhost:8080  (airflow / airflow)

docker compose down -v                               # 정리
```

DAG는 `dags/`에 두면 컨테이너에 자동 반영됩니다(단, DAG가 import 하는 `ecommerce_etl`
패키지는 이미지에 설치되므로 의존성이 바뀌면 `docker compose build` 필요). 개별 도구는
`uv` 등 없이 표준 `venv` + `pip`만으로 동작합니다.

## DAG 1 — PG 주문 수집

합성 PG 주문을 날짜 파티션으로 수집·정제해 staging(parquet)에 적재합니다.
`generate_raw → transform_to_staging → quality_check`(통합 스키마 매핑 + `SCHEMA.md` Q1~Q7).

```shell
# 특정 날짜 실행
docker compose exec airflow-scheduler airflow dags test pg_orders_ingest 2026-09-01
# → data/staging/pg/order_date=2026-09-01/orders.parquet

# 또는 Airflow UI(localhost:8080)에서 pg_orders_ingest 트리거

# 로컬에서 원천만 미리 생성해 눈으로 확인
python scripts/gen_pg_orders.py --start 2026-09-01 --end 2026-09-07
```

## DAG 2 — 오픈마켓 주문 수집

오픈마켓 주문을 **HTTP API로** 수집합니다. 재현성을 위해 외부 API 대신 compose의
`mock-openmarket`(fakestore 형태 목업 서버)을 띄우고, DAG는 여기에 실제 `requests` 호출을 합니다.
`fetch → transform_to_staging → quality_check`.

```shell
docker compose up -d   # mock-openmarket 포함해 함께 기동
docker compose exec airflow-scheduler airflow dags test openmarket_orders_ingest 2026-09-01
# → data/staging/openmarket/order_date=2026-09-01/orders.parquet
```

BigQuery 적재는 별도 DAG로 이어집니다(계획 9~10일차).

## 검증

```shell
pre-commit run --all-files   # 공백/개행/YAML/JSON/시크릿 + ruff
pytest
git diff --check
docker compose config        # compose 문법 확인
```

## 저장소 구조

```
.
├── src/ecommerce_etl/    # 수집·정제 코어 로직 (Airflow 무관, 순수 파이썬)
│   ├── schema.py         # 통합 18컬럼 정의 (단일 출처)
│   ├── quality.py        # 데이터 품질 검사 Q1~Q7
│   ├── staging.py        # staging parquet 쓰기 (소스 공용)
│   ├── catalog.py        # 상품 카탈로그 (소스 공용)
│   ├── pg/               # PG 소스: generate(합성) · transform(통합 매핑)
│   └── openmarket/       # 오픈마켓 소스: client(HTTP) · transform
├── dags/                 # Airflow DAG (컨테이너에 바인드 마운트)
├── mock/                 # 로컬 목업 오픈마켓 API (compose 서비스로 실행)
├── scripts/              # 로컬 편의 스크립트 (합성 데이터 생성 등)
├── data/                 # raw/·staging/ 데이터 (git 제외, 컨테이너에 마운트)
├── docs/SCHEMA.md        # 통합 주문 스키마 설계 + DDL
├── tests/                # pytest
├── docker-compose.yaml   # 로컬 Airflow (webserver+scheduler+postgres, LocalExecutor)
├── Dockerfile            # 로컬 Airflow 이미지 (공식 이미지 + ecommerce_etl + 의존성)
├── pyproject.toml        # 메타데이터 · 런타임/개발 의존성 · ruff/pytest 설정
├── README.md  LICENSE  CONTRIBUTING.md
├── CLAUDE.md             # AI 코딩 에이전트 진입점 (AGENTS.md·.agents는 symlink)
├── .github/              # 이슈·PR 템플릿, CI, AI 리뷰, dependabot, branch_ruleset_main.json
├── .claude/docs/         # AI 에이전트 참고 문서 (워크플로/리뷰/보안/금지)
└── (dotfiles)            # .gitignore .editorconfig .python-version .pre-commit-config.yaml …
```

## AI 리뷰

PR을 열거나 Ready로 전환하면 Anthropic Claude(`anthropics/claude-code-action`, 모델은
`.github/workflows/ai-review.yml`의 `CLAUDE_MODEL`)가 자동으로 리뷰합니다 — 심각도 순 요약
코멘트 + diff 라인에 "이해도 확인:" inline 질문. 필수 체크가 아니며, 재리뷰는 PR 대화에
`/ai-review` 코멘트를 남깁니다. 문서 전용 PR은 자동 실행되지 않습니다.

활성화하려면 [Anthropic Console](https://console.anthropic.com/settings/keys)에서 API 키를
발급받아 저장소 `Settings > Secrets and variables > Actions`에 `GUDOKPIN_API_KEY`로 등록합니다.
키가 없으면 워크플로는 조용히 건너뜁니다.

## 기여

브랜치·커밋·PR 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.
브랜치명은 `<type>/<issue#>-설명` 형식입니다 (예: `feat/4-add-pg-dag`).

## License

MIT — [LICENSE](LICENSE) 참조.
