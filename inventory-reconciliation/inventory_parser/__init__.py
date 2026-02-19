"""Public API exports for the inventory parser and reconciliation helpers."""

from .models import CombinedParseResult, DataIssue, ParseResult, UnifiedInventoryRow
from .parser import detect_schema, parse_both_snapshots, parse_snapshot
from .reconcile import (
    ChangedItem,
    DuplicateMergeInfo,
    ReconciliationKey,
    ReconciliationSummary,
    detect_merged_duplicates,
    reconcile_combined_result,
    reconcile_rows,
)

__all__ = [
    "CombinedParseResult",
    "ChangedItem",
    "DataIssue",
    "DuplicateMergeInfo",
    "ParseResult",
    "ReconciliationKey",
    "ReconciliationSummary",
    "UnifiedInventoryRow",
    "detect_merged_duplicates",
    "detect_schema",
    "parse_both_snapshots",
    "parse_snapshot",
    "reconcile_combined_result",
    "reconcile_rows",
]
