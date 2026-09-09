"""목업 서버를 스레드로 띄우고 HTTP 클라이언트↔서버 계약을 검증한다."""

import sys
import threading
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mock"))

from ecommerce_etl.openmarket import client  # noqa: E402


@pytest.fixture(scope="module")
def server_url():
    import openmarket_server

    httpd = openmarket_server.build_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()


def test_fetch_products(server_url):
    products = client.fetch_products(server_url)
    assert len(products) == 10
    assert {"id", "title", "price"} <= products[0].keys()


def test_fetch_carts_filtered_by_date(server_url):
    carts = client.fetch_carts(server_url, date(2026, 9, 1))
    assert carts
    for cart in carts:
        assert cart["date"].startswith("2026-09-01")
        assert cart["products"]


def test_fetch_carts_other_date_differs(server_url):
    a = client.fetch_carts(server_url, date(2026, 9, 1))
    b = client.fetch_carts(server_url, date(2026, 9, 2))
    assert {c["id"] for c in a} != {c["id"] for c in b}


def test_retry_then_raise(monkeypatch):
    monkeypatch.setattr(client, "_BACKOFF_BASE", 0)
    with pytest.raises(RuntimeError, match="실패"):
        client.fetch_products("http://127.0.0.1:1")  # 연결 거부
