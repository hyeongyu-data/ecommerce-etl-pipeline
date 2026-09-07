"""저장소 기본 구성을 확인하는 스모크 테스트.

폴더를 늘리지 않기 위해 저장소 루트에 둔다(기본 폴더 구조 유지).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    "pyproject.toml",
    "requirements-dev.txt",
    ".python-version",
    ".pre-commit-config.yaml",
    ".env.example",
    ".github/workflows/ci.yml",
]


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
