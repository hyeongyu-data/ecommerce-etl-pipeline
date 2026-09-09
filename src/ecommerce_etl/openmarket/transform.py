"""오픈마켓 원천 JSON → 통합 order-line 스키마 (docs/SCHEMA.md §2-2).

carts(cart 단위) 와 products(카탈로그) 를 조인해 라인 단위 레코드로 편다.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pandas as pd

from ecommerce_etl import schema


def _hash(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _to_utc(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tz is None else ts.tz_convert("UTC")


def transform(
    carts: list[dict],
    products: list[dict],
    *,
    source_file: str | None = None,
    ingested_at: datetime | None = None,
) -> pd.DataFrame:
    ingested_at = ingested_at or datetime.now(UTC)
    ingested_ts = pd.Timestamp(ingested_at).tz_convert("UTC")
    source_file = source_file or "openmarket_api"
    prod_by_id = {p["id"]: p for p in products}

    records: list[dict] = []
    for cart in carts:
        cart_id = str(cart["id"])
        order_id = f"openmarket:{cart_id}"
        ordered_at = _to_utc(cart["date"])
        order_date = ordered_at.tz_convert(schema.REPORT_TZ).date()
        customer_id = _hash(cart["userId"])
        for line_no, line in enumerate(cart["products"], start=1):
            prod = prod_by_id.get(line["productId"], {})
            qty = int(line["quantity"])
            unit_price = prod.get("price")
            records.append(
                {
                    "source": "openmarket",
                    "source_order_id": cart_id,
                    "order_id": order_id,
                    "order_line_id": f"{order_id}#{line_no}",
                    "line_no": line_no,
                    "ordered_at": ordered_at,
                    "order_date": order_date,
                    "customer_id": customer_id,
                    "product_id": str(line["productId"]),
                    "product_name": prod.get("title"),
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_amount": qty * unit_price if unit_price is not None else None,
                    "currency": "KRW",
                    "channel": "openmarket",
                    "event_name": "order",
                    "source_file": source_file,
                    "ingested_at": ingested_ts,
                }
            )

    df = pd.DataFrame.from_records(records, columns=list(schema.UNIFIED_COLUMNS))
    non_object = {c: t for c, t in schema.PANDAS_DTYPES.items() if t != "object"}
    return df.astype(non_object)
