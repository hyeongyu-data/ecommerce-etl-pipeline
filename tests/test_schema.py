"""통합 스키마 단일 출처(src/ecommerce_etl/schema.py)와 문서·DDL의 일치 검증."""

import re
from pathlib import Path

from ecommerce_etl import schema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_MD = (ROOT / "docs/SCHEMA.md").read_text(encoding="utf-8")


def test_columns_documented_in_schema_md():
    missing = [c for c in schema.UNIFIED_COLUMNS if f"`{c}`" not in SCHEMA_MD]
    assert not missing, f"docs/SCHEMA.md 표에 없는 컬럼: {missing}"


def test_sources_documented():
    missing = [s for s in schema.SOURCES if f"`{s}`" not in SCHEMA_MD]
    assert not missing, f"docs/SCHEMA.md에 없는 소스: {missing}"


def test_ddl_block_matches_columns():
    m = re.search(r"```sql\n(.*?)```", SCHEMA_MD, re.DOTALL)
    assert m, "docs/SCHEMA.md에 ```sql DDL 블록이 없다"
    ddl = m.group(1)
    assert "PARTITION BY order_date" in ddl
    assert "CLUSTER BY source" in ddl
    for col in schema.UNIFIED_COLUMNS:
        assert re.search(
            rf"^\s*{re.escape(col)}\s", ddl, re.MULTILINE
        ), f"DDL에 컬럼 정의 없음: {col}"


def test_dtypes_cover_all_columns():
    assert set(schema.PANDAS_DTYPES) == set(schema.UNIFIED_COLUMNS)


def test_required_is_complement_of_nullable():
    assert set(schema.REQUIRED) | set(schema.NULLABLE) == set(schema.UNIFIED_COLUMNS)
    assert not (set(schema.REQUIRED) & set(schema.NULLABLE))
