from __future__ import annotations

"""Delta-focused reconciliation tests for key strategy comparison.

These tests validate reconciliation outcomes when keyed by SKU versus product
name and explicitly compare the resulting delta maps between strategies.
"""

from collections import defaultdict
from pathlib import Path
from typing import Callable, TypedDict

from inventory_parser import parse_both_snapshots
from inventory_parser.models import UnifiedInventoryRow

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_1 = PROJECT_ROOT / "data" / "snapshot_1.csv"
SNAPSHOT_2 = PROJECT_ROOT / "data" / "snapshot_2.csv"

KeyFn = Callable[[UnifiedInventoryRow], str | None]
DeltaByKey = dict[str, int]


class ReconciliationSummary(TypedDict):
    only_in_snapshot_1: list[str]
    only_in_snapshot_2: list[str]
    delta_by_key: DeltaByKey


def _reconcile_summary(
    snapshot_1_rows: list[UnifiedInventoryRow],
    snapshot_2_rows: list[UnifiedInventoryRow],
    key_fn: KeyFn,
) -> ReconciliationSummary:
    """Build reconciliation summary with explicit quantity deltas."""

    def aggregate(rows: list[UnifiedInventoryRow]) -> DeltaByKey:
        totals: defaultdict[str, int] = defaultdict(int)
        for row in rows:
            key = key_fn(row)
            if not key:
                continue
            quantity = 0 if row.quantity is None else row.quantity
            totals[key] += quantity
        return dict(totals)

    snapshot_1_totals = aggregate(snapshot_1_rows)
    snapshot_2_totals = aggregate(snapshot_2_rows)

    snapshot_1_keys = set(snapshot_1_totals)
    snapshot_2_keys = set(snapshot_2_totals)
    shared_keys = snapshot_1_keys & snapshot_2_keys

    delta_by_key: DeltaByKey = {
        key: snapshot_2_totals[key] - snapshot_1_totals[key]
        for key in shared_keys
        if snapshot_1_totals[key] != snapshot_2_totals[key]
    }

    return {
        "only_in_snapshot_1": sorted(snapshot_1_keys - snapshot_2_keys),
        "only_in_snapshot_2": sorted(snapshot_2_keys - snapshot_1_keys),
        "delta_by_key": delta_by_key,
    }


def test_reconciliation_using_sku_key_tracks_expected_deltas() -> None:
    """SKU-keyed reconciliation should produce expected category and delta output."""
    combined = parse_both_snapshots(SNAPSHOT_1, SNAPSHOT_2)

    by_sku = _reconcile_summary(
        combined.snapshot_1.rows,
        combined.snapshot_2.rows,
        key_fn=lambda row: row.sku,
    )

    assert by_sku["only_in_snapshot_1"] == ["SKU-025", "SKU-026"]
    assert by_sku["only_in_snapshot_2"] == [
        "SKU-076",
        "SKU-077",
        "SKU-078",
        "SKU-079",
        "SKU-080",
    ]
    assert len(by_sku["delta_by_key"]) == 71
    assert by_sku["delta_by_key"]["SKU-016"] == -15
    assert by_sku["delta_by_key"]["SKU-045"] == -7


def test_reconciliation_using_product_name_key_compares_deltas_against_sku_key() -> None:
    """Name-keyed and SKU-keyed delta maps should differ on current sample data."""
    combined = parse_both_snapshots(SNAPSHOT_1, SNAPSHOT_2)

    by_sku = _reconcile_summary(
        combined.snapshot_1.rows,
        combined.snapshot_2.rows,
        key_fn=lambda row: row.sku,
    )
    by_name = _reconcile_summary(
        combined.snapshot_1.rows,
        combined.snapshot_2.rows,
        key_fn=lambda row: (row.name or "").casefold(),
    )

    assert by_name["only_in_snapshot_1"] == ["dvi cable", "vga cable"]
    assert "multimeter professional" in by_name["only_in_snapshot_2"]
    assert len(by_name["delta_by_key"]) == 71
    assert by_name["delta_by_key"]["usb hub 4-port"] == -15
    assert by_name["delta_by_key"]["multimeter pro"] == -30

    # Explicit strategy-vs-strategy checks.
    assert by_name["delta_by_key"] != by_sku["delta_by_key"]
    assert by_name["only_in_snapshot_2"] != by_sku["only_in_snapshot_2"]
    assert sum(by_name["delta_by_key"].values()) != sum(by_sku["delta_by_key"].values())
