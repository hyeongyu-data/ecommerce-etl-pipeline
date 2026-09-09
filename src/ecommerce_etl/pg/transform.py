"""PG 원천 CSV → 통합 order-line 스키마 (docs/SCHEMA.md §2-1)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ecommerce_etl import schema


def _hash_customer(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def transform(
    raw_csv: str | Path,
    *,
    source_file: str | None = None,
    ingested_at: datetime | None = None,
) -> pd.DataFrame:
    """원천 CSV를 통합 스키마 DataFrame(컬럼 순서·dtype 고정)으로 변환한다."""
    raw_csv = Path(raw_csv)
    src = pd.read_csv(
        raw_csv,
        dtype={
            "order_id": "string",
            "customer_id": "string",
            "product_id": "string",
            "product_name": "string",
        },
    )
    ingested_at = ingested_at or datetime.now(UTC)
    source_file = source_file or raw_csv.name

    ordered_at = pd.to_datetime(src["ordered_at"], utc=True)

    out = pd.DataFrame(index=src.index)
    out["source"] = "pg"
    out["source_order_id"] = src["order_id"]
    out["order_id"] = ("pg:" + src["order_id"]).astype("string")
    out["line_no"] = src.groupby("order_id").cumcount() + 1
    out["order_line_id"] = (out["order_id"] + "#" + out["line_no"].astype("string")).astype(
        "string"
    )
    out["ordered_at"] = ordered_at
    out["order_date"] = ordered_at.dt.tz_convert(schema.REPORT_TZ).dt.date
    out["customer_id"] = src["customer_id"].map(_hash_customer).astype("string")
    out["product_id"] = src["product_id"]
    out["product_name"] = src["product_name"]
    out["quantity"] = src["quantity"].astype("Int64")
    out["unit_price"] = src["unit_price"].astype("Int64")
    out["line_amount"] = (out["quantity"] * out["unit_price"]).astype("Int64")
    out["currency"] = "KRW"
    out["channel"] = pd.NA
    out["event_name"] = "order"
    out["source_file"] = source_file
    out["ingested_at"] = pd.Timestamp(ingested_at).tz_convert("UTC")

    out = out[list(schema.UNIFIED_COLUMNS)]
    non_object = {c: t for c, t in schema.PANDAS_DTYPES.items() if t != "object"}
    return out.astype(non_object)


def write_staging(df: pd.DataFrame, staging_dir: str | Path, order_date) -> Path:
    """`staging_dir/order_date=YYYY-MM-DD/orders.parquet` 로 쓴다. 경로를 반환."""
    part_dir = Path(staging_dir) / f"order_date={order_date.isoformat()}"
    part_dir.mkdir(parents=True, exist_ok=True)
    path = part_dir / "orders.parquet"
    df.to_parquet(path, index=False)
    return path
