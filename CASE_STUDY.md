# ReportFlow: weekly order reporting

## Scenario

A fictional B2B distributor prepares a weekly order report from two sources. Orders come from a sales platform API. Customer names, regions and account owners live in an internal SQL database.

The reporting task is to fetch every API page, validate the records, match the customer table and produce both a management summary and an operational file.

## One run

The command `reportflow demo --output output` starts a local demo API and runs the complete pipeline. It reads 50 source records from two pages, accepts 46 and rejects 4. One accepted order has no customer match in SQLite.

The missing match is reported as a warning, but the order remains in the totals. The run creates a one-page PDF, a three-sheet Excel workbook, an execution log and the SQLite database used for enrichment.

## Failure handling

The demo API returns `503` once when page 2 is requested. The client retries the request and records the retry in the log. Other data-quality cases are handled separately:

- missing fields, unsupported statuses, non-positive amounts and duplicate IDs are rejected;
- a missing SQL customer produces a warning rather than a rejected order;
- the generated data is deterministic, so tests can assert exact totals.

Seven automated tests cover validation, pagination, retry, KPI calculations and the complete pipeline.

## Output

The PDF is the manager view: four KPIs, order value by region, orders by status and a short data-quality note. The Excel workbook keeps the same summary together with accepted orders and the rejected-record trail.

All data is synthetic. The project does not use client systems, credentials or confidential information.
