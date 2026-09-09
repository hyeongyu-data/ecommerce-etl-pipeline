"""저장소 기본 구성 스모크 테스트. 스키마 정합성은 test_schema.py."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "pyproject.toml",
    ".python-version",
    ".pre-commit-config.yaml",
    ".env.example",
    "docs/SCHEMA.md",
    "Dockerfile",
    ".dockerignore",
    "docker-compose.yaml",
    "dags/.gitkeep",
    ".github/workflows/ci.yml",
    ".github/workflows/ai-review.yml",
]


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"필수 파일 누락: {missing}"


def test_env_example_has_no_real_values():
    """`.env.example` 은 키 이름만 두고 값은 비워 둔다(시크릿 유출 방지)."""
    allowed = {"", "local", "/opt/airflow/data"}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert "=" in stripped, f"형식 오류: {stripped!r}"
        key, _, value = stripped.partition("=")
        assert value in allowed, f"실제 값으로 보이는 항목: {key}"


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
    assert "pyproject.toml" in text
    assert "pip install" in text


def test_ai_review_workflow_is_non_blocking_and_guarded():
    """AI 리뷰 워크플로: 필수 아님·시크릿 없으면 skip·문서 전용 PR 제외."""
    text = (ROOT / ".github/workflows/ai-review.yml").read_text(encoding="utf-8")
    assert "GROQ_API_KEY" in text
    assert "paths-ignore" in text  # 문서 전용 PR 제외
    assert "/ai-review" in text  # 코멘트 재실행
    assert "시크릿이 없어" in text and "exit 0" in text


def test_pyproject_declares_deps():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.optional-dependencies]" in text
    for tool in ("pre-commit", "ruff", "pytest"):
        assert tool in text, f"pyproject.toml dev 의존성에 {tool} 없음"
    for pkg in ("pandas", "pyarrow"):
        assert pkg in text, f"pyproject.toml 런타임 의존성에 {pkg} 없음"
    assert not (ROOT / "requirements-dev.txt").exists()
    assert not (ROOT / "requirements.txt").exists()
