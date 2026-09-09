"""오픈마켓(fakestore 형태) API HTTP 클라이언트.

타임아웃 + 지수 백오프 재시도. base_url 은 DAG가 환경변수 OPENMARKET_API_BASE_URL 로 준다.
"""

from __future__ import annotations

import time
from datetime import date

import requests

DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # 테스트에서 0으로 낮출 수 있다


def _get(url: str, *, params: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> object:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE * (2**attempt))
    raise RuntimeError(f"GET {url} 실패 ({MAX_RETRIES}회 시도)") from last_exc


def fetch_products(base_url: str) -> list[dict]:
    return _get(f"{base_url.rstrip('/')}/products")


def fetch_carts(base_url: str, order_date: date) -> list[dict]:
    """지정 날짜의 cart 목록. fakestore 의 startdate/enddate 쿼리를 쓴다."""
    return _get(
        f"{base_url.rstrip('/')}/carts",
        params={"startdate": order_date.isoformat(), "enddate": order_date.isoformat()},
    )
