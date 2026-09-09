"""상품 카탈로그 — 여러 판매 채널(pg·openmarket)이 공유한다.

같은 상품이 여러 채널에서 팔리는 것을 흉내낸다. 금액은 KRW 정수(docs/SCHEMA.md §4-3).
"""

from __future__ import annotations

from typing import NamedTuple


class Product(NamedTuple):
    product_id: str
    name: str
    unit_price: int  # KRW


CATALOG: tuple[Product, ...] = (
    Product("P001", "무선 이어폰", 89000),
    Product("P002", "보조배터리 10000mAh", 24900),
    Product("P003", "USB-C 케이블 2m", 8900),
    Product("P004", "스마트워치 밴드", 15900),
    Product("P005", "블루투스 스피커", 43000),
    Product("P006", "노트북 파우치 15인치", 27000),
    Product("P007", "기계식 키보드", 119000),
    Product("P008", "무선 마우스", 32000),
    Product("P009", "모니터 받침대", 21000),
    Product("P010", "웹캠 1080p", 54000),
)

BY_ID: dict[str, Product] = {p.product_id: p for p in CATALOG}
