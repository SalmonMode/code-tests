from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DataIssue:
    code: str
    message: str
    field: str | None = None


@dataclass(slots=True)
class UnifiedInventoryRow:
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
        return bool(self.issues)


@dataclass(slots=True)
class ParseResult:
    file_path: Path
    schema_name: str
    rows: list[UnifiedInventoryRow]
    file_issues: list[DataIssue] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return len(self.rows)

    @property
    def rows_with_issues(self) -> int:
        return sum(1 for row in self.rows if row.has_issues)


@dataclass(slots=True)
class CombinedParseResult:
    snapshot_1: ParseResult
    snapshot_2: ParseResult

    def all_rows(self) -> list[UnifiedInventoryRow]:
        return [*self.snapshot_1.rows, *self.snapshot_2.rows]
