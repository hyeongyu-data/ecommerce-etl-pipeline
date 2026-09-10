# ecommerce-etl-pipeline

> 이종 데이터소스(PG 주문·오픈마켓 주문·GA4 이벤트)를 Airflow로 수집·정제해 통합 주문 테이블로
> 적재하는 미니 ETL 파이프라인. 설계 목표 웨어하우스는 BigQuery이고, 로컬에서는 결제 계정 없이
> 돌리기 위해 같은 스키마의 DuckDB로 적재합니다.

<!-- ![CI](https://github.com/hyeongyu-data/ecommerce-etl-pipeline/actions/workflows/ci.yml/badge.svg) -->

## 배경

이커머스 현장에서 결제(PG)·오픈마켓 주문 데이터를 수작업으로 대조·정산하던 경험을, 자동화된
파이프라인으로 축소 재현하는 개인 프로젝트입니다. 서로 스키마가 다른 3개 소스를 하나의 통합
주문 테이블로 모으고, 적재 과정에서 데이터 품질(누락·중복·이상치)을 검증합니다.

## 아키텍처

```
[PG 주문 CSV]  ─┐
[오픈마켓 API] ─┼─▶ Airflow DAG (수집)  ─▶  staging  ─▶  통합 적재  ─▶  orders_unified  ─▶  대시보드
[GA4 이벤트]   ─┘        (소스별 1개)      (parquet)   (품질검사 후)   DuckDB (로컬)      (후속)
```

- **수집**: 소스마다 DAG 1개. PG는 날짜 파티션 CSV를 일별 배치처럼 읽고, 오픈마켓은 목업 API를
  호출하며, GA4는 현재 보고서 형태의 목업 JSON을 생성합니다(실제 Data API 연동은 후속 범위).
- **정제·통합**: 소스별 원본 필드를 [`docs/SCHEMA.md`](docs/SCHEMA.md)의 통합 주문 스키마로 매핑합니다.
- **적재**: `warehouse_orders_load` DAG가 세 소스 staging을 합쳐 공통 품질검사 후 `orders_unified`
  테이블의 해당 날짜를 트랜잭션으로 교체합니다. 로컬 웨어하우스는 DuckDB(`DUCKDB_PATH`), 설계
  목표는 BigQuery(날짜 파티션 + `source` 클러스터) — 스키마·멱등 계약은 동일합니다.
- **대시보드**: 소스별 주문 수·매출 추이(후속 범위).

통합 스키마·DDL·설계 판단 근거(왜 이 스키마인지, 왜 BigQuery를 목표로 잡았는지)는
[`docs/SCHEMA.md`](docs/SCHEMA.md)에 있습니다.

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
# → http://localhost:18080  (airflow / airflow ; AIRFLOW_WEB_PORT로 변경 가능)

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

# 또는 Airflow UI(localhost:18080)에서 pg_orders_ingest 트리거

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

## DAG 3 — GA4 목업 구매 보고서

GA4 Data API의 보고서 형태(`dimensionHeaders`·`metricHeaders`·`rows`)를 흉내 낸
**결정론적 합성 JSON**을 날짜별로 생성합니다. 실제 Google API 호출이나 인증은 하지 않으며,
목업 실행 성공은 실제 GA4 연동 검증을 의미하지 않습니다.

`generate_raw → validate_and_stage`: 입력 계약과 공통 Q1~Q7 품질검사(위반 허용 0)를
모두 통과한 뒤에만 staging을 씁니다. 자세한 매핑과 제약은 [통합 스키마](docs/SCHEMA.md#2-3-ga4-구매-보고서--ga4-현재는-목업)를 참고하세요.

```shell
docker compose build       # 새 코어 코드도 Airflow 이미지에 설치
docker compose up -d
docker compose exec airflow-scheduler airflow dags test ga4_events_ingest 2026-09-01
# 원천: data/raw/ga4/order_date=2026-09-01/report.json
# 결과: data/staging/ga4/order_date=2026-09-01/orders.parquet
```

- 속성 시간대는 `Asia/Seoul`, 통화는 KRW, 이벤트는 purchase로 제한합니다.
- 보고서의 누락·중복 헤더, 잘못된 행 구조, 대상일 밖 날짜, 거래 내 중복 상품,
  불일치하는 거래 시각, 음수·소수 수량/금액 및 소수 단가는 명시적으로 실패합니다.
- 거래별 상품 ID를 정렬하여 라인 번호를 부여합니다. 입력 순서만 바뀌어도 키는 유지됩니다.
  같은 날짜 재실행은 같은 경로에 덮어쓰며 `ingested_at`은 새 처리 시각입니다.
- 빈 보고서는 정상적인 0행 결과로 저장하지만, 수집 오류·손상된 JSON은 빈 성공으로 처리하지 않습니다.
  입력·품질 실패 시 raw와 이전 staging을 보존합니다. 공통 저장 함수의 쓰기는 비원자적이므로
  디스크 오류 시 기존 결과 보존까지 보장하지는 않습니다.
- DAG는 동시 활성 실행을 1개로 제한합니다. 오늘 날짜의 목업은 아직 지나지 않은 시간대도 만들 수 있어
  미래 시각 검사에서 실패할 수 있습니다. 재현 검증은 과거 날짜로 수행하세요.
- 실제 GA4 속성의 필드 조합 호환성, 인증, 페이지 처리, 보고서 집계·지연 도착 처리는 후속 작업입니다.
  합성 소스별 주문을 실제 결제와 GA4 구매 이벤트의 중복 제거가 끝난 매출로 해석하지 않습니다.

## 통합 적재 — warehouse_orders_load

세 소스(`pg`·`openmarket`·`ga4`)의 그날 staging parquet을 합쳐 공통 품질검사(Q1~Q7, union 기준)를
통과한 뒤 웨어하우스 `orders_unified` 테이블의 해당 날짜를 **트랜잭션으로 교체**합니다. 같은 날짜를
다시 실행해도 행이 중복되지 않고, 다른 날짜 파티션은 보존됩니다.

- **로컬 웨어하우스**: DuckDB. 파일 경로는 `DUCKDB_PATH`(컨테이너 기본
  `/opt/airflow/data/warehouse/orders.duckdb` — 호스트 `data/` 아래라 재기동해도 유지).
  구현은 `ecommerce_etl.duckdb`.
- **설계 목표**: BigQuery(`${GCP_PROJECT_ID}.${BQ_DATASET}.orders_unified`, 날짜 파티션 + `source`
  클러스터). 18컬럼 스키마와 날짜 단위 멱등 교체 계약은 두 백엔드가 동일합니다. 전환 근거는
  [`docs/SCHEMA.md` §4-1](docs/SCHEMA.md#4-1-왜-bigquery인가-설계-목표-로컬은-왜-duckdb인가).

```shell
# 선행: pg/openmarket/ga4 DAG로 해당 날짜 staging을 먼저 만든 뒤
docker compose exec airflow-scheduler airflow dags test warehouse_orders_load 2026-09-01
# → DuckDB orders_unified 테이블의 order_date=2026-09-01 파티션 교체
```

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
│   ├── openmarket/       # 오픈마켓 소스: client(HTTP) · transform
│   └── ga4/              # GA4 목업 보고서: generate · transform(검증 후 저장)
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
├── .github/              # 이슈·PR 템플릿, CI, dependabot, branch_ruleset_main.json
├── .claude/docs/         # AI 에이전트 참고 문서 (워크플로/리뷰/보안/금지)
└── (dotfiles)            # .gitignore .editorconfig .python-version .pre-commit-config.yaml …
```

## 기여

브랜치·커밋·PR 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.
브랜치명은 `<type>/<issue#>-설명` 형식입니다 (예: `feat/4-add-pg-dag`).

## License

MIT — [LICENSE](LICENSE) 참조.
