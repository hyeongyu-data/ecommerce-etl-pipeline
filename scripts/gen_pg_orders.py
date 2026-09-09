"""여러 날짜의 합성 PG 원천 CSV를 한 번에 생성한다 (로컬 편의).

    python scripts/gen_pg_orders.py --start 2026-09-01 --end 2026-09-07

DAG는 실행 시 필요한 날짜를 스스로 생성하므로, 이 스크립트는 로컬에서 미리
데이터를 눈으로 확인하거나 백필용 원천을 채워둘 때 쓴다.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from ecommerce_etl.pg import generate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/pg"))
    args = parser.parse_args()

    if args.end < args.start:
        parser.error("--end 는 --start 이후여야 합니다")

    day = args.start
    while day <= args.end:
        print(generate.write_csv(day, args.raw_dir, seed=args.seed))
        day += timedelta(days=1)


if __name__ == "__main__":
    main()
