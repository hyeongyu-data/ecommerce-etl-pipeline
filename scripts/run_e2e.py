"""전체 ETL 파이프라인 종단간 검증 (로컬 전용).

`docker compose` 스택을 띄운 뒤 pg·openmarket·ga4 수집 DAG와 `warehouse_orders_load`를
대상 날짜로 실행하고, DuckDB `orders_unified`의 행 수·소스 분포·중복을 출력한다.
`warehouse_orders_load`는 2회 실행해 동일 날짜 재실행 시 행이 중복되지 않는지 확인한다.

    python scripts/run_e2e.py [YYYY-MM-DD]   # 기본 2026-09-01, 이미지 재빌드 후 실행
    python scripts/run_e2e.py --no-up        # compose up --build 생략 (이미 최신 이미지로 기동)

CI가 아니라 로컬에서 파이프라인 전체를 손으로 확인할 때 쓴다. 무거우므로 CI에는 넣지 않는다.
실행 후 스택은 계속 떠 있다. 정리는 `docker compose down -v`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from ecommerce_etl import schema

ROOT = Path(__file__).resolve().parent.parent
# 기본 DUCKDB_PATH(warehouse_orders_load.py) + 기본 ./data 바인드 마운트를 가정한다.
# .env/compose 에서 DUCKDB_PATH 를 바꿨다면 이 경로도 맞춰야 한다.
DUCKDB_FILE = ROOT / "data" / "warehouse" / "orders.duckdb"
SOURCE_DAGS = {
    "pg": "pg_orders_ingest",
    "openmarket": "openmarket_orders_ingest",
    "ga4": "ga4_events_ingest",
}


def _run(*args: str) -> None:
    print(f"$ {' '.join(args)}")
    subprocess.run(args, check=True, cwd=ROOT)


def _dag_test(dag_id: str, load_date: date) -> None:
    _run(
        "docker",
        "compose",
        "exec",
        "-T",
        "airflow-scheduler",
        "airflow",
        "dags",
        "test",
        dag_id,
        load_date.isoformat(),
    )


def duckdb_stats(db_path: Path, load_date: date) -> dict:
    """orders_unified 요약: 전체·대상일 행 수, 소스 분포, 중복 order_line_id, 파티션 수."""
    if not db_path.exists():
        raise SystemExit(f"FAIL: DuckDB 파일 없음 — 적재가 실패했을 수 있음 ({db_path})")
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        total = con.execute("SELECT count(*) FROM orders_unified").fetchone()[0]
        day_rows = con.execute(
            "SELECT count(*) FROM orders_unified WHERE order_date = ?", [load_date]
        ).fetchone()[0]
        by_source = dict(
            con.execute(
                "SELECT source, count(*) FROM orders_unified WHERE order_date = ? "
                "GROUP BY source ORDER BY source",
                [load_date],
            ).fetchall()
        )
        # 2회 이상 나타난 order_line_id 그룹 수(테이블 전체 기준). 멱등 적재면 0이어야 한다.
        dups = con.execute(
            "SELECT count(*) FROM ("
            "  SELECT order_line_id FROM orders_unified GROUP BY order_line_id HAVING count(*) > 1"
            ")"
        ).fetchone()[0]
        partitions = con.execute(
            "SELECT count(DISTINCT order_date) FROM orders_unified"
        ).fetchone()[0]
        return {
            "total": total,
            "day_rows": day_rows,
            "by_source": by_source,
            "dups": dups,
            "partitions": partitions,
        }
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("load_date", nargs="?", type=date.fromisoformat, default=date(2026, 9, 1))
    parser.add_argument(
        "--no-up",
        action="store_true",
        help="docker compose up --build 를 생략한다(이미 최신 이미지로 기동한 경우)",
    )
    args = parser.parse_args()
    load_date: date = args.load_date

    if not args.no_up:
        # --build: ecommerce_etl 은 이미지에 설치되므로 코어 코드 변경을 반영한다.
        # 스케줄러·목업만 띄운다. 웹서버는 제외해 호스트 포트 충돌(#38)과 무관하게 돈다.
        _run(
            "docker",
            "compose",
            "up",
            "-d",
            "--build",
            "--wait",
            "airflow-scheduler",
            "mock-openmarket",
        )

    print(f"\n=== 1) 세 소스 수집 ({load_date}) ===")
    for source in schema.SOURCES:
        _dag_test(SOURCE_DAGS[source], load_date)
        staging = (
            ROOT
            / "data"
            / "staging"
            / source
            / f"order_date={load_date.isoformat()}"
            / "orders.parquet"
        )
        if not staging.exists():
            print(f"FAIL: staging 파일 없음 {staging}")
            return 1
        print(f"  ok  {source}: {len(pd.read_parquet(staging))}행  {staging.relative_to(ROOT)}")

    print("\n=== 2) 통합 적재 1회차 ===")
    _dag_test("warehouse_orders_load", load_date)
    first = duckdb_stats(DUCKDB_FILE, load_date)
    print(f"  {first}")
    # airflow dags test 의 종료 코드만 믿지 않는다: 적재가 실제로 행을 넣었는지 확인.
    if first["day_rows"] <= 0 or first["total"] < first["day_rows"]:
        print(f"FAIL: 1회차 적재 결과가 비정상 {first}")
        return 1

    print("\n=== 3) 통합 적재 2회차 (멱등성) ===")
    _dag_test("warehouse_orders_load", load_date)
    second = duckdb_stats(DUCKDB_FILE, load_date)
    print(f"  {second}")

    print("\n=== 결과 ===")
    ok = True
    if second["dups"] != 0:
        print(f"FAIL: 중복 order_line_id {second['dups']}건")
        ok = False
    if first["day_rows"] != second["day_rows"]:
        print(f"FAIL: 재실행 후 대상일 행 수 변동 {first['day_rows']} -> {second['day_rows']}")
        ok = False
    if set(second["by_source"]) != set(schema.SOURCES):
        print(f"FAIL: 소스 누락 {set(schema.SOURCES) - set(second['by_source'])}")
        ok = False
    if ok:
        print(
            f"PASS: {load_date} {second['day_rows']}행 "
            f"({second['by_source']}), 중복 0, 재실행 안정, 파티션 {second['partitions']}개 보존"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
