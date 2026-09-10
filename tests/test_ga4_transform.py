"""GA4 목업 보고서의 입력 계약·재실행·검증 전 저장 차단을 확인한다."""

import copy
import json
from datetime import UTC, date, datetime

import pandas as pd
import pytest

from ecommerce_etl import quality, schema
from ecommerce_etl.ga4 import generate, transform

DAY = date(2026, 9, 1)
INGESTED = datetime(2026, 9, 2, tzinfo=UTC)


@pytest.fixture
def report():
    # 생성기와 독립적인 입력으로 변환의 필드 의미를 검증한다.
    return {
        "dimensionHeaders": [
            {"name": n}
            for n in (
                "itemId",
                "transactionId",
                "dateHour",
                "currencyCode",
                "eventName",
                "itemName",
            )
        ],
        "metricHeaders": [{"name": "itemRevenue"}, {"name": "itemsPurchased"}],
        "metadata": {"timeZone": "Asia/Seoul", "currencyCode": "KRW"},
        "rowCount": 2,
        "rows": [
            {
                "dimensionValues": [
                    {"value": v} for v in ("P002", "T1", "2026090100", "KRW", "purchase", "케이블")
                ],
                "metricValues": [{"value": "17800.0"}, {"value": "2"}],
            },
            {
                "dimensionValues": [
                    {"value": v} for v in ("P001", "T1", "2026090100", "KRW", "purchase", "이어폰")
                ],
                "metricValues": [{"value": "89000"}, {"value": "1"}],
            },
        ],
    }


def convert(report):
    return transform.transform(report, order_date=DAY, ingested_at=INGESTED)


def test_mapping_and_kst_boundary(report):
    df = convert(report)
    assert list(df.columns) == list(schema.UNIFIED_COLUMNS)
    assert df["order_line_id"].tolist() == ["ga4:T1#1", "ga4:T1#2"]
    assert df["product_id"].tolist() == ["P001", "P002"]
    assert df["unit_price"].tolist() == [89000, 8900]
    assert df["line_amount"].tolist() == [89000, 17800]
    assert df["quantity"].tolist() == [1, 2]
    assert (df["ordered_at"] == pd.Timestamp("2026-08-31T15:00:00Z")).all()
    assert (df["order_date"] == DAY).all()
    assert df["customer_id"].isna().all() and df["channel"].isna().all()
    assert (df["event_name"] == "purchase").all()
    assert (df["source"] == "ga4").all()
    assert (df["currency"] == "KRW").all()
    assert quality.check(df, max_violation_rate=0).passed


def test_reordering_headers_and_rows_preserves_output(report):
    expected = convert(report)
    for headers, values in (
        ("dimensionHeaders", "dimensionValues"),
        ("metricHeaders", "metricValues"),
    ):
        report[headers].reverse()
        for row in report["rows"]:
            row[values].reverse()
    report["rows"].reverse()
    pd.testing.assert_frame_equal(convert(report), expected)


def test_generation_is_deterministic_and_valid(tmp_path):
    original = generate.generate_report(DAY)
    assert original == generate.generate_report(DAY)
    assert original != generate.generate_report(DAY, seed=43)
    other = generate.generate_report(date(2026, 9, 2))
    assert set(convert(original)["order_id"]).isdisjoint(
        transform.transform(other, order_date=date(2026, 9, 2))["order_id"]
    )
    assert quality.check(convert(original), max_violation_rate=0).passed
    path = generate.write_json(DAY, tmp_path)
    assert json.loads(path.read_text()) == original
    before = path.read_bytes()
    generate.write_json(DAY, tmp_path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("headers", ["dimensionHeaders", "metricHeaders"])
@pytest.mark.parametrize("kind", ["missing", "duplicate", "extra", "invalid"])
def test_rejects_broken_headers(report, headers, kind):
    if kind == "missing":
        report[headers].pop()
    elif kind == "duplicate":
        report[headers][1] = report[headers][0]
    elif kind == "extra":
        report[headers].append({"name": "unknown"})
    else:
        report[headers] = None
    with pytest.raises(ValueError, match="헤더"):
        convert(report)


@pytest.mark.parametrize("field", ["dimensionValues", "metricValues"])
@pytest.mark.parametrize("kind", ["short", "missing_value", "not_string", "not_list"])
def test_rejects_malformed_row_values(report, field, kind):
    values = report["rows"][0][field]
    if kind == "short":
        values.pop()
    elif kind == "missing_value":
        values[0] = {}
    elif kind == "not_string":
        values[0] = {"value": 1}
    else:
        report["rows"][0][field] = None
    with pytest.raises(ValueError, match="행"):
        convert(report)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("itemId", ""),
        ("transactionId", " "),
        ("transactionId", "(not set)"),
        ("dateHour", "202609010"),
        ("dateHour", "2026090124"),
        ("dateHour", "2026023000"),
        ("dateHour", "2026090200"),
        ("dateHour", "2026090101"),  # 동일 거래의 다른 행과 시각 불일치
        ("currencyCode", "USD"),
        ("eventName", "refund"),
    ],
)
def test_rejects_invalid_dimensions(report, field, value):
    index = [h["name"] for h in report["dimensionHeaders"]].index(field)
    report["rows"][0]["dimensionValues"][index]["value"] = value
    with pytest.raises(ValueError):
        convert(report)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("itemsPurchased", "0"),
        ("itemsPurchased", "-1"),
        ("itemsPurchased", "1.5"),
        ("itemsPurchased", "NaN"),
        ("itemsPurchased", "1e1000000"),
        ("itemsPurchased", str(2**63)),
        ("itemRevenue", str(2**63)),
        ("itemRevenue", "Infinity"),
        ("itemRevenue", "-1"),
        ("itemRevenue", "1.5"),
        ("itemRevenue", "17801"),
    ],
)
def test_rejects_invalid_metrics(report, field, value):
    index = [h["name"] for h in report["metricHeaders"]].index(field)
    report["rows"][0]["metricValues"][index]["value"] = value
    with pytest.raises(ValueError):
        convert(report)


def test_duplicate_transaction_product_is_not_silently_aggregated(report):
    report["rows"].append(copy.deepcopy(report["rows"][0]))
    report["rowCount"] += 1
    with pytest.raises(ValueError, match="중복"):
        convert(report)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("rows", None),
        ("rows", [None, None]),
        ("rowCount", 1),
        ("rowCount", True),
        ("metadata", {}),
        ("metadata", {"timeZone": "UTC", "currencyCode": "KRW"}),
        ("metadata", {"timeZone": "Asia/Seoul", "currencyCode": "USD"}),
    ],
)
def test_rejects_incomplete_or_wrong_report(report, key, value):
    report[key] = value
    with pytest.raises(ValueError):
        convert(report)


def test_staging_rerun_and_empty_report(report, tmp_path):
    raw = tmp_path / "report.json"
    raw.write_text(json.dumps(report))
    path = transform.validate_and_stage(raw, tmp_path / "staging", DAY, ingested_at=INGESTED)
    before = pd.read_parquet(path)
    assert before["source_file"].tolist() == [raw.as_posix()] * 2
    later = datetime(2026, 9, 3, tzinfo=UTC)
    assert transform.validate_and_stage(raw, tmp_path / "staging", DAY, ingested_at=later) == path
    after = pd.read_parquet(path)
    pd.testing.assert_frame_equal(
        before.drop(columns="ingested_at"), after.drop(columns="ingested_at")
    )
    assert (after["ingested_at"] == pd.Timestamp(later)).all()

    report["rows"] = []
    report["rowCount"] = 0
    raw.write_text(json.dumps(report))
    transform.validate_and_stage(raw, tmp_path / "staging", DAY, ingested_at=INGESTED)
    empty = pd.read_parquet(path)
    assert empty.empty
    assert list(empty.columns) == list(schema.UNIFIED_COLUMNS)
    assert empty.dtypes.equals(before.dtypes)


@pytest.mark.parametrize("kind", ["invalid_json", "wrong_shape", "bad_row", "future_order"])
def test_failure_preserves_raw_and_existing_staging(report, tmp_path, kind):
    raw = tmp_path / "report.json"
    raw.write_text(json.dumps(report))
    staging_dir = tmp_path / "staging"
    path = transform.validate_and_stage(raw, staging_dir, DAY, ingested_at=INGESTED)
    before = path.read_bytes()
    ingested = INGESTED
    if kind == "invalid_json":
        raw.write_text('{"비공개-입력값":')
    elif kind == "wrong_shape":
        raw.write_text("null")
    elif kind == "bad_row":
        report["rows"][0]["metricValues"][0]["value"] = "비공개-입력값"
        raw.write_text(json.dumps(report))
    else:
        ingested = datetime(2026, 8, 31, tzinfo=UTC)
    raw_before = raw.read_bytes()
    with pytest.raises(ValueError) as exc:
        transform.validate_and_stage(raw, staging_dir, DAY, ingested_at=ingested)
    assert "비공개-입력값" not in str(exc.value)
    assert path.read_bytes() == before
    assert raw.read_bytes() == raw_before
    with pytest.raises(ValueError):
        transform.validate_and_stage(raw, tmp_path / "new_staging", DAY, ingested_at=ingested)
    assert not (tmp_path / "new_staging").exists()


def test_ingestion_requires_timezone(report):
    with pytest.raises(ValueError, match="적재 시각"):
        transform.transform(report, order_date=DAY, ingested_at=datetime(2026, 9, 2))
