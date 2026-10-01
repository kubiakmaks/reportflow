from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from .analytics import build_summary
from .api import ApiConfig, OrdersApiClient
from .database import enrich_orders, prepare_demo_database
from .models import Order, RejectedRecord
from .pdf_report import build_pdf
from .xlsx_report import build_excel


def run_pipeline(base_url: str, token: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("reportflow")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(output_dir / "reportflow.log", mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    try:
        client = OrdersApiClient(ApiConfig(base_url=base_url, token=token), logger)
        orders: list[Order] = []
        rejected: list[RejectedRecord] = []
        seen_ids: set[str] = set()
        pages_by_order_id: dict[str, int] = {}
        for page, records in client.iter_pages():
            logger.info("Received %s records from page %s", len(records), page)
            for raw in records:
                try:
                    order = Order.from_api(raw)
                    if order.order_id in seen_ids:
                        raise ValueError("duplicate order_id")
                    seen_ids.add(order.order_id)
                    pages_by_order_id[order.order_id] = page
                    orders.append(order)
                except ValueError as exc:
                    rejected.append(RejectedRecord(page, raw, str(exc)))

        database_path = output_dir / "reference.db"
        prepare_demo_database(database_path)
        enriched, missing_customers = enrich_orders(orders, database_path)
        warnings = [
            {
                "page": pages_by_order_id[item.order.order_id],
                "order_id": item.order.order_id,
                "customer_id": item.order.customer_id,
                "reason": "customer not found in SQLite; order kept in totals",
            }
            for item in enriched
            if item.order.customer_id in missing_customers
        ]
        summary = build_summary(enriched, len(rejected), missing_customers)
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        build_pdf(output_dir / "reportflow_report.pdf", summary, generated_at)
        build_excel(output_dir / "reportflow_report.xlsx", summary, enriched, rejected, warnings, generated_at)
        logger.info("Pipeline completed: %s valid, %s rejected, %s warnings", len(enriched), len(rejected), len(warnings))
        return {
            "generated_at": generated_at,
            "summary": summary,
            "orders": enriched,
            "rejected_records": rejected,
            "warnings": warnings,
        }
    finally:
        for handler in list(logger.handlers):
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
