from __future__ import annotations

import json
from pathlib import Path

import xlsxwriter

from .models import EnrichedOrder, RejectedRecord


NAVY = "#16324F"
BLUE = "#246BCE"
LIGHT = "#F2F5F8"
TEXT = "#243447"
MUTED = "#62748A"
RED = "#C83E4D"


def build_excel(
    path: Path,
    summary: dict,
    orders: list[EnrichedOrder],
    rejected: list[RejectedRecord],
    warnings: list[dict],
    generated_at: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = xlsxwriter.Workbook(path)
    workbook.set_properties({"title": "ReportFlow weekly operations report", "subject": "Synthetic API and SQL reporting demo", "author": "ReportFlow"})

    title = workbook.add_format({"font_name": "Arial", "font_size": 16, "bold": True, "font_color": NAVY})
    section = workbook.add_format({"font_name": "Arial", "font_size": 11, "bold": True, "font_color": NAVY})
    note = workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": MUTED, "italic": True})
    header = workbook.add_format({"font_name": "Arial", "font_size": 9, "bold": True, "font_color": "#FFFFFF", "bg_color": NAVY, "align": "center", "valign": "vcenter"})
    card_label = workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": MUTED, "bg_color": LIGHT})
    card_value = workbook.add_format({"font_name": "Arial", "font_size": 13, "bold": True, "font_color": NAVY, "bg_color": LIGHT})
    card_money = workbook.add_format({"font_name": "Arial", "font_size": 13, "bold": True, "font_color": NAVY, "bg_color": LIGHT, "num_format": "#,##0.00 \"PLN\""})
    card_percent = workbook.add_format({"font_name": "Arial", "font_size": 13, "bold": True, "font_color": NAVY, "bg_color": LIGHT, "num_format": "0.0%"})
    body = workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": TEXT})
    money = workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": TEXT, "num_format": "#,##0.00 \"PLN\""})
    date_format = workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": TEXT, "num_format": "yyyy-mm-dd"})
    warning_format = workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": "#7A4B00", "bg_color": "#FFF4D6"})
    error_format = workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": RED, "bg_color": "#FDEBEC"})

    summary_sheet = workbook.add_worksheet("Summary")
    summary_sheet.hide_gridlines(2)
    summary_sheet.set_tab_color(NAVY)
    summary_sheet.set_column("A:A", 3)
    summary_sheet.set_column("B:I", 15)
    summary_sheet.write("B2", "Weekly order report", title)
    period = summary["period"]
    summary_sheet.write("B3", f"{period['start']} to {period['end']} | Generated {generated_at[:10]}", note)
    kpis = summary["kpis"]
    cards = [
        ("B5:C5", "B6:C7", "Valid orders", kpis["valid_orders"], card_value),
        ("D5:E5", "D6:E7", "Non-cancelled value", kpis["non_cancelled_value"], card_money),
        ("F5:G5", "F6:G7", "On-time shipped", kpis["on_time_shipped_rate"], card_percent),
        ("H5:I5", "H6:I7", "Rejected records", kpis["rejected_records"], card_value),
    ]
    for label_range, value_range, label, value, value_format in cards:
        summary_sheet.merge_range(label_range, label, card_label)
        summary_sheet.merge_range(value_range, value if value is not None else "n/a", value_format)

    summary_sheet.write("B10", "Order value by region", section)
    summary_sheet.write_row("B11", ["Region", "Value (PLN)"], header)
    for row, (region, value) in enumerate(summary["value_by_region"].items(), start=11):
        summary_sheet.write(row, 1, region, body)
        summary_sheet.write_number(row, 2, value, money)

    summary_sheet.write("E10", "Orders by status", section)
    summary_sheet.write_row("E11", ["Status", "Orders"], header)
    for row, (status, count) in enumerate(summary["orders_by_status"].items(), start=11):
        summary_sheet.write(row, 4, status.title(), body)
        summary_sheet.write_number(row, 5, count, body)

    region_chart = workbook.add_chart({"type": "column"})
    region_end = 11 + len(summary["value_by_region"])
    region_chart.add_series({"name": "Order value", "categories": f"=Summary!$B$12:$B${region_end}", "values": f"=Summary!$C$12:$C${region_end}", "fill": {"color": BLUE}, "border": {"none": True}})
    region_chart.set_title({"name": "Order value by region (PLN)"})
    region_chart.set_legend({"none": True})
    region_chart.set_y_axis({"min": 0, "num_format": "#,##0"})
    region_chart.set_chartarea({"border": {"none": True}})
    region_chart.set_plotarea({"border": {"none": True}})
    summary_sheet.insert_chart("B19", region_chart, {"x_scale": 0.78, "y_scale": 0.85})

    status_chart = workbook.add_chart({"type": "column"})
    status_end = 11 + len(summary["orders_by_status"])
    status_chart.add_series({"name": "Orders", "categories": f"=Summary!$E$12:$E${status_end}", "values": f"=Summary!$F$12:$F${status_end}", "fill": {"color": "#3BB6C4"}, "border": {"none": True}})
    status_chart.set_title({"name": "Orders by status"})
    status_chart.set_legend({"none": True})
    status_chart.set_y_axis({"min": 0, "major_unit": 5})
    status_chart.set_chartarea({"border": {"none": True}})
    status_chart.set_plotarea({"border": {"none": True}})
    summary_sheet.insert_chart("F19", status_chart, {"x_scale": 0.78, "y_scale": 0.85})
    summary_sheet.write("B36", f"Data quality: {kpis['rejected_records']} rejected records and {summary['quality']['missing_customer_ids']} missing SQL customer match.", note)
    summary_sheet.set_landscape()
    summary_sheet.fit_to_pages(1, 1)
    summary_sheet.print_area("B2:I36")

    orders_sheet = workbook.add_worksheet("Orders")
    orders_sheet.hide_gridlines(2)
    orders_sheet.freeze_panes(1, 2)
    order_headers = ["Order ID", "Customer ID", "Customer", "Segment", "Region", "Account owner", "Ordered", "Promised", "Shipped", "Status", "Amount (PLN)", "On time"]
    orders_sheet.write_row(0, 0, order_headers, header)
    for row, item in enumerate(orders, start=1):
        for column, value in enumerate([item.order.order_id, item.order.customer_id, item.customer_name, item.segment, item.region, item.account_owner]):
            orders_sheet.write(row, column, value, body)
        orders_sheet.write_datetime(row, 6, item.order.ordered_at, date_format)
        orders_sheet.write_datetime(row, 7, item.order.promised_at, date_format)
        if item.order.shipped_at:
            orders_sheet.write_datetime(row, 8, item.order.shipped_at, date_format)
        else:
            orders_sheet.write_blank(row, 8, None, date_format)
        orders_sheet.write(row, 9, item.order.status.title(), body)
        orders_sheet.write_number(row, 10, float(item.order.amount), money)
        orders_sheet.write(row, 11, "Yes" if item.on_time is True else "No" if item.on_time is False else "n/a", body)
    orders_sheet.add_table(0, 0, len(orders), len(order_headers) - 1, {"name": "OrdersTable", "style": "Table Style Medium 2", "columns": [{"header": value} for value in order_headers]})
    orders_sheet.set_column("A:B", 13)
    orders_sheet.set_column("C:C", 21)
    orders_sheet.set_column("D:F", 15)
    orders_sheet.set_column("G:J", 12)
    orders_sheet.set_column("K:K", 15)
    orders_sheet.set_column("L:L", 10)

    quality_sheet = workbook.add_worksheet("Data quality")
    quality_sheet.hide_gridlines(2)
    quality_sheet.freeze_panes(1, 0)
    quality_headers = ["Severity", "Page", "Order ID", "Customer ID", "Issue", "Source record"]
    quality_sheet.write_row(0, 0, quality_headers, header)
    quality_rows: list[tuple[list, object]] = []
    for record in rejected:
        quality_rows.append((["Rejected", record.page, record.record.get("order_id", ""), record.record.get("customer_id", ""), record.reason, json.dumps(record.record, ensure_ascii=False, sort_keys=True)], error_format))
    for warning in warnings:
        quality_rows.append((["Warning", warning["page"], warning["order_id"], warning["customer_id"], warning["reason"], ""], warning_format))
    for row, (values, row_format) in enumerate(quality_rows, start=1):
        for column, value in enumerate(values):
            quality_sheet.write(row, column, value, row_format)
    quality_sheet.add_table(0, 0, len(quality_rows), len(quality_headers) - 1, {"name": "DataQualityTable", "style": "Table Style Medium 2", "columns": [{"header": value} for value in quality_headers]})
    quality_sheet.set_column("A:A", 11)
    quality_sheet.set_column("B:B", 8)
    quality_sheet.set_column("C:D", 14)
    quality_sheet.set_column("E:E", 46)
    quality_sheet.set_column("F:F", 80)

    workbook.close()
