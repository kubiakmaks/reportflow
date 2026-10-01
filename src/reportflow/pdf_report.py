from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


NAVY = colors.HexColor("#16324F")
BLUE = colors.HexColor("#246BCE")
LIGHT = colors.HexColor("#F2F5F8")
TEXT = colors.HexColor("#243447")
MUTED = colors.HexColor("#62748A")
RED = colors.HexColor("#C83E4D")


def _money(value: float) -> str:
    return f"{value:,.2f} PLN"


def _bar_list(pdf: canvas.Canvas, title: str, values: dict[str, float], x: float, y: float, width: float) -> None:
    pdf.setFillColor(TEXT)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, title)
    maximum = max(values.values(), default=1) or 1
    row_y = y - 9 * mm
    for label, value in values.items():
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(TEXT)
        pdf.drawString(x, row_y + 2, label)
        pdf.setFillColor(LIGHT)
        pdf.roundRect(x + 28 * mm, row_y, width - 53 * mm, 4 * mm, 2 * mm, stroke=0, fill=1)
        pdf.setFillColor(BLUE)
        pdf.roundRect(x + 28 * mm, row_y, (width - 53 * mm) * (value / maximum), 4 * mm, 2 * mm, stroke=0, fill=1)
        pdf.setFillColor(MUTED)
        pdf.drawRightString(x + width, row_y + 2, f"{value:,.0f}")
        row_y -= 8 * mm


def build_pdf(path: Path, summary: dict, generated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    pdf.setTitle("ReportFlow weekly operations report")
    pdf.setAuthor("ReportFlow")
    pdf.setSubject("Synthetic API and SQL reporting demo")
    page_width, page_height = A4

    pdf.setFillColor(NAVY)
    pdf.rect(0, page_height - 22 * mm, page_width, 22 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(16 * mm, page_height - 13 * mm, "REPORTFLOW")
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(page_width - 16 * mm, page_height - 13 * mm, "Weekly operations report")

    period = summary["period"]
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(16 * mm, page_height - 38 * mm, "Order performance")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(16 * mm, page_height - 45 * mm, f"Reporting period: {period['start']} to {period['end']}")
    pdf.drawRightString(page_width - 16 * mm, page_height - 45 * mm, f"Generated: {generated_at[:10]}")

    kpis = summary["kpis"]
    cards = [
        ("Valid orders", f"{kpis['valid_orders']:,}"),
        ("Non-cancelled value", _money(kpis["non_cancelled_value"])),
        ("On-time shipped", f"{kpis['on_time_shipped_rate']:.1%}" if kpis["on_time_shipped_rate"] is not None else "n/a"),
        ("Rejected records", f"{kpis['rejected_records']:,}"),
    ]
    card_y = page_height - 75 * mm
    gap = 4 * mm
    card_width = (page_width - 32 * mm - 3 * gap) / 4
    for index, (label, value) in enumerate(cards):
        x = 16 * mm + index * (card_width + gap)
        pdf.setFillColor(LIGHT)
        pdf.roundRect(x, card_y, card_width, 20 * mm, 2 * mm, stroke=0, fill=1)
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 7.5)
        pdf.drawString(x + 4 * mm, card_y + 13 * mm, label)
        pdf.setFillColor(NAVY if index != 3 else RED)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(x + 4 * mm, card_y + 5 * mm, value)

    panel_y = page_height - 100 * mm
    panel_width = (page_width - 36 * mm) / 2
    _bar_list(pdf, "Order value by region (PLN)", summary["value_by_region"], 16 * mm, panel_y, panel_width)
    _bar_list(pdf, "Orders by status", {key.title(): float(value) for key, value in summary["orders_by_status"].items()}, 20 * mm + panel_width, panel_y, panel_width)

    quality_y = 120 * mm
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(16 * mm, quality_y + 12 * mm, "Data quality")
    pdf.setFillColor(LIGHT)
    pdf.roundRect(16 * mm, quality_y - 2 * mm, page_width - 32 * mm, 10 * mm, 2 * mm, stroke=0, fill=1)
    pdf.setFillColor(TEXT)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(20 * mm, quality_y + 2 * mm, f"{kpis['rejected_records']} rejected API records. {summary['quality']['missing_customer_ids']} order has no matching SQL customer and remains in totals.")

    pdf.setStrokeColor(colors.HexColor("#D9E1E8"))
    pdf.line(16 * mm, 17 * mm, page_width - 16 * mm, 17 * mm)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(16 * mm, 11 * mm, "Synthetic demo data. Source: local REST API and SQLite.")
    pdf.drawRightString(page_width - 16 * mm, 11 * mm, "Page 1")
    pdf.showPage()
    pdf.save()
