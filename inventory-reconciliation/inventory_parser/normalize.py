"""Field-level normalization helpers used by inventory parsing."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .models import DataIssue

_SKU_STANDARD_RE = re.compile(r"^SKU-\d{3}$")
_SKU_NO_HYPHEN_RE = re.compile(r"^SKU\d{3}$")


def normalize_text(value: str | None, *, field: str) -> tuple[str | None, list[DataIssue]]:
    """Trim text, collapse empty values to None, and emit quality issues."""

    if value is None:
        return None, [DataIssue(code="missing_value", message=f"{field} is missing", field=field)]

    stripped = value.strip()
    issues: list[DataIssue] = []

    if stripped == "":
        issues.append(DataIssue(code="missing_value", message=f"{field} is empty", field=field))
        return None, issues

    if stripped != value:
        issues.append(
            DataIssue(
                code="whitespace_trimmed",
                message=f"{field} had leading/trailing whitespace",
                field=field,
            )
        )

    return stripped, issues


def normalize_sku(value: str | None) -> tuple[str | None, list[DataIssue]]:
    """Normalize SKU formatting to canonical `SKU-XXX` when possible."""

    cleaned, issues = normalize_text(value, field="sku")
    if cleaned is None:
        return None, issues

    candidate = re.sub(r"\s+", "", cleaned.upper())

    if _SKU_STANDARD_RE.match(candidate):
        if candidate != cleaned:
            issues.append(
                DataIssue(
                    code="sku_format_normalized",
                    message="SKU casing/spacing was normalized",
                    field="sku",
                )
            )
        return candidate, issues

    if _SKU_NO_HYPHEN_RE.match(candidate):
        normalized = f"SKU-{candidate[-3:]}"
        issues.append(
            DataIssue(
                code="sku_format_normalized",
                message="SKU missing hyphen was normalized",
                field="sku",
            )
        )
        return normalized, issues

    issues.append(
        DataIssue(
            code="invalid_sku_format",
            message=f"SKU has unexpected format: {cleaned}",
            field="sku",
        )
    )
    return candidate, issues


def parse_quantity(value: str | None) -> tuple[int | None, list[DataIssue]]:
    """Parse quantity as int and emit issues for invalid or unusual formats."""

    cleaned, issues = normalize_text(value, field="quantity")
    if cleaned is None:
        return None, issues

    try:
        parsed = Decimal(cleaned)
    except InvalidOperation:
        issues.append(
            DataIssue(
                code="invalid_quantity",
                message=f"Quantity is not numeric: {cleaned}",
                field="quantity",
            )
        )
        return None, issues

    if parsed != parsed.to_integral_value():
        issues.append(
            DataIssue(
                code="non_integral_quantity",
                message=f"Quantity is not an integer: {cleaned}",
                field="quantity",
            )
        )
        return None, issues

    if "." in cleaned:
        issues.append(
            DataIssue(
                code="decimal_quantity_format",
                message=f"Quantity uses decimal formatting: {cleaned}",
                field="quantity",
            )
        )

    quantity = int(parsed)
    if quantity < 0:
        issues.append(
            DataIssue(
                code="negative_quantity",
                message=f"Quantity is negative: {quantity}",
                field="quantity",
            )
        )
    return quantity, issues


def parse_inventory_date(value: str | None) -> tuple[date | None, list[DataIssue]]:
    """Parse inventory date, accepting ISO and known legacy MM/DD/YYYY format."""

    cleaned, issues = normalize_text(value, field="counted_on")
    if cleaned is None:
        return None, issues

    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            if fmt != "%Y-%m-%d":
                # Legacy format is accepted for resilience but still flagged.
                issues.append(
                    DataIssue(
                        code="non_iso_date_format",
                        message=f"Date is not ISO-8601 format: {cleaned}",
                        field="counted_on",
                    )
                )
            return parsed, issues
        except ValueError:
            continue

    issues.append(
        DataIssue(
            code="invalid_date",
            message=f"Unable to parse date: {cleaned}",
            field="counted_on",
        )
    )
    return None, issues
