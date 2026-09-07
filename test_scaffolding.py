"""저장소 기본 구성과 스키마 문서 정합성을 확인하는 스모크 테스트.

폴더를 늘리지 않기 위해 저장소 루트에 둔다(기본 폴더 구조 유지).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements.txt",
    ".python-version",
    ".pre-commit-config.yaml",
    ".env.example",
    "SCHEMA.md",
    "Dockerfile",
    ".dockerignore",
    "docker-compose.yaml",
    "dags/.gitkeep",
    ".github/workflows/ci.yml",
]

# SCHEMA.md 통합 스키마 표 / DDL에 반드시 있어야 하는 컬럼
UNIFIED_COLUMNS = [
    "source",
    "source_order_id",
    "order_id",
    "order_line_id",
    "line_no",
    "ordered_at",
    "order_date",
    "customer_id",
    "product_id",
    "product_name",
    "quantity",
    "unit_price",
    "line_amount",
    "currency",
    "channel",
    "event_name",
    "source_file",
    "ingested_at",
]

SOURCES = ["pg", "openmarket", "ga4"]


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"필수 파일 누락: {missing}"


def test_env_example_has_no_real_values():
    """`.env.example` 은 키 이름만 두고 값은 비워 둔다(시크릿 유출 방지)."""
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert "=" in stripped, f"형식 오류: {stripped!r}"
        key, _, value = stripped.partition("=")
        assert value == "" or value == "local", f"실제 값으로 보이는 항목: {key}"


def test_compose_is_minimal_local_airflow():
    """docker-compose 는 LocalExecutor 기반 최소 구성(Celery/Redis/MySQL 없음)."""
    lines = (ROOT / "docker-compose.yaml").read_text(encoding="utf-8").splitlines()
    body = "\n".join(ln for ln in lines if not ln.lstrip().startswith("#")).lower()
    for needed in ("airflow-webserver", "airflow-scheduler", "postgres", "localexecutor"):
        assert needed in body, f"docker-compose.yaml 에 {needed} 없음"
    for excluded in ("redis", "celeryexecutor", "mysql", "flower"):
        assert excluded not in body, f"docker-compose.yaml 에 불필요한 {excluded} 포함"


def test_dockerfile_extends_official_airflow():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM apache/airflow:" in text
    assert "requirements.txt" in text


def test_schema_doc_covers_all_columns_and_sources():
    text = (ROOT / "SCHEMA.md").read_text(encoding="utf-8")
    missing_cols = [c for c in UNIFIED_COLUMNS if f"`{c}`" not in text]
    assert not missing_cols, f"SCHEMA.md에 없는 컬럼: {missing_cols}"
    missing_src = [s for s in SOURCES if f"`{s}`" not in text]
    assert not missing_src, f"SCHEMA.md에 없는 소스: {missing_src}"


def test_schema_doc_ddl_matches_columns():
    """SCHEMA.md 안의 sql DDL 블록이 통합 컬럼 목록과 일치하는지."""
    text = (ROOT / "SCHEMA.md").read_text(encoding="utf-8")
    m = re.search(r"```sql\n(.*?)```", text, re.DOTALL)
    assert m, "SCHEMA.md에 sql DDL 블록이 없다"
    ddl = m.group(1)
    assert "PARTITION BY order_date" in ddl
    assert "CLUSTER BY source" in ddl
    for col in UNIFIED_COLUMNS:
        assert re.search(
            rf"^\s*{re.escape(col)}\s", ddl, re.MULTILINE
        ), f"DDL에 컬럼 정의 없음: {col}"
