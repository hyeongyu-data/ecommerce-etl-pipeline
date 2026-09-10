from datetime import date

import pandas as pd

from ecommerce_etl.duckdb import replace_date


def test_replace_date_is_idempotent_and_reorders(tmp_path):
    frame = pd.read_parquet("data/staging/ga4/order_date=2026-09-01/orders.parquet").head(1)
    frame = frame.iloc[:, ::-1]
    assert replace_date(tmp_path / "x.duckdb", frame, date(2026, 9, 1)) == 1
    assert replace_date(tmp_path / "x.duckdb", frame, date(2026, 9, 1)) == 1
