"""통합 주문 데이터를 DuckDB에 날짜별로 멱등 적재한다."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from .schema import UNIFIED_COLUMNS


def replace_date(db_path: Path, frame: pd.DataFrame, load_date: date) -> int:
    if frame.empty:
        return 0
    missing = [c for c in UNIFIED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {', '.join(missing)}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE TABLE IF NOT EXISTS orders_unified AS SELECT * FROM frame LIMIT 0")
        con.execute("BEGIN TRANSACTION")
        con.execute("DELETE FROM orders_unified WHERE order_date = ?", [load_date])
        con.execute("INSERT INTO orders_unified SELECT * FROM frame")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return len(frame)
