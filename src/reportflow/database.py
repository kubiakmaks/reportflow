from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import EnrichedOrder, Order


CUSTOMERS = [
    ("C001", "Northstar Retail", "Enterprise", "Central", "Anna Kowalska"),
    ("C002", "Vistula Foods", "Mid-market", "North", "Marek Nowak"),
    ("C003", "Orion Labs", "Enterprise", "West", "Julia Zielinska"),
    ("C004", "Greenline Logistics", "SMB", "South", "Piotr Wojcik"),
    ("C005", "Amber Commerce", "Mid-market", "Central", "Anna Kowalska"),
    ("C006", "Baltic Supply", "SMB", "North", "Marek Nowak"),
    ("C007", "Silesia Tools", "Mid-market", "South", "Piotr Wojcik"),
    ("C008", "Nova Medical", "Enterprise", "West", "Julia Zielinska"),
]


def prepare_demo_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                segment TEXT NOT NULL,
                region TEXT NOT NULL,
                account_owner TEXT NOT NULL
            )"""
        )
        connection.executemany(
            "INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?, ?)", CUSTOMERS
        )


def enrich_orders(orders: list[Order], database_path: Path) -> tuple[list[EnrichedOrder], list[str]]:
    enriched: list[EnrichedOrder] = []
    missing_customers: list[str] = []
    with sqlite3.connect(database_path) as connection:
        for order in orders:
            row = connection.execute(
                "SELECT customer_name, segment, region, account_owner FROM customers WHERE customer_id = ?",
                (order.customer_id,),
            ).fetchone()
            if row is None:
                missing_customers.append(order.customer_id)
                enriched.append(
                    EnrichedOrder(order, "Unknown customer", "Unknown", "Unassigned", "Unassigned")
                )
            else:
                enriched.append(EnrichedOrder(order, *row))
    return enriched, sorted(set(missing_customers))
