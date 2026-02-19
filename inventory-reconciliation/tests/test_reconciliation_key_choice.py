"""Delta-focused reconciliation tests for key strategy comparison.

These tests validate reconciliation outcomes when keyed by SKU versus product
name and explicitly compare the resulting delta maps between strategies.
"""

from __future__ import annotations

from pathlib import Path

from inventory_parser import parse_both_snapshots, reconcile_combined_result

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_1 = PROJECT_ROOT / "data" / "snapshot_1.csv"
SNAPSHOT_2 = PROJECT_ROOT / "data" / "snapshot_2.csv"

def test_reconciliation_using_sku_key_tracks_expected_deltas() -> None:
    """SKU-keyed reconciliation should produce expected category and delta output."""
    combined = parse_both_snapshots(SNAPSHOT_1, SNAPSHOT_2)
    by_sku = reconcile_combined_result(combined, key="sku")

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

    by_sku = reconcile_combined_result(combined, key="sku")
    by_name = reconcile_combined_result(combined, key="name")

    assert by_name["only_in_snapshot_1"] == ["dvi cable", "vga cable"]
    assert "multimeter professional" in by_name["only_in_snapshot_2"]
    assert len(by_name["delta_by_key"]) == 71
    assert by_name["delta_by_key"]["usb hub 4-port"] == -15
    assert by_name["delta_by_key"]["multimeter pro"] == -30

    # Explicit strategy-vs-strategy checks.
    assert by_name["delta_by_key"] != by_sku["delta_by_key"]
    assert by_name["only_in_snapshot_2"] != by_sku["only_in_snapshot_2"]
    assert sum(by_name["delta_by_key"].values()) != sum(by_sku["delta_by_key"].values())
