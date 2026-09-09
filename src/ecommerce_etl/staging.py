"""staging 영역에 통합 order-line DataFrame을 쓴다 (소스 공용)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


def write_parquet(df: pd.DataFrame, staging_dir: str | Path, order_date: date) -> Path:
    """`staging_dir/order_date=YYYY-MM-DD/orders.parquet` 로 쓴다. 경로를 반환."""
    part_dir = Path(staging_dir) / f"order_date={order_date.isoformat()}"
    part_dir.mkdir(parents=True, exist_ok=True)
    path = part_dir / "orders.parquet"
    df.to_parquet(path, index=False)
    return path
