"""DAG 3: GA4 목업 구매 보고서 생성 → 검증 후 staging 저장.

실제 GA4 API를 호출하지 않는다. 원천·품질 검사에서 실패하면 결과를 저장하지 않는다.
    docker compose exec airflow-scheduler airflow dags test ga4_events_ingest 2026-09-01
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

from ecommerce_etl.ga4 import generate, transform

DATA_DIR = Path(os.environ.get("ETL_DATA_DIR", "/opt/airflow/data"))
RAW_DIR = DATA_DIR / "raw" / "ga4"
STAGING_DIR = DATA_DIR / "staging" / "ga4"


def _order_date() -> date:
    """실행 기준일을 KST 날짜 파티션으로 사용한다."""
    return get_current_context()["logical_date"].in_timezone("Asia/Seoul").date()


@dag(
    dag_id="ga4_events_ingest",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 9, 1, tz="Asia/Seoul"),
    catchup=False,
    max_active_runs=1,
    tags=["ga4", "mock", "ingest"],
    doc_md=__doc__,
)
def ga4_events_ingest():
    @task
    def generate_raw() -> str:
        return str(generate.write_json(_order_date(), RAW_DIR))

    @task
    def validate_and_stage(raw_json: str) -> str:
        return str(transform.validate_and_stage(raw_json, STAGING_DIR, _order_date()))

    validate_and_stage(generate_raw())


ga4_events_ingest()
