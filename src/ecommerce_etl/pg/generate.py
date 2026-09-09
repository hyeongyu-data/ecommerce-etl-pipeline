"""합성 PG 주문 원천 데이터 생성.

실제 Kaggle Olist 대신 결정론적 생성기를 쓴다(인증·라이선스 없이 누구나 재현).
원천 CSV는 PG 시스템의 주문 라인 export를 흉내낸다: 주문 1건이 여러 상품 행으로 나뉜다.
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ecommerce_etl.catalog import CATALOG

KST = timezone(timedelta(hours=9))

RAW_COLUMNS: tuple[str, ...] = (
    "order_id",
    "customer_id",
    "ordered_at",
    "product_id",
    "product_name",
    "quantity",
    "unit_price",
)


def generate_rows(order_date: date, *, seed: int = 42) -> list[dict[str, object]]:
    """지정 날짜의 합성 PG 주문 라인들. (order_date, seed) 에 대해 결정론적."""
    rng = random.Random(seed ^ order_date.toordinal())
    n_orders = rng.randint(20, 40)
    rows: list[dict[str, object]] = []
    midnight = datetime.combine(order_date, datetime.min.time(), tzinfo=KST)
    for i in range(1, n_orders + 1):
        order_id = f"PG-{order_date:%Y%m%d}-{i:04d}"
        customer_id = f"C{rng.randint(1, 500):04d}"
        ordered_at = (midnight + timedelta(seconds=rng.randint(0, 86399))).isoformat()
        for _ in range(rng.randint(1, 3)):
            product = rng.choice(CATALOG)
            rows.append(
                {
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "ordered_at": ordered_at,
                    "product_id": product.product_id,
                    "product_name": product.name,
                    "quantity": rng.randint(1, 5),
                    "unit_price": product.unit_price,
                }
            )
    return rows


def write_csv(order_date: date, raw_dir: str | Path, *, seed: int = 42) -> Path:
    """`raw_dir/order_date=YYYY-MM-DD/orders.csv` 로 원천 CSV를 쓴다(있으면 덮어씀)."""
    part_dir = Path(raw_dir) / f"order_date={order_date.isoformat()}"
    part_dir.mkdir(parents=True, exist_ok=True)
    path = part_dir / "orders.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS)
        writer.writeheader()
        writer.writerows(generate_rows(order_date, seed=seed))
    return path
