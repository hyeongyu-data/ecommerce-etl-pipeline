"""데이터 품질 검사(Q1~Q7) 검증."""

from datetime import date, timedelta

import pandas as pd
import pytest

from ecommerce_etl import quality, schema
from ecommerce_etl.pg import generate, transform


@pytest.fixture
def clean(tmp_path):
    csv = generate.write_csv(date(2026, 9, 1), tmp_path / "raw", seed=7)
    return transform.transform(csv)


def test_clean_passes(clean):
    r = quality.check(clean)
    assert r.passed
    assert r.bad_rows == 0
    assert r.violations == {}


def test_q1_null_required(clean):
    clean.loc[clean.index[0], "product_id"] = None
    r = quality.check(clean, max_violation_rate=0.0)
    assert not r.passed
    assert "Q1:product_id_null" in r.violations


def test_q2_duplicate_line_id(clean):
    clean.loc[clean.index[1], "order_line_id"] = clean.loc[clean.index[0], "order_line_id"]
    r = quality.check(clean, max_violation_rate=0.0)
    assert "Q2:order_line_id_dup" in r.violations
    assert r.violations["Q2:order_line_id_dup"] == 2


def test_q4_amount_mismatch(clean):
    clean.loc[clean.index[0], "line_amount"] = clean.loc[clean.index[0], "line_amount"] + 100
    r = quality.check(clean, max_violation_rate=0.0)
    assert "Q4:amount_mismatch" in r.violations


def test_q7_future_order(clean):
    clean.loc[clean.index[0], "ordered_at"] = clean["ingested_at"].iloc[0] + timedelta(days=1)
    r = quality.check(clean, max_violation_rate=0.0)
    assert "Q7:future_order" in r.violations


def test_threshold_tolerates_small_violation_rate(clean):
    clean.loc[clean.index[0], "line_amount"] = 999_999_999
    # 1행만 위반 → 비율이 임계 이하면 통과
    r = quality.check(clean, max_violation_rate=0.5)
    assert r.passed
    assert r.bad_rows == 1


def test_empty_frame():
    r = quality.check(pd.DataFrame(columns=list(schema.UNIFIED_COLUMNS)))
    assert r.total == 0
    assert r.passed
