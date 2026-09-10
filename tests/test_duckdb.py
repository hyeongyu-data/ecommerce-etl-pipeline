from datetime import date

import pandas as pd

from ecommerce_etl.duckdb import replace_date
from ecommerce_etl.schema import UNIFIED_COLUMNS


def test_replace_date_is_idempotent_and_reorders(tmp_path):
    frame = pd.DataFrame({column: [None] for column in UNIFIED_COLUMNS})
    frame.update(
        pd.DataFrame(
            [
                {
                    "source": "ga4",
                    "source_order_id": "s1",
                    "order_id": "o1",
                    "order_line_id": "l1",
                    "line_no": 1,
                    "ordered_at": pd.Timestamp("2026-09-01", tz="UTC"),
                    "order_date": date(2026, 9, 1),
                    "product_id": "p1",
                    "quantity": 1,
                    "line_amount": 0,
                    "currency": "KRW",
                    "ingested_at": pd.Timestamp("2026-09-01", tz="UTC"),
                }
            ]
        )
    )
    frame = frame.iloc[:, ::-1]
    assert replace_date(tmp_path / "x.duckdb", frame, date(2026, 9, 1)) == 1
    assert replace_date(tmp_path / "x.duckdb", frame, date(2026, 9, 1)) == 1
