"""데이터 품질 검사 (docs/SCHEMA.md §3, Q1~Q7).

적재 전 staging DataFrame을 검사한다. 위반 행 비율이 임계를 넘으면 `passed=False`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ecommerce_etl import schema


@dataclass
class QualityResult:
    total: int
    bad_rows: int
    violation_rate: float
    passed: bool
    violations: dict[str, int]


def check(df: pd.DataFrame, *, max_violation_rate: float = 0.01) -> QualityResult:
    total = len(df)
    if total == 0:
        return QualityResult(total=0, bad_rows=0, violation_rate=0.0, passed=True, violations={})

    bad = pd.Series(False, index=df.index)
    violations: dict[str, int] = {}

    def record(name: str, mask: pd.Series) -> None:
        nonlocal bad
        mask = mask.fillna(False).astype(bool)
        cnt = int(mask.sum())
        if cnt:
            violations[name] = cnt
        bad = bad | mask

    # Q1: 필수 컬럼 NOT NULL
    for col in schema.REQUIRED:
        record(f"Q1:{col}_null", df[col].isna())

    # Q2: order_line_id 유니크
    record("Q2:order_line_id_dup", df["order_line_id"].duplicated(keep=False))

    # Q3: 값 범위
    record("Q3:quantity", ~(df["quantity"] > 0))
    record("Q3:unit_price", df["unit_price"].notna() & (df["unit_price"] < 0))
    record("Q3:line_amount", ~(df["line_amount"] >= 0))

    # Q4: line_amount == quantity * unit_price (허용 오차 1)
    expected = df["quantity"] * df["unit_price"]
    record("Q4:amount_mismatch", (df["line_amount"] - expected).abs() > 1)

    # Q5: order_date == ordered_at 의 Asia/Seoul 날짜
    kst_date = df["ordered_at"].dt.tz_convert(schema.REPORT_TZ).dt.date
    record("Q5:order_date_derive", df["order_date"] != kst_date)

    # Q6: 허용된 source 값만
    record("Q6:source", ~df["source"].isin(schema.SOURCES))

    # Q7: 미래 시각 주문 차단
    record("Q7:future_order", df["ordered_at"] > df["ingested_at"])

    bad_rows = int(bad.sum())
    rate = bad_rows / total if total else 0.0
    return QualityResult(
        total=total,
        bad_rows=bad_rows,
        violation_rate=rate,
        passed=rate <= max_violation_rate,
        violations=violations,
    )
