import pytest

bigquery = pytest.importorskip("google.cloud.bigquery")

from ecommerce_etl.bigquery import _validate_identifier, table_schema  # noqa: E402
from ecommerce_etl.schema import NULLABLE, UNIFIED_COLUMNS  # noqa: E402


def test_bigquery_schema_matches_unified_columns():
    fields = table_schema()
    assert [field.name for field in fields] == list(UNIFIED_COLUMNS)
    assert [field.mode for field in fields] == [
        "NULLABLE" if column in NULLABLE else "REQUIRED" for column in UNIFIED_COLUMNS
    ]


def test_identifier_rejects_injection():
    with pytest.raises(ValueError):
        _validate_identifier("orders; DROP TABLE users", "테이블")


def test_project_identifier_allows_gcp_hyphen():
    assert _validate_identifier("ecommerce-etl-pipeline-508205", "프로젝트", project=True)
