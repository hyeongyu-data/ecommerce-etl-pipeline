"""PG 생성기 + 통합 스키마 변환 검증."""

import re
from datetime import date

import pandas as pd
import pytest

from ecommerce_etl import schema, staging
from ecommerce_etl.pg import generate, transform

HEX64 = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture
def df(tmp_path):
    csv = generate.write_csv(date(2026, 9, 1), tmp_path / "raw", seed=42)
    return transform.transform(csv, source_file="orders.csv")


def test_generate_is_deterministic(tmp_path):
    a = generate.generate_rows(date(2026, 9, 1), seed=42)
    b = generate.generate_rows(date(2026, 9, 1), seed=42)
    assert a == b
    assert a != generate.generate_rows(date(2026, 9, 2), seed=42)


def test_columns_and_constants(df):
    assert list(df.columns) == list(schema.UNIFIED_COLUMNS)
    assert (df["source"] == "pg").all()
    assert (df["currency"] == "KRW").all()
    assert (df["event_name"] == "order").all()
    assert df["channel"].isna().all()


def test_keys_and_amounts(df):
    assert df["order_line_id"].is_unique
    assert df["order_id"].str.startswith("pg:").all()
    assert (df["order_line_id"] == df["order_id"] + "#" + df["line_no"].astype("string")).all()
    assert (df["line_amount"] == df["quantity"] * df["unit_price"]).all()
    # 주문별 line_no는 1부터 연속
    for _, g in df.groupby("order_id"):
        assert list(g["line_no"]) == list(range(1, len(g) + 1))


def test_customer_id_is_hashed(df):
    assert df["customer_id"].map(lambda v: bool(HEX64.match(v))).all()


def test_order_date_is_kst_date(df):
    kst = df["ordered_at"].dt.tz_convert(schema.REPORT_TZ).dt.date
    assert (df["order_date"] == kst).all()
    assert df["order_date"].map(lambda v: isinstance(v, date)).all()


def test_roundtrip_parquet(df, tmp_path):
    path = staging.write_parquet(df, tmp_path / "staging", date(2026, 9, 1))
    back = pd.read_parquet(path)
    assert list(back.columns) == list(schema.UNIFIED_COLUMNS)
    assert len(back) == len(df)
