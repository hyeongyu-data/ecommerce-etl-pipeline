"""DAG 2: 오픈마켓 주문 수집 (HTTP API).

날짜 파티션 단위로 목업 API에서 carts+products fetch → 통합 스키마 변환 → 품질검사
→ staging(parquet). 통합 적재는 별도 DAG(`warehouse_orders_load`). 로직은 `ecommerce_etl`
패키지에 있고 여기서는 태스크 wiring만 한다.

수동 실행:
    docker compose exec airflow-scheduler airflow dags test openmarket_orders_ingest 2026-09-01
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

from ecommerce_etl import quality, staging
from ecommerce_etl.openmarket import client, transform

DATA_DIR = Path(os.environ.get("ETL_DATA_DIR", "/opt/airflow/data"))
RAW_DIR = DATA_DIR / "raw" / "openmarket"
STAGING_DIR = DATA_DIR / "staging" / "openmarket"
API_BASE_URL = os.environ.get("OPENMARKET_API_BASE_URL", "http://mock-openmarket:8000")
MAX_VIOLATION_RATE = float(os.environ.get("OPENMARKET_QUALITY_MAX_VIOLATION_RATE", "0.01"))


def _order_date() -> date:
    """실행의 logical_date를 Asia/Seoul 기준 날짜로 (파티션 키)."""
    ctx = get_current_context()
    return ctx["logical_date"].in_timezone("Asia/Seoul").date()


@dag(
    dag_id="openmarket_orders_ingest",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 9, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["openmarket", "ingest"],
    doc_md=__doc__,
)
def openmarket_orders_ingest():
    @task
    def fetch() -> str:
        order_date = _order_date()
        carts = client.fetch_carts(API_BASE_URL, order_date)
        products = client.fetch_products(API_BASE_URL)
        part_dir = RAW_DIR / f"order_date={order_date.isoformat()}"
        part_dir.mkdir(parents=True, exist_ok=True)
        (part_dir / "carts.json").write_text(
            json.dumps(carts, ensure_ascii=False), encoding="utf-8"
        )
        (part_dir / "products.json").write_text(
            json.dumps(products, ensure_ascii=False), encoding="utf-8"
        )
        return str(part_dir)

    @task
    def transform_to_staging(raw_dir: str) -> str:
        rd = Path(raw_dir)
        carts = json.loads((rd / "carts.json").read_text(encoding="utf-8"))
        products = json.loads((rd / "products.json").read_text(encoding="utf-8"))
        df = transform.transform(carts, products, source_file=rd.name)
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

    quality_check(transform_to_staging(fetch()))


openmarket_orders_ingest()
