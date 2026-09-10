"""`scripts/run_e2e.py` 의 DuckDB 요약 쿼리 검증 (Docker 없이).

파이프라인 전체 실행은 `scripts/run_e2e.py` 로 로컬에서 수행한다. 여기서는 그 스크립트가
멱등성 판정에 쓰는 `duckdb_stats` 가 행 수·소스 분포·중복·파티션 수를 바르게 집계하는지만 본다.
"""

from datetime import date

import pandas as pd
import pytest
from run_e2e import duckdb_stats

from ecommerce_etl.duckdb import replace_date
from ecommerce_etl.schema import UNIFIED_COLUMNS


def _rows(specs: list[tuple[str, str, date]]) -> pd.DataFrame:
    records = []
    for source, line_id, day in specs:
        row = dict.fromkeys(UNIFIED_COLUMNS)
        row.update(
            source=source,
            source_order_id=line_id,
            order_id=line_id,
            order_line_id=line_id,
            line_no=1,
            ordered_at=pd.Timestamp(day, tz="UTC"),
            order_date=day,
            product_id="p1",
            quantity=1,
            line_amount=0,
            currency="KRW",
            ingested_at=pd.Timestamp(day, tz="UTC"),
        )
        records.append(row)
    return pd.DataFrame(records, columns=list(UNIFIED_COLUMNS))


def test_duckdb_stats_counts_sources_dups_and_partitions(tmp_path):
    db = tmp_path / "orders.duckdb"
    day1, day2 = date(2026, 9, 1), date(2026, 9, 2)
    replace_date(
        db,
        _rows([("pg", "a1", day1), ("openmarket", "b1", day1), ("ga4", "c1", day1)]),
        day1,
    )
    replace_date(db, _rows([("pg", "a2", day2), ("openmarket", "b2", day2)]), day2)

    stats = duckdb_stats(db, day1)
    assert stats["total"] == 5
    assert stats["day_rows"] == 3
    assert stats["by_source"] == {"pg": 1, "openmarket": 1, "ga4": 1}
    assert stats["dups"] == 0
    assert stats["partitions"] == 2

    # 같은 날짜 재적재 후에도 중복이 생기지 않는다 (스크립트의 멱등성 판정 근거).
    replace_date(
        db,
        _rows([("pg", "a1", day1), ("openmarket", "b1", day1), ("ga4", "c1", day1)]),
        day1,
    )
    again = duckdb_stats(db, day1)
    assert again["day_rows"] == 3
    assert again["dups"] == 0


def test_duckdb_stats_missing_file_fails_clearly(tmp_path):
    with pytest.raises(SystemExit, match="적재가 실패"):
        duckdb_stats(tmp_path / "nope.duckdb", date(2026, 9, 1))
