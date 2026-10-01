from __future__ import annotations

import json
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


DEMO_TOKEN = "demo-token"


def _records() -> list[dict]:
    records: list[dict] = []
    statuses = ["paid", "shipped", "processing", "shipped", "cancelled"]
    start = date(2026, 9, 14)
    for index in range(1, 47):
        ordered = start + timedelta(days=(index - 1) % 7)
        promised = ordered + timedelta(days=3)
        status = statuses[index % len(statuses)]
        shipped = promised + timedelta(days=(index % 3) - 1) if status == "shipped" else None
        records.append(
            {
                "order_id": f"ORD-{index:04d}",
                "customer_id": "C999" if index == 46 else f"C{((index - 1) % 8) + 1:03d}",
                "ordered_at": ordered.isoformat(),
                "promised_at": promised.isoformat(),
                "shipped_at": shipped.isoformat() if shipped else None,
                "status": status,
                "amount": round(250 + ((index * 137) % 2750) + (index % 4) * 0.25, 2),
            }
        )
    records.extend(
        [
            {"order_id": "ORD-BAD-1", "customer_id": "C001", "promised_at": "2026-09-20", "status": "paid", "amount": 120},
            {"order_id": "ORD-BAD-2", "customer_id": "C002", "ordered_at": "2026-09-18", "promised_at": "2026-09-21", "status": "unknown", "amount": 200},
            {"order_id": "ORD-BAD-3", "customer_id": "C003", "ordered_at": "2026-09-19", "promised_at": "2026-09-22", "status": "processing", "amount": 0},
            {"order_id": "ORD-0001", "customer_id": "C004", "ordered_at": "2026-09-20", "promised_at": "2026-09-23", "status": "paid", "amount": 500},
        ]
    )
    return records


class DemoApiHandler(BaseHTTPRequestHandler):
    attempts: dict[str, int] = {}

    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/v1/orders":
            self._send(404, {"error": "not found"})
            return
        if self.headers.get("Authorization") != f"Bearer {DEMO_TOKEN}":
            self._send(401, {"error": "invalid token"})
            return
        query = parse_qs(parsed.query)
        page = int(query.get("page", ["1"])[0])
        page_size = min(int(query.get("page_size", ["25"])[0]), 50)
        key = f"page-{page}"
        self.attempts[key] = self.attempts.get(key, 0) + 1
        if page == 2 and self.attempts[key] == 1:
            self._send(503, {"error": "temporary demo failure"})
            return
        records = _records()
        start = (page - 1) * page_size
        end = start + page_size
        next_page = page + 1 if end < len(records) else None
        self._send(200, {"items": records[start:end], "next_page": next_page, "total": len(records)})


def start_demo_server() -> tuple[ThreadingHTTPServer, str]:
    DemoApiHandler.attempts = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoApiHandler)
    return server, f"http://127.0.0.1:{server.server_port}"
