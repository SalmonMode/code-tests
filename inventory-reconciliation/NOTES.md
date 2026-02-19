# Inventory Reconciliation Notes

## How I Approached the Problem
- Built a small parser library to read both snapshot schemas and map them into one unified row structure.
- Added normalization/validation for SKU, quantity, date, and text fields so reconciliation can run reliably despite formatting inconsistencies.
- Implemented reconciliation utilities, then used `inventory-reconciliation/reconcile.py` to generate a structured JSON report at `inventory-reconciliation/output/reconciliation_report.json`.
- Added pytest coverage across parsing, normalization, reconciliation, and report generation.

## Key Decisions And Assumptions
- Reconciliation defaults to `sku_warehouse` so quantities from different warehouses are treated as distinct inventory.
- Alternate key strategies (`name_warehouse`, `sku`, `name`) are supported for comparison.
- Deterministic merge rule: if multiple rows map to the same key within one snapshot, quantities are merged by addition.
- Decimal-formatted integer quantities are accepted and flagged; non-integral quantities are treated as invalid.
- Non-ISO dates are parsed when possible and flagged; negative quantities are retained and flagged.

## Data Quality Issues Found
- The current report contains `12` row-level issues and `0` file-level issues.
- Row-level issue counts:
- `whitespace_trimmed`: `5`
- `sku_format_normalized`: `3`
- `decimal_quantity_format`: `2`
- `non_iso_date_format`: `1`
- `negative_quantity`: `1`
- Main quality themes: inconsistent SKU formatting, leading/trailing whitespace, decimal-rendered quantities, one non-ISO date value, and one negative quantity.
