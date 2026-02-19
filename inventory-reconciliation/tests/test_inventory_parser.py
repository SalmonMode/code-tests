from __future__ import annotations

"""Behavior-focused tests for the inventory parsing layer.

These tests intentionally check both "happy path" parsing and known data-quality
anomalies in the provided snapshots. Together they document what the parser
normalizes and what it flags as issues.
"""

from pathlib import Path

from inventory_parser import parse_both_snapshots, parse_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_1 = PROJECT_ROOT / "data" / "snapshot_1.csv"
SNAPSHOT_2 = PROJECT_ROOT / "data" / "snapshot_2.csv"


def test_parse_snapshot_1_schema_and_row_count() -> None:
    """Snapshot 1 should match the v1 schema and produce 75 data rows."""
    result = parse_snapshot(SNAPSHOT_1)
    assert result.schema_name == "snapshot_v1"
    assert result.total_rows == 75


def test_parse_snapshot_2_schema_and_row_count() -> None:
    """Snapshot 2 should match the v2 schema and produce 79 data rows."""
    result = parse_snapshot(SNAPSHOT_2)
    assert result.schema_name == "snapshot_v2"
    assert result.total_rows == 79


def test_sku_normalization_and_row_issues() -> None:
    """Parser should normalize malformed SKUs and flag important row-level issues.

    Validates three behaviors that are essential for reconciliation:
    1. SKU formatting is normalized to canonical `SKU-XXX`.
    2. Negative quantities are preserved but flagged.
    3. Non-ISO dates are parsed but flagged for quality reporting.
    """
    result = parse_snapshot(SNAPSHOT_2)
    row_by_line = {row.source_row: row for row in result.rows}

    # Source rows 6, 9, and 19 contain known SKU formatting anomalies.
    assert row_by_line[6].sku == "SKU-005"
    assert row_by_line[9].sku == "SKU-008"
    assert row_by_line[19].sku == "SKU-018"
    assert any(issue.code == "sku_format_normalized" for issue in row_by_line[6].issues)

    # Source row 54 contains a negative quantity anomaly.
    assert row_by_line[54].quantity == -5
    assert any(issue.code == "negative_quantity" for issue in row_by_line[54].issues)
    # Source row 34 uses MM/DD/YYYY instead of ISO-8601.
    assert any(issue.code == "non_iso_date_format" for issue in row_by_line[34].issues)


def test_parse_both_snapshots_returns_unified_collection() -> None:
    """Combined parse should include both snapshots and all parsed rows."""
    combined = parse_both_snapshots(SNAPSHOT_1, SNAPSHOT_2)
    assert combined.snapshot_1.total_rows == 75
    assert combined.snapshot_2.total_rows == 79
    assert len(combined.all_rows()) == 154
