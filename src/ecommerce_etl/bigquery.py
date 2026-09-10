"""통합 주문 데이터를 BigQuery에 멱등적으로 적재한다."""

from __future__ import annotations

import re
from datetime import date

import pandas as pd
from google.cloud import bigquery

from .schema import UNIFIED_COLUMNS

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str, name: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} 식별자가 올바르지 않습니다: {value!r}")
    return value


def table_schema() -> list[bigquery.SchemaField]:
    """통합 스키마를 BigQuery 필드 정의로 변환한다."""
    types = {
        "source": "STRING",
        "source_order_id": "STRING",
        "order_id": "STRING",
        "order_line_id": "STRING",
        "line_no": "INT64",
        "ordered_at": "TIMESTAMP",
        "order_date": "DATE",
        "customer_id": "STRING",
        "product_id": "STRING",
        "product_name": "STRING",
        "quantity": "INT64",
        "unit_price": "INT64",
        "line_amount": "INT64",
        "currency": "STRING",
        "channel": "STRING",
        "event_name": "STRING",
        "source_file": "STRING",
        "ingested_at": "TIMESTAMP",
    }
    return [
        bigquery.SchemaField(column, types[column], mode="NULLABLE") for column in UNIFIED_COLUMNS
    ]


def ensure_table(client: bigquery.Client, project: str, dataset: str, table: str) -> str:
    """없으면 날짜 파티션·source 클러스터 테이블을 만든다."""
    project = _validate_identifier(project, "프로젝트")
    dataset = _validate_identifier(dataset, "데이터셋")
    table = _validate_identifier(table, "테이블")
    table_id = f"{project}.{dataset}.{table}"
    try:
        client.get_table(table_id)
    except bigquery.NotFound:
        definition = bigquery.Table(table_id, schema=table_schema())
        definition.time_partitioning = bigquery.TimePartitioning(field="order_date")
        definition.clustering_fields = ["source"]
        client.create_table(definition)
    return table_id


def replace_date(client: bigquery.Client, frame: pd.DataFrame, target: str, load_date: date) -> int:
    """임시 테이블을 검증한 뒤 해당 날짜 파티션을 원자적으로 교체한다."""
    if frame.empty:
        return 0
    missing = [column for column in UNIFIED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {', '.join(missing)}")
    frame = frame.loc[:, UNIFIED_COLUMNS].copy()
    temp = f"{target}_staging_{load_date.strftime('%Y%m%d')}"
    job = client.load_table_from_dataframe(
        frame,
        temp,
        job_config=bigquery.LoadJobConfig(
            schema=table_schema(), write_disposition="WRITE_TRUNCATE"
        ),
    )
    job.result()
    query = f"""BEGIN TRANSACTION;
DELETE FROM `{target}` WHERE order_date = @load_date;
INSERT INTO `{target}` ({', '.join(UNIFIED_COLUMNS)})
SELECT {', '.join(UNIFIED_COLUMNS)} FROM `{temp}`;
COMMIT TRANSACTION;"""
    client.query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("load_date", "DATE", load_date)]
        ),
    ).result()
    client.delete_table(temp, not_found_ok=True)
    return len(frame)
