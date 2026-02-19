"""Small-scale unit tests for reconciliation utility functions.

These tests use explicit handcrafted rows so each reconciliation helper can be
verified in isolation without relying on the larger snapshot fixture files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from inventory_parser.models import CombinedParseResult, ParseResult, UnifiedInventoryRow
from inventory_parser.reconcile import (
    aggregate_quantities,
    key_by_name,
    key_by_sku,
    reconcile_combined_result,
    reconcile_rows,
    resolve_key_fn,
)


def _row(
    *,
    sku: str | None,
    name: str | None,
    quantity: int | None,
    source_row: int = 1,
) -> UnifiedInventoryRow:
    """Build a minimal canonical row for targeted reconciliation tests."""
    return UnifiedInventoryRow(
        source_file="unit-test.csv",
        source_row=source_row,
        source_schema="unit",
        sku=sku,
        name=name,
        quantity=quantity,
        location=None,
        counted_on=None,
        raw={},
        issues=[],
    )


def test_key_by_sku_returns_sku_value() -> None:
    """`key_by_sku` should return the row SKU as-is."""
    row = _row(sku="SKU-101", name="Widget A", quantity=3)
    assert key_by_sku(row) == "SKU-101"


def test_key_by_name_normalizes_and_handles_empty_values() -> None:
    """`key_by_name` should case-normalize and trim names, and drop empties."""
    normalized = key_by_name(_row(sku="SKU-101", name="  Widget A  ", quantity=3))
    assert normalized == "widget a"

    blank_name = key_by_name(_row(sku="SKU-102", name="   ", quantity=3))
    missing_name = key_by_name(_row(sku="SKU-103", name=None, quantity=3))
    assert blank_name is None
    assert missing_name is None


def test_resolve_key_fn_supports_named_and_callable_strategies() -> None:
    """`resolve_key_fn` should support built-ins and custom callables."""
    custom = lambda row: row.sku
    assert resolve_key_fn("sku") is key_by_sku
    assert resolve_key_fn("name") is key_by_name
    assert resolve_key_fn(custom) is custom


def test_resolve_key_fn_rejects_unknown_key_name() -> None:
    """`resolve_key_fn` should fail fast for unsupported strategy names."""
    with pytest.raises(ValueError, match="Unsupported reconciliation key"):
        resolve_key_fn(cast(Any, "category"))


def test_aggregate_quantities_accumulates_and_handles_none_quantity() -> None:
    """Aggregation should sum per key, skip missing keys, and treat None as 0."""
    rows = [
        _row(sku="SKU-001", name="Widget A", quantity=3, source_row=1),
        _row(sku="SKU-001", name="Widget A", quantity=2, source_row=2),
        _row(sku=None, name="No SKU", quantity=7, source_row=3),
        _row(sku="SKU-002", name="Widget B", quantity=None, source_row=4),
    ]

    totals = aggregate_quantities(rows, key_by_sku)
    assert totals == {"SKU-001": 5, "SKU-002": 0}


def test_reconcile_rows_with_sku_key_reports_add_remove_and_delta() -> None:
    """SKU-key reconciliation should report clear add/remove and delta output."""
    snapshot_1_rows = [
        _row(sku="SKU-A", name="Alpha", quantity=10, source_row=1),
        _row(sku="SKU-B", name="Beta", quantity=5, source_row=2),
        _row(sku="SKU-C", name="Gamma", quantity=2, source_row=3),
    ]
    snapshot_2_rows = [
        _row(sku="SKU-A", name="Alpha", quantity=7, source_row=1),
        _row(sku="SKU-B", name="Beta", quantity=5, source_row=2),
        _row(sku="SKU-D", name="Delta", quantity=4, source_row=3),
    ]

    summary = reconcile_rows(snapshot_1_rows, snapshot_2_rows, key="sku")
    assert summary["only_in_snapshot_1"] == ["SKU-C"]
    assert summary["only_in_snapshot_2"] == ["SKU-D"]
    assert summary["delta_by_key"] == {"SKU-A": -3}


def test_reconcile_rows_with_name_key_normalizes_matching() -> None:
    """Name-key reconciliation should match case/whitespace-equivalent names."""
    snapshot_1_rows = [
        _row(sku="SKU-1", name=" Widget A ", quantity=10, source_row=1),
        _row(sku="SKU-2", name="Widget B", quantity=5, source_row=2),
    ]
    snapshot_2_rows = [
        _row(sku="SKU-3", name="widget a", quantity=12, source_row=1),
        _row(sku="SKU-4", name="Widget C", quantity=2, source_row=2),
    ]

    summary = reconcile_rows(snapshot_1_rows, snapshot_2_rows, key="name")
    assert summary["only_in_snapshot_1"] == ["widget b"]
    assert summary["only_in_snapshot_2"] == ["widget c"]
    assert summary["delta_by_key"] == {"widget a": 2}


def test_reconcile_rows_with_custom_key_function() -> None:
    """Custom key strategies should be usable for domain-specific grouping."""

    def key_by_first_token(row: UnifiedInventoryRow) -> str | None:
        if row.name is None:
            return None
        token = row.name.split()[0].strip().casefold()
        return token or None

    snapshot_1_rows = [
        _row(sku="SKU-1", name="Alpha One", quantity=1, source_row=1),
        _row(sku="SKU-2", name="Beta One", quantity=2, source_row=2),
    ]
    snapshot_2_rows = [
        _row(sku="SKU-3", name="alpha Two", quantity=4, source_row=1),
        _row(sku="SKU-4", name="Gamma One", quantity=3, source_row=2),
    ]

    summary = reconcile_rows(snapshot_1_rows, snapshot_2_rows, key=key_by_first_token)
    assert summary["only_in_snapshot_1"] == ["beta"]
    assert summary["only_in_snapshot_2"] == ["gamma"]
    assert summary["delta_by_key"] == {"alpha": 3}


def test_reconcile_combined_result_matches_reconcile_rows() -> None:
    """Combined-result wrapper should match direct row-based reconciliation."""
    snapshot_1_rows = [_row(sku="SKU-A", name="Alpha", quantity=2, source_row=1)]
    snapshot_2_rows = [_row(sku="SKU-A", name="Alpha", quantity=6, source_row=1)]

    combined = CombinedParseResult(
        snapshot_1=ParseResult(
            file_path=Path("snapshot_1.csv"),
            schema_name="unit",
            rows=snapshot_1_rows,
            file_issues=[],
        ),
        snapshot_2=ParseResult(
            file_path=Path("snapshot_2.csv"),
            schema_name="unit",
            rows=snapshot_2_rows,
            file_issues=[],
        ),
    )

    direct = reconcile_rows(snapshot_1_rows, snapshot_2_rows, key="sku")
    wrapped = reconcile_combined_result(combined, key="sku")
    assert wrapped == direct
