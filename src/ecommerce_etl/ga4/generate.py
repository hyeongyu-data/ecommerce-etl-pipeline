"""인증 없이 재현 가능한 GA4 보고서 형태의 합성 자료. 실제 API 호출은 하지 않는다."""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

from ecommerce_etl import schema
from ecommerce_etl.catalog import CATALOG

DIMENSIONS = ("transactionId", "dateHour", "itemId", "itemName", "eventName", "currencyCode")
METRICS = ("itemsPurchased", "itemRevenue")


def generate_report(order_date: date, *, seed: int = 42) -> dict:
    """같은 날짜·시드에는 같은 보고서를 만든다. 주문 안의 상품은 중복되지 않는다."""
    rng = random.Random(seed ^ (order_date.toordinal() * 11))
    rows = []
    for i in range(1, rng.randint(15, 30) + 1):
        transaction_id = f"GA4-{order_date:%Y%m%d}-{i:04d}"
        date_hour = f"{order_date:%Y%m%d}{rng.randrange(24):02d}"
        for product in rng.sample(CATALOG, rng.randint(1, 3)):
            quantity = rng.randint(1, 5)
            dimensions = (
                transaction_id,
                date_hour,
                product.product_id,
                product.name,
                "purchase",
                "KRW",
            )
            rows.append(
                {
                    "dimensionValues": [{"value": v} for v in dimensions],
                    "metricValues": [
                        {"value": str(quantity)},
                        {"value": str(quantity * product.unit_price)},
                    ],
                }
            )
    return {
        "dimensionHeaders": [{"name": n} for n in DIMENSIONS],
        "metricHeaders": [{"name": n} for n in METRICS],
        "metadata": {"timeZone": schema.REPORT_TZ, "currencyCode": "KRW"},
        "rowCount": len(rows),
        "rows": rows,
    }


def write_json(order_date: date, raw_dir: str | Path, *, seed: int = 42) -> Path:
    """지정 날짜의 원천 보고서를 저장한다. 같은 날짜로 실행하면 덮어쓴다."""
    part_dir = Path(raw_dir) / f"order_date={order_date.isoformat()}"
    part_dir.mkdir(parents=True, exist_ok=True)
    path = part_dir / "report.json"
    path.write_text(
        json.dumps(generate_report(order_date, seed=seed), ensure_ascii=False), encoding="utf-8"
    )
    return path
