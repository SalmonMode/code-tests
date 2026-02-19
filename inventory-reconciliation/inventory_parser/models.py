"""Core typed models shared by parser and reconciliation modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DataIssue:
    """Structured data-quality issue emitted during parsing or reconciliation."""

    code: str
    message: str
    field: str | None = None


@dataclass(slots=True)
class UnifiedInventoryRow:
    """Canonical representation of one inventory row after normalization."""

    source_file: str
    source_row: int
    source_schema: str
    sku: str | None
    name: str | None
    quantity: int | None
    location: str | None
    counted_on: date | None
    raw: dict[str, str | None]
    issues: list[DataIssue] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """Return whether the row has one or more associated issues."""

        return bool(self.issues)


@dataclass(slots=True)
class ParseResult:
    """Parsed output for one snapshot file."""

    file_path: Path
    schema_name: str
    rows: list[UnifiedInventoryRow]
    file_issues: list[DataIssue] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        """Return the total number of parsed, non-skipped rows."""

        return len(self.rows)

    @property
    def rows_with_issues(self) -> int:
        """Return the number of parsed rows that contain one or more issues."""

        return sum(1 for row in self.rows if row.has_issues)


@dataclass(slots=True)
class CombinedParseResult:
    """Container for both parsed snapshots."""

    snapshot_1: ParseResult
    snapshot_2: ParseResult

    def all_rows(self) -> list[UnifiedInventoryRow]:
        """Return a flat list of rows from both snapshots."""

        return [*self.snapshot_1.rows, *self.snapshot_2.rows]
