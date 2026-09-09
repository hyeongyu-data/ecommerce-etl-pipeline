"""DAG 1: PG 주문 수집.

날짜 파티션 단위로 합성 원천 생성 → 통합 스키마 변환 → 품질검사 → staging(parquet).
BigQuery 적재는 별도 DAG(계획 9~10일차). 로직은 전부 `ecommerce_etl` 패키지에 있고
여기서는 태스크 wiring만 한다.

수동 실행:
    docker compose exec airflow-scheduler airflow dags test pg_orders_ingest 2026-09-01
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

from ecommerce_etl import quality, staging
from ecommerce_etl.pg import generate, transform

DATA_DIR = Path(os.environ.get("ETL_DATA_DIR", "/opt/airflow/data"))
RAW_DIR = DATA_DIR / "raw" / "pg"
STAGING_DIR = DATA_DIR / "staging" / "pg"
MAX_VIOLATION_RATE = float(os.environ.get("PG_QUALITY_MAX_VIOLATION_RATE", "0.01"))


def _order_date() -> date:
    """실행의 logical_date를 Asia/Seoul 기준 날짜로 (파티션 키)."""
    ctx = get_current_context()
    return ctx["logical_date"].in_timezone("Asia/Seoul").date()


@dag(
    dag_id="pg_orders_ingest",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 9, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["pg", "ingest"],
    doc_md=__doc__,
)
def pg_orders_ingest():
    @task
    def generate_raw() -> str:
        return str(generate.write_csv(_order_date(), RAW_DIR))

    @task
    def transform_to_staging(raw_csv: str) -> str:
        df = transform.transform(raw_csv)
        return str(staging.write_parquet(df, STAGING_DIR, _order_date()))

    @task
    def quality_check(staging_parquet: str) -> None:
        df = pd.read_parquet(staging_parquet)
        result = quality.check(df, max_violation_rate=MAX_VIOLATION_RATE)
        print(
            f"품질검사: {result.bad_rows}/{result.total} 위반 "
            f"(rate={result.violation_rate:.4f}, 임계={MAX_VIOLATION_RATE})"
        )
        if result.violations:
            print("위반 상세:", result.violations)
        if not result.passed:
            raise ValueError(f"품질 위반율이 임계를 초과했습니다: {result.violation_rate:.4f}")

    quality_check(transform_to_staging(generate_raw()))


pg_orders_ingest()
