from __future__ import annotations

"""Schema-detection and parser edge-case tests.

These tests target behavior that is easy to break when modifying header
matching or CSV ingestion logic.
"""

import pytest

from inventory_parser.parser import detect_schema, parse_snapshot


def _issue_codes(issues: list[object]) -> set[str]:
    return {issue.code for issue in issues}


def test_detect_schema_matches_with_whitespace_and_case_variation() -> None:
    """Known schemas should still match when header formatting is inconsistent."""
    headers = [" SKU ", "Name", "QUANTITY", "location", " last_counted "]
    schema = detect_schema(headers)
    assert schema.name == "snapshot_v1"


def test_detect_schema_requires_header_row() -> None:
    """Header-less inputs should fail fast with a clear error."""
    with pytest.raises(ValueError, match="CSV file has no header row"):
        detect_schema([])


def test_detect_schema_rejects_unknown_field_set() -> None:
    """Unsupported header sets should be rejected to avoid silent mis-parsing."""
    with pytest.raises(ValueError, match="Unrecognized CSV schema fields"):
        detect_schema(["sku", "name", "qty", "location", "when_counted"])


def test_parse_snapshot_flags_file_level_issues(tmp_path) -> None:
    """Parser should keep valid rows while reporting file-level CSV issues."""
    csv_path = tmp_path / "custom_snapshot.csv"
    csv_path.write_text(
        "sku,name,quantity,location,last_counted\n"
        "SKU-001,Widget A,10,Warehouse A,2024-01-08\n"
        ",,,,\n"
        "SKU-002,Widget B,20,Warehouse B,2024-01-09,EXTRA\n",
        encoding="utf-8",
    )

    result = parse_snapshot(csv_path)
    file_issue_codes = _issue_codes(result.file_issues)

    assert result.schema_name == "snapshot_v1"
    assert result.total_rows == 2
    assert file_issue_codes == {"blank_row_skipped", "row_has_extra_columns"}
    assert result.rows[0].source_schema == "snapshot_v1"
    assert result.rows[1].sku == "SKU-002"


def test_parse_snapshot_raises_for_unknown_schema(tmp_path) -> None:
    """Files with unrecognized schemas should raise instead of guessing mappings."""
    csv_path = tmp_path / "unknown_schema.csv"
    csv_path.write_text(
        "item_id,item_name,count,site,date_seen\n"
        "1,Widget A,10,Warehouse A,2024-01-08\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unrecognized CSV schema fields"):
        parse_snapshot(csv_path)
