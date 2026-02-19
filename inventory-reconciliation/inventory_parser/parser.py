"""Schema-aware CSV parser for inventory snapshots."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .models import CombinedParseResult, DataIssue, ParseResult, UnifiedInventoryRow
from .normalize import normalize_sku, normalize_text, parse_inventory_date, parse_quantity


@dataclass(frozen=True, slots=True)
class SchemaDefinition:
    """Defines how an input schema maps to canonical row fields."""

    name: str
    fields: frozenset[str]
    column_map: dict[str, str]


_SCHEMAS = (
    SchemaDefinition(
        name="snapshot_v1",
        fields=frozenset({"sku", "name", "quantity", "location", "last_counted"}),
        column_map={
            "sku": "sku",
            "name": "name",
            "quantity": "quantity",
            "location": "location",
            "counted_on": "last_counted",
        },
    ),
    SchemaDefinition(
        name="snapshot_v2",
        fields=frozenset({"sku", "product_name", "qty", "warehouse", "updated_at"}),
        column_map={
            "sku": "sku",
            "name": "product_name",
            "quantity": "qty",
            "location": "warehouse",
            "counted_on": "updated_at",
        },
    ),
)


def _normalize_header(header: str | None) -> str:
    """Normalize header names so schema matching is resilient to formatting."""

    if header is None:
        return ""
    return header.strip().lower()


def detect_schema(headers: list[str] | None) -> SchemaDefinition:
    """Return the matching schema definition for a header row.

    Matching is exact by normalized header set so unknown schema drift fails
    fast instead of silently mis-mapping columns.
    """

    if not headers:
        raise ValueError("CSV file has no header row")

    normalized_fields = frozenset(_normalize_header(header) for header in headers if header is not None)
    for schema in _SCHEMAS:
        if normalized_fields == schema.fields:
            return schema

    sorted_fields = ", ".join(sorted(normalized_fields))
    raise ValueError(f"Unrecognized CSV schema fields: {sorted_fields}")


def _is_blank_row(raw_row: dict[str | None, str | None], headers: list[str]) -> bool:
    """Return True when all declared columns in a row are empty."""

    for header in headers:
        value = raw_row.get(header)
        if value is None:
            continue
        if value.strip() != "":
            return False
    return True


def _to_row(
    *,
    raw_row: dict[str | None, str | None],
    line_number: int,
    source_file: Path,
    schema: SchemaDefinition,
) -> UnifiedInventoryRow:
    """Convert one raw CSV row into a canonical row with issue metadata."""

    issues: list[DataIssue] = []

    sku_raw = raw_row.get(schema.column_map["sku"])
    name_raw = raw_row.get(schema.column_map["name"])
    quantity_raw = raw_row.get(schema.column_map["quantity"])
    location_raw = raw_row.get(schema.column_map["location"])
    counted_on_raw = raw_row.get(schema.column_map["counted_on"])

    sku, sku_issues = normalize_sku(sku_raw)
    name, name_issues = normalize_text(name_raw, field="name")
    quantity, quantity_issues = parse_quantity(quantity_raw)
    location, location_issues = normalize_text(location_raw, field="location")
    counted_on, date_issues = parse_inventory_date(counted_on_raw)

    issues.extend(sku_issues)
    issues.extend(name_issues)
    issues.extend(quantity_issues)
    issues.extend(location_issues)
    issues.extend(date_issues)

    return UnifiedInventoryRow(
        source_file=str(source_file),
        source_row=line_number,
        source_schema=schema.name,
        sku=sku,
        name=name,
        quantity=quantity,
        location=location,
        counted_on=counted_on,
        raw={
            "sku": sku_raw,
            "name": name_raw,
            "quantity": quantity_raw,
            "location": location_raw,
            "counted_on": counted_on_raw,
        },
        issues=issues,
    )


def parse_snapshot(csv_path: str | Path) -> ParseResult:
    """Parse one snapshot CSV into canonical rows and file-level issues."""

    path = Path(csv_path)
    file_issues: list[DataIssue] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        schema = detect_schema(headers)
        rows: list[UnifiedInventoryRow] = []

        for line_number, raw_row in enumerate(reader, start=2):
            if raw_row is None:
                continue

            if None in raw_row:
                # DictReader uses `None` for extra unnamed columns.
                file_issues.append(
                    DataIssue(
                        code="row_has_extra_columns",
                        message=f"Row {line_number} has more columns than the header",
                    )
                )

            if _is_blank_row(raw_row, headers):
                file_issues.append(
                    DataIssue(
                        code="blank_row_skipped",
                        message=f"Row {line_number} is blank and was skipped",
                    )
                )
                continue

            rows.append(
                _to_row(
                    raw_row=raw_row,
                    line_number=line_number,
                    source_file=path,
                    schema=schema,
                )
            )

    return ParseResult(file_path=path, schema_name=schema.name, rows=rows, file_issues=file_issues)


def parse_both_snapshots(snapshot_1_path: str | Path, snapshot_2_path: str | Path) -> CombinedParseResult:
    """Parse both snapshots and return them as one combined structure."""

    return CombinedParseResult(
        snapshot_1=parse_snapshot(snapshot_1_path),
        snapshot_2=parse_snapshot(snapshot_2_path),
    )
