"""Tests for assignment-level reconciliation report generation."""

from __future__ import annotations

import json
from pathlib import Path

from reconcile import build_report, write_report


def _write_csv(path: Path, content: str) -> None:
    """Write CSV text fixture content to a file."""

    path.write_text(content, encoding="utf-8")


def test_build_report_has_required_sections_and_counts(tmp_path: Path) -> None:
    """Report should include explicit in-both sections and merge rule metadata."""
    snapshot_1 = tmp_path / "snapshot_1.csv"
    snapshot_2 = tmp_path / "snapshot_2.csv"

    _write_csv(
        snapshot_1,
        (
            "sku,name,quantity,location,last_counted\n"
            "SKU-001,Widget A,10,Warehouse A,2024-01-08\n"
            "SKU-001,Widget A,5,Warehouse A,2024-01-08\n"
            "SKU-002,Widget B,4,Warehouse B,2024-01-08\n"
        ),
    )
    _write_csv(
        snapshot_2,
        (
            "sku,product_name,qty,warehouse,updated_at\n"
            "SKU-001,Widget A,20,Warehouse A,2024-01-15\n"
            "SKU-003,Widget C,2,Warehouse C,2024-01-15\n"
        ),
    )

    report = build_report(
        snapshot_1_path=snapshot_1,
        snapshot_2_path=snapshot_2,
        key_strategy="sku_warehouse",
    )

    assert "deterministic_merge_rule" in report["metadata"]
    assert "addition" in report["metadata"]["deterministic_merge_rule"]

    reconciliation = report["reconciliation"]
    assert reconciliation["in_both_unchanged"] == []
    assert reconciliation["in_both_changed"] == [
        {
            "key": "SKU-001|warehouse a",
            "snapshot_1_quantity": 15,
            "snapshot_2_quantity": 20,
            "delta": 5,
        }
    ]
    assert reconciliation["only_in_snapshot_1"] == ["SKU-002|warehouse b"]
    assert reconciliation["only_in_snapshot_2"] == ["SKU-003|warehouse c"]

    summary = report["summary"]
    assert summary["in_both_changed_count"] == 1
    assert summary["in_both_unchanged_count"] == 0
    assert summary["only_in_snapshot_1_count"] == 1
    assert summary["only_in_snapshot_2_count"] == 1

    merged_duplicates = report["data_quality_issues"]["duplicate_keys_merged_by_addition"]
    assert merged_duplicates["snapshot_1"] == [
        {
            "key": "SKU-001|warehouse a",
            "row_count": 2,
            "merged_quantity": 15,
        }
    ]
    assert merged_duplicates["snapshot_2"] == []


def test_write_report_writes_valid_json(tmp_path: Path) -> None:
    """`write_report` should create parent directory and emit valid JSON."""
    output_path = tmp_path / "output" / "report.json"
    report = {
        "metadata": {"generated_at_utc": "2026-01-01T00:00:00+00:00"},
        "summary": {},
        "reconciliation": {},
        "data_quality_issues": {},
    }

    write_report(report, output_path=output_path)

    assert output_path.exists()
    parsed = json.loads(output_path.read_text(encoding="utf-8"))
    assert parsed == report
