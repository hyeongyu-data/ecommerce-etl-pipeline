"""로컬 목업 오픈마켓 API (fakestore 형태). 재현성을 위해 외부 API 대신 쓴다.

    python mock/openmarket_server.py [--host 0.0.0.0] [--port 8000]

라우트:
  GET /products                        상품 목록
  GET /products/{id}                   상품 1건 (없으면 404)
  GET /carts?startdate=&enddate=       기간 내 cart 목록 (없으면 최근 7일)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# 컨테이너(python:slim)는 ecommerce_etl 을 pip 설치하지 않고 src/ 만 마운트한다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import openmarket_data as data  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # 조용히
        pass

    def _send(self, obj: object, status: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        qs = parse_qs(parsed.query)

        if parts == ["products"]:
            self._send(data.PRODUCTS)
        elif len(parts) == 2 and parts[0] == "products":
            prod = next((p for p in data.PRODUCTS if str(p["id"]) == parts[1]), None)
            self._send(prod if prod else {"error": "not found"}, 200 if prod else 404)
        elif parts == ["carts"]:
            start = qs.get("startdate", [None])[0]
            end = qs.get("enddate", [None])[0]
            if start and end:
                s, e = date.fromisoformat(start), date.fromisoformat(end)
            else:
                e = date.today()
                s = e - timedelta(days=6)
            self._send(data.carts_between(s, e))
        else:
            self._send({"error": "not found"}, 404)


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="0.0.0.0")  # 컨테이너 간 접근을 위해 전체 인터페이스
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    httpd = build_server(args.host, args.port)
    print(f"mock openmarket API on {args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
