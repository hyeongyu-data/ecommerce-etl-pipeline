"""단일 날짜의 GA4 목업 보고서를 검증하고 통합 주문 라인으로 변환한다.

보고서 행은 원본 이벤트의 items 배열이 아니다. 거래별 상품 ID 정렬로 라인 번호를 만든다.
오류 메시지에는 원천 값이나 응답 전문을 넣지 않는다.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ecommerce_etl import quality, schema, staging
from ecommerce_etl.ga4.generate import DIMENSIONS, METRICS


def _headers(value: object, expected: tuple[str, ...]) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(h, dict) or not isinstance(h.get("name"), str) for h in value
    ):
        raise ValueError("보고서 헤더 형식이 잘못되었습니다")
    names = [h["name"] for h in value]
    if len(names) != len(expected) or set(names) != set(expected):
        raise ValueError("보고서 헤더에 누락·중복·미지원 항목이 있습니다")
    return names


def _values(value: object, names: list[str]) -> dict[str, str]:
    if (
        not isinstance(value, list)
        or len(value) != len(names)
        or any(not isinstance(v, dict) or not isinstance(v.get("value"), str) for v in value)
    ):
        raise ValueError("보고서 행의 값 형식 또는 개수가 잘못되었습니다")
    return {name: cell["value"] for name, cell in zip(names, value, strict=True)}


def _integer(value: str) -> int:
    # 큰 지수·무한대·NaN 및 정수 범위 초과를 pandas 변환 전에 차단한다.
    if len(value) > 64 or re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) is None:
        raise ValueError("수량·금액은 0 이상의 정수여야 합니다")
    number = Decimal(value)
    if number != number.to_integral_value() or number > 2**63 - 1:
        raise ValueError("수량·금액이 Int64 정수 범위를 벗어났습니다")
    return int(number)


def transform(
    report: dict,
    *,
    order_date: date,
    source_file: str = "ga4_mock_report",
    ingested_at: datetime | None = None,
) -> pd.DataFrame:
    """KST·KRW 단일 날짜 보고서만 허용한다. 손상된 응답은 빈 보고서로 대체하지 않는다."""
    if not isinstance(report, dict):
        raise ValueError("보고서는 객체여야 합니다")
    dimensions = _headers(report.get("dimensionHeaders"), DIMENSIONS)
    metrics = _headers(report.get("metricHeaders"), METRICS)
    metadata = report.get("metadata")
    if not isinstance(metadata, dict) or (
        metadata.get("timeZone") != schema.REPORT_TZ or metadata.get("currencyCode") != "KRW"
    ):
        raise ValueError("보고서 메타데이터는 Asia/Seoul 시간대·KRW 통화여야 합니다")
    rows = report.get("rows")
    count = report.get("rowCount")
    if not isinstance(rows, list) or type(count) is not int or count != len(rows):
        raise ValueError("보고서 행 목록과 rowCount가 일치해야 합니다")

    ingested = pd.Timestamp(ingested_at or datetime.now(UTC))
    if pd.isna(ingested) or ingested.tzinfo is None:
        raise ValueError("적재 시각은 시간대가 있는 유효한 시각이어야 합니다")
    ingested = ingested.tz_convert("UTC")
    records = []
    seen = set()
    order_times = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("보고서 행은 객체여야 합니다")
        dim = _values(row.get("dimensionValues"), dimensions)
        metric = _values(row.get("metricValues"), metrics)
        transaction_id, product_id = dim["transactionId"], dim["itemId"]
        if any(not v.strip() or v.strip() == "(not set)" for v in (transaction_id, product_id)):
            raise ValueError("거래·상품 식별자가 누락되었습니다")
        if dim["eventName"] != "purchase" or dim["currencyCode"] != "KRW":
            raise ValueError("purchase·KRW 보고서만 허용합니다")
        if re.fullmatch(r"[0-9]{10}", dim["dateHour"]) is None:
            raise ValueError("dateHour는 YYYYMMDDHH 형식이어야 합니다")
        try:
            local_time = datetime.strptime(dim["dateHour"], "%Y%m%d%H")
        except ValueError:
            raise ValueError("dateHour에 유효하지 않은 날짜·시간이 있습니다") from None
        if local_time.date() != order_date:
            raise ValueError("보고서 행이 대상 날짜를 벗어났습니다")
        ordered_at = pd.Timestamp(local_time).tz_localize(schema.REPORT_TZ).tz_convert("UTC")
        if transaction_id in order_times and order_times[transaction_id] != ordered_at:
            raise ValueError("같은 거래의 주문 시각이 일치하지 않습니다")
        order_times[transaction_id] = ordered_at
        key = (transaction_id, product_id)
        if key in seen:
            raise ValueError("거래 내 상품이 중복되었습니다")
        seen.add(key)
        quantity = _integer(metric["itemsPurchased"])
        amount = _integer(metric["itemRevenue"])
        if quantity == 0 or amount % quantity:
            raise ValueError("수량은 양수이며 금액을 수량으로 나눈 단가는 정수여야 합니다")
        records.append(
            {
                "source": "ga4",
                "source_order_id": transaction_id,
                "order_id": f"ga4:{transaction_id}",
                "ordered_at": ordered_at,
                "order_date": order_date,
                "customer_id": pd.NA,
                "product_id": product_id,
                "product_name": dim["itemName"] or pd.NA,
                "quantity": quantity,
                "unit_price": amount // quantity,
                "line_amount": amount,
                "currency": "KRW",
                "channel": pd.NA,
                "event_name": "purchase",
                "source_file": source_file,
                "ingested_at": ingested,
            }
        )
    # API 응답 순서나 페이지 순서에 라인 키가 의존하지 않게 한다.
    records.sort(key=lambda r: (r["source_order_id"], r["product_id"]))
    line_counts = {}
    for record in records:
        order_id = record["order_id"]
        line_counts[order_id] = line_counts.get(order_id, 0) + 1
        record["line_no"] = line_counts[order_id]
        record["order_line_id"] = f"{order_id}#{record['line_no']}"
    df = pd.DataFrame.from_records(records, columns=list(schema.UNIFIED_COLUMNS))
    return df.astype({c: t for c, t in schema.PANDAS_DTYPES.items() if t != "object"})


def validate_and_stage(
    raw_json: str | Path,
    staging_dir: str | Path,
    order_date: date,
    *,
    ingested_at: datetime | None = None,
) -> Path:
    """원천은 보존하고, 입력·Q1~Q7 검증을 모두 통과한 경우에만 결과를 쓴다."""
    raw_json = Path(raw_json)
    try:
        report = json.loads(raw_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("원천 보고서가 유효한 UTF-8 JSON이 아닙니다") from None
    df = transform(
        report, order_date=order_date, source_file=raw_json.as_posix(), ingested_at=ingested_at
    )
    result = quality.check(df, max_violation_rate=0.0)
    if not result.passed:
        raise ValueError(f"GA4 품질검사 실패: {result.bad_rows}/{result.total}행 위반")
    return staging.write_parquet(df, staging_dir, order_date)
