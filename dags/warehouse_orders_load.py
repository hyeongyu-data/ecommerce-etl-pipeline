"""DAG: 세 소스의 staging 주문을 DuckDB 날짜 파티션으로 교체 적재한다."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

from ecommerce_etl import schema
from ecommerce_etl.duckdb import replace_date
from ecommerce_etl.quality import check

DATA_DIR = Path(os.environ.get("ETL_DATA_DIR", "/opt/airflow/data"))
DB_PATH = Path(os.environ.get("DUCKDB_PATH", "/opt/airflow/data/warehouse/orders.duckdb"))


def _order_date() -> date:
    return get_current_context()["logical_date"].in_timezone("Asia/Seoul").date()


@dag(
    dag_id="warehouse_orders_load",
    schedule=None,
    start_date=pendulum.datetime(2026, 9, 1, tz="Asia/Seoul"),
    catchup=False,
    max_active_runs=1,
    tags=["duckdb", "load"],
    doc_md=__doc__,
)
def warehouse_orders_load():
    @task
    def load_partition() -> int:
        load_date = _order_date()
        frames = []
        for source in schema.SOURCES:
            path = (
                DATA_DIR
                / "staging"
                / source
                / f"order_date={load_date.isoformat()}"
                / "orders.parquet"
            )
            if path.exists():
                frames.append(pd.read_parquet(path))
        if not frames:
            raise FileNotFoundError(f"staging 파일이 없습니다: {load_date}")
        combined = pd.concat(frames, ignore_index=True).loc[:, list(schema.UNIFIED_COLUMNS)]
        result = check(combined)
        if not result.passed:
            raise ValueError(f"통합 품질검사 실패: {result.violations}")
        return replace_date(DB_PATH, combined, load_date)

    load_partition()


warehouse_orders_load()
