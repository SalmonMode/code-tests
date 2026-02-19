"""Assignment runner for inventory reconciliation.

This script parses both snapshot files, performs reconciliation, and writes a
structured JSON report under `output/` by default.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inventory_parser import parse_both_snapshots
from inventory_parser.models import DataIssue, ParseResult, UnifiedInventoryRow
from inventory_parser.reconcile import ReconciliationKey, detect_merged_duplicates, reconcile_combined_result

DEFAULT_SNAPSHOT_1 = Path("data/snapshot_1.csv")
DEFAULT_SNAPSHOT_2 = Path("data/snapshot_2.csv")
DEFAULT_OUTPUT = Path("output/reconciliation_report.json")


def _issue_to_dict(issue: DataIssue) -> dict[str, str | None]:
    """Serialize a `DataIssue` into a JSON-friendly dictionary."""

    return {
        "code": issue.code,
        "field": issue.field,
        "message": issue.message,
    }


def _collect_file_issues(result: ParseResult, *, snapshot: str) -> list[dict[str, str | None]]:
    """Collect file-level issues for one parsed snapshot."""

    issues: list[dict[str, str | None]] = []
    for issue in result.file_issues:
        item = _issue_to_dict(issue)
        item["snapshot"] = snapshot
        issues.append(item)
    return issues


def _collect_row_issues(rows: list[UnifiedInventoryRow], *, snapshot: str) -> list[dict[str, Any]]:
    """Collect row-level issues for one snapshot."""

    issues: list[dict[str, Any]] = []
    for row in rows:
        for issue in row.issues:
            issues.append(
                {
                    "snapshot": snapshot,
                    "source_file": row.source_file,
                    "source_row": row.source_row,
                    "key_fields": {
                        "sku": row.sku,
                        "name": row.name,
                        "location": row.location,
                    },
                    "issue": _issue_to_dict(issue),
                }
            )
    return issues


def build_report(
    *,
    snapshot_1_path: Path,
    snapshot_2_path: Path,
    key_strategy: ReconciliationKey,
) -> dict[str, Any]:
    """Build a complete reconciliation report payload."""

    combined = parse_both_snapshots(snapshot_1_path, snapshot_2_path)
    reconciliation = reconcile_combined_result(combined, key=key_strategy)

    snapshot_1_duplicates = detect_merged_duplicates(combined.snapshot_1.rows, key=key_strategy)
    snapshot_2_duplicates = detect_merged_duplicates(combined.snapshot_2.rows, key=key_strategy)

    file_issues = [
        *_collect_file_issues(combined.snapshot_1, snapshot="snapshot_1"),
        *_collect_file_issues(combined.snapshot_2, snapshot="snapshot_2"),
    ]
    row_issues = [
        *_collect_row_issues(combined.snapshot_1.rows, snapshot="snapshot_1"),
        *_collect_row_issues(combined.snapshot_2.rows, snapshot="snapshot_2"),
    ]

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "snapshot_1_path": str(snapshot_1_path),
            "snapshot_2_path": str(snapshot_2_path),
            "key_strategy": key_strategy,
            "deterministic_merge_rule": (
                "If multiple rows resolve to the same reconciliation key within a snapshot, "
                "their quantities are merged by deterministic addition."
            ),
        },
        "summary": {
            "snapshot_1_row_count": combined.snapshot_1.total_rows,
            "snapshot_2_row_count": combined.snapshot_2.total_rows,
            "in_both_changed_count": len(reconciliation["in_both_changed"]),
            "in_both_unchanged_count": len(reconciliation["in_both_unchanged"]),
            "only_in_snapshot_1_count": len(reconciliation["only_in_snapshot_1"]),
            "only_in_snapshot_2_count": len(reconciliation["only_in_snapshot_2"]),
        },
        "reconciliation": reconciliation,
        "data_quality_issues": {
            "file_issues": file_issues,
            "row_issues": row_issues,
            "duplicate_keys_merged_by_addition": {
                "snapshot_1": snapshot_1_duplicates,
                "snapshot_2": snapshot_2_duplicates,
            },
        },
    }


def write_report(report: dict[str, Any], *, output_path: Path) -> None:
    """Write report JSON to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for report generation."""

    parser = argparse.ArgumentParser(description="Run inventory reconciliation and emit JSON report.")
    parser.add_argument("--snapshot-1", type=Path, default=DEFAULT_SNAPSHOT_1, help="Path to snapshot 1 CSV")
    parser.add_argument("--snapshot-2", type=Path, default=DEFAULT_SNAPSHOT_2, help="Path to snapshot 2 CSV")
    parser.add_argument(
        "--key-strategy",
        choices=["sku_warehouse", "name_warehouse", "sku", "name"],
        default="sku_warehouse",
        help="Reconciliation key strategy",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    return parser.parse_args()


def main() -> int:
    """Entrypoint for command-line execution."""

    args = _parse_args()
    report = build_report(
        snapshot_1_path=args.snapshot_1,
        snapshot_2_path=args.snapshot_2,
        key_strategy=args.key_strategy,
    )
    write_report(report, output_path=args.output)
    print(f"Wrote reconciliation report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
