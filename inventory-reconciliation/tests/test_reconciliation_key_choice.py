"""Delta-focused reconciliation tests for key strategy comparison.

These tests validate reconciliation outcomes when keyed by SKU+warehouse versus
product-name+warehouse and explicitly compare delta maps between strategies.
"""

from __future__ import annotations

from pathlib import Path

from inventory_parser import parse_both_snapshots, reconcile_combined_result

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_1 = PROJECT_ROOT / "data" / "snapshot_1.csv"
SNAPSHOT_2 = PROJECT_ROOT / "data" / "snapshot_2.csv"

def test_reconciliation_using_sku_warehouse_key_tracks_expected_deltas() -> None:
    """SKU+warehouse reconciliation should produce expected category/delta output."""
    combined = parse_both_snapshots(SNAPSHOT_1, SNAPSHOT_2)
    by_sku = reconcile_combined_result(combined, key="sku_warehouse")

    assert by_sku["only_in_snapshot_1"] == ["SKU-025|warehouse b", "SKU-026|warehouse b"]
    assert by_sku["only_in_snapshot_2"] == [
        "SKU-045|warehouse b",
        "SKU-076|warehouse a",
        "SKU-077|warehouse a",
        "SKU-078|warehouse a",
        "SKU-079|warehouse a",
        "SKU-080|warehouse a",
    ]
    assert len(by_sku["delta_by_key"]) == 71
    assert len(by_sku["in_both_changed"]) == 71
    assert len(by_sku["in_both_unchanged"]) == 2
    assert by_sku["delta_by_key"]["SKU-016|warehouse a"] == -15
    assert by_sku["delta_by_key"]["SKU-045|warehouse a"] == -2


def test_reconciliation_using_name_warehouse_key_compares_deltas_against_sku_warehouse_key() -> None:
    """Name+warehouse and SKU+warehouse delta maps should differ on sample data."""
    combined = parse_both_snapshots(SNAPSHOT_1, SNAPSHOT_2)

    by_sku = reconcile_combined_result(combined, key="sku_warehouse")
    by_name = reconcile_combined_result(combined, key="name_warehouse")

    assert by_name["only_in_snapshot_1"] == [
        "dvi cable|warehouse b",
        "multimeter pro|warehouse a",
        "vga cable|warehouse b",
    ]
    assert "multimeter professional|warehouse a" in by_name["only_in_snapshot_2"]
    assert "multimeter pro|warehouse b" in by_name["only_in_snapshot_2"]
    assert len(by_name["delta_by_key"]) == 70
    assert len(by_name["in_both_changed"]) == 70
    assert len(by_name["in_both_unchanged"]) == 2
    assert by_name["delta_by_key"]["usb hub 4-port|warehouse a"] == -15

    # Explicit strategy-vs-strategy checks.
    assert by_name["delta_by_key"] != by_sku["delta_by_key"]
    assert by_name["only_in_snapshot_2"] != by_sku["only_in_snapshot_2"]
    assert sum(by_name["delta_by_key"].values()) != sum(by_sku["delta_by_key"].values())
