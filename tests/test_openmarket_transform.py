"""오픈마켓 원천 JSON → 통합 스키마 변환 검증."""

import re
from datetime import date

import pandas as pd
import pytest

from ecommerce_etl import quality, schema
from ecommerce_etl.openmarket import transform

HEX64 = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture
def sample():
    products = [
        {"id": 1, "title": "무선 이어폰", "price": 89000},
        {"id": 2, "title": "USB-C 케이블 2m", "price": 8900},
    ]
    carts = [
        {
            "id": 20260901001,
            "userId": 7,
            "date": "2026-09-01T14:23:11+09:00",
            "products": [{"productId": 1, "quantity": 2}, {"productId": 2, "quantity": 1}],
        },
        {
            "id": 20260901002,
            "userId": 12,
            "date": "2026-09-01T02:05:00+09:00",  # KST 새벽 → UTC 전날, order_date는 KST 기준
            "products": [{"productId": 1, "quantity": 1}],
        },
    ]
    return carts, products


def test_columns_and_constants(sample):
    df = transform.transform(*sample)
    assert list(df.columns) == list(schema.UNIFIED_COLUMNS)
    assert (df["source"] == "openmarket").all()
    assert (df["channel"] == "openmarket").all()
    assert (df["event_name"] == "order").all()
    assert (df["currency"] == "KRW").all()


def test_keys_join_amounts(sample):
    df = transform.transform(*sample)
    assert df["order_line_id"].is_unique
    assert df["order_id"].str.startswith("openmarket:").all()
    assert (df["line_amount"] == df["quantity"] * df["unit_price"]).all()
    row = df.loc[df["order_line_id"] == "openmarket:20260901001#1"].iloc[0]
    assert row["product_name"] == "무선 이어폰"
    assert row["unit_price"] == 89000
    assert row["line_amount"] == 178000


def test_customer_hashed_and_order_date(sample):
    df = transform.transform(*sample)
    assert df["customer_id"].map(lambda v: bool(HEX64.match(v))).all()
    assert (df["order_date"] == date(2026, 9, 1)).all()
    assert df["order_date"].map(lambda v: isinstance(v, date)).all()


def test_line_no_per_cart(sample):
    df = transform.transform(*sample)
    for _, g in df.groupby("order_id"):
        assert list(g["line_no"]) == list(range(1, len(g) + 1))


def test_quality_passes(sample):
    result = quality.check(transform.transform(*sample))
    assert result.passed, result.violations


def test_empty_carts():
    df = transform.transform([], [{"id": 1, "title": "x", "price": 1}])
    assert list(df.columns) == list(schema.UNIFIED_COLUMNS)
    assert len(df) == 0
    assert isinstance(df, pd.DataFrame)
