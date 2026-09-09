"""합성 PG 주문 원천 데이터 생성.

실제 Kaggle Olist 대신 결정론적 생성기를 쓴다(인증·라이선스 없이 누구나 재현).
원천 CSV는 PG 시스템의 주문 라인 export를 흉내낸다: 주문 1건이 여러 상품 행으로 나뉜다.
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))

# (product_id, product_name, unit_price KRW). 금액은 KRW 정수(docs/SCHEMA.md §4-3).
_CATALOG: tuple[tuple[str, str, int], ...] = (
    ("P001", "무선 이어폰", 89000),
    ("P002", "보조배터리 10000mAh", 24900),
    ("P003", "USB-C 케이블 2m", 8900),
    ("P004", "스마트워치 밴드", 15900),
    ("P005", "블루투스 스피커", 43000),
    ("P006", "노트북 파우치 15인치", 27000),
    ("P007", "기계식 키보드", 119000),
    ("P008", "무선 마우스", 32000),
    ("P009", "모니터 받침대", 21000),
    ("P010", "웹캠 1080p", 54000),
)

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
            product_id, product_name, unit_price = rng.choice(_CATALOG)
            rows.append(
                {
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "ordered_at": ordered_at,
                    "product_id": product_id,
                    "product_name": product_name,
                    "quantity": rng.randint(1, 5),
                    "unit_price": unit_price,
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
