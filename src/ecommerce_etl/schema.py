"""통합 주문 스키마 (order-line grain) — 단일 출처.

`docs/SCHEMA.md` 의 §1 표와 그 안의 ```sql DDL 블록이 이 정의와 일치해야 한다.
`tests/test_schema.py` 가 세 곳의 일치를 검증한다.
"""

from __future__ import annotations

# staging 파일의 컬럼 순서이기도 하다.
UNIFIED_COLUMNS: tuple[str, ...] = (
    "source",
    "source_order_id",
    "order_id",
    "order_line_id",
    "line_no",
    "ordered_at",
    "order_date",
    "customer_id",
    "product_id",
    "product_name",
    "quantity",
    "unit_price",
    "line_amount",
    "currency",
    "channel",
    "event_name",
    "source_file",
    "ingested_at",
)

# NULL 허용 컬럼 (docs/SCHEMA.md §1 의 Null=Y)
NULLABLE: frozenset[str] = frozenset(
    {
        "customer_id",
        "product_name",
        "unit_price",
        "channel",
        "event_name",
        "source_file",
    }
)

# 필수(NOT NULL) 컬럼
REQUIRED: tuple[str, ...] = tuple(c for c in UNIFIED_COLUMNS if c not in NULLABLE)

SOURCES: tuple[str, ...] = ("pg", "openmarket", "ga4")

# 파티션·기준일 시간대
REPORT_TZ = "Asia/Seoul"

# pandas dtype. 문자열 표기라 이 모듈은 pandas import가 필요 없다.
# 금액은 이 프로젝트에서 KRW 정수로만 다룬다(docs/SCHEMA.md §4-3) → Int64.
PANDAS_DTYPES: dict[str, str] = {
    "source": "string",
    "source_order_id": "string",
    "order_id": "string",
    "order_line_id": "string",
    "line_no": "Int64",
    "ordered_at": "datetime64[ns, UTC]",
    "order_date": "object",  # datetime.date
    "customer_id": "string",
    "product_id": "string",
    "product_name": "string",
    "quantity": "Int64",
    "unit_price": "Int64",
    "line_amount": "Int64",
    "currency": "string",
    "channel": "string",
    "event_name": "string",
    "source_file": "string",
    "ingested_at": "datetime64[ns, UTC]",
}
