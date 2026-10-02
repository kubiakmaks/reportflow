from __future__ import annotations

import threading
import zipfile
from pathlib import Path

import pytest

from reportflow.analytics import build_summary
from reportflow.api import ApiConfig, OrdersApiClient
from reportflow.database import enrich_orders, prepare_demo_database
from reportflow.mock_api import DEMO_TOKEN, DemoApiHandler, start_demo_server
from reportflow.models import Order
from reportflow.pipeline import run_pipeline


def raw_order(**changes) -> dict:
    record = {
        "order_id": "ORD-TEST",
        "customer_id": "C001",
        "ordered_at": "2026-09-14",
        "promised_at": "2026-09-17",
        "shipped_at": None,
        "status": "paid",
        "amount": 100,
    }
    record.update(changes)
    return record


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"ordered_at": None}, "missing fields"),
        ({"status": "unknown"}, "unsupported status"),
        ({"amount": "bad"}, "amount is not numeric"),
        ({"amount": 0}, "amount must be positive"),
    ],
)
def test_validation_rejects_core_errors(changes: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Order.from_api(raw_order(**changes))


def test_api_uses_two_pages_and_retries_503() -> None:
    server, url = start_demo_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = OrdersApiClient(ApiConfig(url, DEMO_TOKEN, retry_backoff_seconds=0))
        pages = list(client.iter_pages())
        assert [len(records) for _, records in pages] == [25, 25]
        assert DemoApiHandler.attempts["page-2"] == 2
    finally:
        server.shutdown()
        server.server_close()


def test_kpis_keep_order_without_sql_customer(tmp_path: Path) -> None:
    known = Order.from_api(raw_order(order_id="ORD-1", amount=100))
    unknown = Order.from_api(
        raw_order(
            order_id="ORD-2",
            customer_id="C999",
            status="shipped",
            amount=250,
            shipped_at="2026-09-17",
        )
    )
    late = Order.from_api(
        raw_order(
            order_id="ORD-3", status="shipped", amount=50, shipped_at="2026-09-18"
        )
    )
    cancelled = Order.from_api(raw_order(order_id="ORD-4", status="cancelled", amount=999))
    database = tmp_path / "reference.db"
    prepare_demo_database(database)
    enriched, missing = enrich_orders([known, unknown, late, cancelled], database)
    summary = build_summary(enriched, rejected_count=2, missing_customers=missing)

    assert len(enriched) == 4
    assert summary["kpis"] == {
        "valid_orders": 4,
        "non_cancelled_value": 400.0,
        "on_time_shipped_rate": 0.5,
        "rejected_records": 2,
    }
    assert summary["quality"]["missing_customer_ids"] == 1


def test_full_demo_creates_required_files(tmp_path: Path) -> None:
    server, url = start_demo_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = run_pipeline(url, DEMO_TOKEN, tmp_path)
    finally:
        server.shutdown()
        server.server_close()

    assert payload["summary"]["kpis"]["valid_orders"] == 46
    assert payload["summary"]["kpis"]["rejected_records"] == 4
    assert payload["summary"]["quality"]["missing_customer_ids"] == 1
    assert len(payload["summary"]["kpis"]) == 4
    required = ["reportflow_report.pdf", "reportflow_report.xlsx", "reportflow.log", "reference.db"]
    assert all((tmp_path / name).stat().st_size > 0 for name in required)
    assert "Retryable HTTP 503" in (tmp_path / "reportflow.log").read_text(encoding="utf-8")
    with zipfile.ZipFile(tmp_path / "reportflow_report.xlsx") as workbook:
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        assert all(name in workbook_xml for name in ["Summary", "Orders", "Data quality"])
