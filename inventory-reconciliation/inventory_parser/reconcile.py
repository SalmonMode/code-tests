"""Reconciliation helpers for comparing two parsed inventory snapshots."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Literal, TypedDict, TypeAlias

from .models import CombinedParseResult, UnifiedInventoryRow

ReconciliationKey: TypeAlias = Literal[
    "sku",
    "name",
    "sku_warehouse",
    "name_warehouse",
]
KeyFn: TypeAlias = Callable[[UnifiedInventoryRow], str | None]
DeltaByKey: TypeAlias = dict[str, int]


class ChangedItem(TypedDict):
    """Quantity change details for a key present in both snapshots."""

    key: str
    snapshot_1_quantity: int
    snapshot_2_quantity: int
    delta: int


class ReconciliationSummary(TypedDict):
    """Structured reconciliation output for one keying strategy."""

    in_both_unchanged: list[str]
    in_both_changed: list[ChangedItem]
    only_in_snapshot_1: list[str]
    only_in_snapshot_2: list[str]
    delta_by_key: DeltaByKey


class DuplicateMergeInfo(TypedDict):
    """Duplicate-key summary after deterministic quantity merging."""

    key: str
    row_count: int
    merged_quantity: int


def key_by_sku(row: UnifiedInventoryRow) -> str | None:
    """Key selector that uses normalized SKU."""

    return row.sku


def key_by_name(row: UnifiedInventoryRow) -> str | None:
    """Key selector that uses normalized product name."""

    if row.name is None:
        return None
    normalized = row.name.strip().casefold()
    return normalized or None


def key_by_sku_warehouse(row: UnifiedInventoryRow) -> str | None:
    """Key selector that combines SKU and warehouse location.

    This avoids collapsing inventory from different warehouses under one SKU key.
    """

    sku = row.sku
    location = _normalize_location(row.location)
    if sku is None or location is None:
        return None
    return f"{sku}|{location}"


def key_by_name_warehouse(row: UnifiedInventoryRow) -> str | None:
    """Key selector that combines normalized product name and warehouse."""

    name = key_by_name(row)
    location = _normalize_location(row.location)
    if name is None or location is None:
        return None
    return f"{name}|{location}"


def _normalize_location(location: str | None) -> str | None:
    """Normalize warehouse location for keying."""

    if location is None:
        return None
    normalized = location.strip().casefold()
    return normalized or None


def resolve_key_fn(key: ReconciliationKey | KeyFn) -> KeyFn:
    """Resolve a strategy key or pass through custom callable."""

    if callable(key):
        return key
    if key == "sku":
        return key_by_sku
    if key == "name":
        return key_by_name
    if key == "sku_warehouse":
        return key_by_sku_warehouse
    if key == "name_warehouse":
        return key_by_name_warehouse
    raise ValueError(f"Unsupported reconciliation key: {key}")


def aggregate_quantities(rows: list[UnifiedInventoryRow], key_fn: KeyFn) -> DeltaByKey:
    """Aggregate row quantities by key for one snapshot.

    Rows without a key are skipped. Missing parsed quantities are treated as `0`
    so issue-flagged rows can still be included in reconciliation output.
    """

    totals: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        key = key_fn(row)
        if not key:
            continue
        quantity = 0 if row.quantity is None else row.quantity
        totals[key] += quantity
    return dict(totals)


def detect_merged_duplicates(
    rows: list[UnifiedInventoryRow],
    *,
    key: ReconciliationKey | KeyFn = "sku_warehouse",
) -> list[DuplicateMergeInfo]:
    """Return keys that were merged from multiple rows by addition.

    Reconciliation uses deterministic addition when multiple rows resolve to the
    same key. This helper exposes where that merge behavior occurred.
    """

    key_fn = resolve_key_fn(key)
    row_counts: defaultdict[str, int] = defaultdict(int)
    merged_totals: defaultdict[str, int] = defaultdict(int)

    for row in rows:
        item_key = key_fn(row)
        if not item_key:
            continue
        row_counts[item_key] += 1
        merged_totals[item_key] += 0 if row.quantity is None else row.quantity

    duplicates: list[DuplicateMergeInfo] = []
    for item_key in sorted(row_counts):
        if row_counts[item_key] <= 1:
            continue
        duplicates.append(
            {
                "key": item_key,
                "row_count": row_counts[item_key],
                "merged_quantity": merged_totals[item_key],
            }
        )
    return duplicates


def reconcile_rows(
    snapshot_1_rows: list[UnifiedInventoryRow],
    snapshot_2_rows: list[UnifiedInventoryRow],
    *,
    key: ReconciliationKey | KeyFn = "sku_warehouse",
) -> ReconciliationSummary:
    """Reconcile two row collections and return category/delta summary."""

    key_fn = resolve_key_fn(key)
    snapshot_1_totals = aggregate_quantities(snapshot_1_rows, key_fn)
    snapshot_2_totals = aggregate_quantities(snapshot_2_rows, key_fn)

    snapshot_1_keys = set(snapshot_1_totals)
    snapshot_2_keys = set(snapshot_2_totals)
    shared_keys = snapshot_1_keys & snapshot_2_keys

    unchanged_keys = sorted(
        item_key for item_key in shared_keys if snapshot_1_totals[item_key] == snapshot_2_totals[item_key]
    )
    changed_keys = sorted(
        item_key for item_key in shared_keys if snapshot_1_totals[item_key] != snapshot_2_totals[item_key]
    )

    in_both_changed: list[ChangedItem] = []
    for item_key in changed_keys:
        snapshot_1_quantity = snapshot_1_totals[item_key]
        snapshot_2_quantity = snapshot_2_totals[item_key]
        in_both_changed.append(
            {
                "key": item_key,
                "snapshot_1_quantity": snapshot_1_quantity,
                "snapshot_2_quantity": snapshot_2_quantity,
                "delta": snapshot_2_quantity - snapshot_1_quantity,
            }
        )

    delta_by_key: DeltaByKey = {item["key"]: item["delta"] for item in in_both_changed}

    return {
        "in_both_unchanged": unchanged_keys,
        "in_both_changed": in_both_changed,
        "only_in_snapshot_1": sorted(snapshot_1_keys - snapshot_2_keys),
        "only_in_snapshot_2": sorted(snapshot_2_keys - snapshot_1_keys),
        "delta_by_key": delta_by_key,
    }


def reconcile_combined_result(
    combined_result: CombinedParseResult,
    *,
    key: ReconciliationKey | KeyFn = "sku_warehouse",
) -> ReconciliationSummary:
    """Reconcile snapshots contained in a `CombinedParseResult`."""

    return reconcile_rows(
        combined_result.snapshot_1.rows,
        combined_result.snapshot_2.rows,
        key=key,
    )
