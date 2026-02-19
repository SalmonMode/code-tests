# inventory_parser

`inventory_parser` is a small parsing/normalization library for loading both
inventory snapshot formats into one canonical structure.

## What It Does

- Detects which known CSV schema is being parsed.
- Normalizes each row into the same output model.
- Preserves source metadata (`source_file`, `source_row`, `source_schema`).
- Flags data-quality issues while parsing.
- Provides reconciliation summaries with configurable key strategy.

## Package Layout

- `inventory_parser/models.py`
  - Dataclasses used by the parser outputs.
- `inventory_parser/normalize.py`
  - Field-level normalization and validation helpers.
- `inventory_parser/parser.py`
  - Schema detection and CSV parsing entry points.
- `inventory_parser/reconcile.py`
  - Reconciliation helpers for delta/category summaries.
- `inventory_parser/__init__.py`
  - Public API exports.

## Public API

```python
from inventory_parser import (
    detect_schema,
    parse_snapshot,
    parse_both_snapshots,
    reconcile_rows,
    reconcile_combined_result,
    DataIssue,
    UnifiedInventoryRow,
    ParseResult,
    CombinedParseResult,
)
```

### `parse_snapshot(csv_path) -> ParseResult`

Parses one CSV into canonical rows.

- Detects schema from headers.
- Returns:
  - `schema_name` for the file (`snapshot_v1` or `snapshot_v2`)
  - `rows` as `UnifiedInventoryRow` objects
  - `file_issues` for file-level conditions (for example extra columns)

### `parse_both_snapshots(snapshot_1_path, snapshot_2_path) -> CombinedParseResult`

Parses both files and returns:

- `snapshot_1`: `ParseResult`
- `snapshot_2`: `ParseResult`
- `all_rows()`: list containing both snapshots' rows

### `detect_schema(headers) -> SchemaDefinition`

Uses exact header-set matching after:

- trimming whitespace
- lowercasing header names

If headers do not match a known schema, it raises `ValueError`.

### `reconcile_rows(snapshot_1_rows, snapshot_2_rows, key="sku_warehouse") -> ReconciliationSummary`

Builds a summary with:

- `in_both_unchanged`
- `in_both_changed` (with per-key quantities and deltas)
- `only_in_snapshot_1`
- `only_in_snapshot_2`
- `delta_by_key` (`snapshot_2_total - snapshot_1_total`)

`key` accepts `"sku_warehouse"` (default), `"name_warehouse"`, `"sku"`, `"name"`, or a custom callable.

### `reconcile_combined_result(combined_result, key="sku_warehouse") -> ReconciliationSummary`

Convenience wrapper around `reconcile_rows(...)` for a `CombinedParseResult`.

### `detect_merged_duplicates(rows, key="sku_warehouse") -> list[DuplicateMergeInfo]`

Returns keys that were merged from multiple rows by deterministic addition
within a single snapshot.

## Supported Input Schemas

### `snapshot_v1`

- headers: `sku,name,quantity,location,last_counted`
- canonical mapping:
  - `sku` -> `sku`
  - `name` -> `name`
  - `quantity` -> `quantity`
  - `location` -> `location`
  - `last_counted` -> `counted_on`

### `snapshot_v2`

- headers: `sku,product_name,qty,warehouse,updated_at`
- canonical mapping:
  - `sku` -> `sku`
  - `product_name` -> `name`
  - `qty` -> `quantity`
  - `warehouse` -> `location`
  - `updated_at` -> `counted_on`

## Canonical Row Model

Each parsed row is a `UnifiedInventoryRow` with:

- `source_file`, `source_row`, `source_schema`
- `sku`, `name`, `quantity`, `location`, `counted_on`
- `raw` input values for traceability
- `issues`: list of `DataIssue`

## Normalization And Issue Codes

Common issue codes currently produced by the library:

- `missing_value`
- `whitespace_trimmed`
- `sku_format_normalized`
- `invalid_sku_format`
- `invalid_quantity`
- `non_integral_quantity`
- `decimal_quantity_format`
- `negative_quantity`
- `non_iso_date_format`
- `invalid_date`
- `row_has_extra_columns`
- `blank_row_skipped`

Notes:

- SKU normalization canonicalizes to `SKU-XXX` where possible.
- Decimal-formatted integer values like `70.0` are converted to `70` and flagged
  with `decimal_quantity_format`.
- Dates accept ISO (`YYYY-MM-DD`) and `MM/DD/YYYY`; the latter is flagged with
  `non_iso_date_format`.

## Example Usage

```python
from inventory_parser import parse_both_snapshots

result = parse_both_snapshots("data/snapshot_1.csv", "data/snapshot_2.csv")

print(result.snapshot_1.schema_name)  # snapshot_v1
print(result.snapshot_2.schema_name)  # snapshot_v2
print(len(result.all_rows()))         # 154 with current sample files

rows_with_issues = [
    row for row in result.all_rows() if row.issues
]
print(len(rows_with_issues))
```

## Tests

Library tests live in `tests/test_inventory_parser.py` and are run with:

```bash
.venv/bin/pytest -v
```
