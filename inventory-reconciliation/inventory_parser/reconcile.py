"""Reconciliation helpers for comparing two parsed inventory snapshots."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Literal, TypedDict, TypeAlias

from .models import CombinedParseResult, UnifiedInventoryRow

ReconciliationKey: TypeAlias = Literal["sku", "name"]
KeyFn: TypeAlias = Callable[[UnifiedInventoryRow], str | None]
DeltaByKey: TypeAlias = dict[str, int]


class ReconciliationSummary(TypedDict):
    """Structured reconciliation output for one keying strategy."""

    only_in_snapshot_1: list[str]
    only_in_snapshot_2: list[str]
    delta_by_key: DeltaByKey


def key_by_sku(row: UnifiedInventoryRow) -> str | None:
    """Key selector that uses normalized SKU."""

    return row.sku


def key_by_name(row: UnifiedInventoryRow) -> str | None:
    """Key selector that uses normalized product name."""

    if row.name is None:
        return None
    normalized = row.name.strip().casefold()
    return normalized or None


def resolve_key_fn(key: ReconciliationKey | KeyFn) -> KeyFn:
    """Resolve a strategy key (`sku`/`name`) or pass through custom callable."""

    if callable(key):
        return key
    if key == "sku":
        return key_by_sku
    if key == "name":
        return key_by_name
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


def reconcile_rows(
    snapshot_1_rows: list[UnifiedInventoryRow],
    snapshot_2_rows: list[UnifiedInventoryRow],
    *,
    key: ReconciliationKey | KeyFn = "sku",
) -> ReconciliationSummary:
    """Reconcile two row collections and return category/delta summary."""

    key_fn = resolve_key_fn(key)
    snapshot_1_totals = aggregate_quantities(snapshot_1_rows, key_fn)
    snapshot_2_totals = aggregate_quantities(snapshot_2_rows, key_fn)

    snapshot_1_keys = set(snapshot_1_totals)
    snapshot_2_keys = set(snapshot_2_totals)
    shared_keys = snapshot_1_keys & snapshot_2_keys

    delta_by_key: DeltaByKey = {
        item_key: snapshot_2_totals[item_key] - snapshot_1_totals[item_key]
        for item_key in shared_keys
        if snapshot_1_totals[item_key] != snapshot_2_totals[item_key]
    }

    return {
        "only_in_snapshot_1": sorted(snapshot_1_keys - snapshot_2_keys),
        "only_in_snapshot_2": sorted(snapshot_2_keys - snapshot_1_keys),
        "delta_by_key": delta_by_key,
    }


def reconcile_combined_result(
    combined_result: CombinedParseResult,
    *,
    key: ReconciliationKey | KeyFn = "sku",
) -> ReconciliationSummary:
    """Reconcile snapshots contained in a `CombinedParseResult`."""

    return reconcile_rows(
        combined_result.snapshot_1.rows,
        combined_result.snapshot_2.rows,
        key=key,
    )
