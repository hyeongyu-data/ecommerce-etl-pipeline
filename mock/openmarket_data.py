"""로컬 목업 오픈마켓 API가 서빙하는 결정론적 데이터 (fakestore 형태).

products 는 공용 카탈로그(ecommerce_etl.catalog)에서 파생하고, carts 는 날짜·시드로
결정론적으로 만든다.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from ecommerce_etl.catalog import CATALOG

KST = timezone(timedelta(hours=9))

# fakestore 형태 products: 카탈로그 인덱스 → 정수 id (P001 → 1 ...)
PRODUCTS: list[dict] = [
    {"id": i + 1, "title": p.name, "price": p.unit_price, "category": "electronics"}
    for i, p in enumerate(CATALOG)
]
_PRODUCT_IDS = [p["id"] for p in PRODUCTS]


def carts_for_date(order_date: date, *, seed: int = 42) -> list[dict]:
    """지정 날짜의 fakestore 형태 cart 목록. (order_date, seed) 에 결정론적."""
    rng = random.Random(seed ^ (order_date.toordinal() * 7))
    midnight = datetime.combine(order_date, datetime.min.time(), tzinfo=KST)
    carts: list[dict] = []
    for i in range(1, rng.randint(15, 30) + 1):
        ordered_at = midnight + timedelta(seconds=rng.randint(0, 86399))
        lines = [
            {"productId": rng.choice(_PRODUCT_IDS), "quantity": rng.randint(1, 5)}
            for _ in range(rng.randint(1, 4))
        ]
        carts.append(
            {
                "id": int(f"{order_date:%Y%m%d}{i:03d}"),
                "userId": rng.randint(1, 50),
                "date": ordered_at.isoformat(),
                "products": lines,
            }
        )
    return carts


def carts_between(start: date, end: date, *, seed: int = 42) -> list[dict]:
    out: list[dict] = []
    day = start
    while day <= end:
        out.extend(carts_for_date(day, seed=seed))
        day += timedelta(days=1)
    return out
