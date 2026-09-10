from datetime import date

import pytest

bigquery = pytest.importorskip("google.cloud.bigquery")

from ecommerce_etl.bigquery import _validate_identifier, table_schema  # noqa: E402


def test_bigquery_schema_matches_unified_columns():
    assert [field.name for field in table_schema()] == [
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
    ]


def test_identifier_rejects_injection():
    with pytest.raises(ValueError):
        _validate_identifier("orders; DROP TABLE users", "테이블")


def test_date_format_is_stable():
    assert date(2026, 9, 1).strftime("%Y%m%d") == "20260901"
