from __future__ import annotations

"""Unit tests for field-level normalization helpers.

These tests document the expected behavior of low-level parsing utilities used
by the CSV parser. Each case focuses on one rule so regressions are easy to
diagnose.
"""

from datetime import date

from inventory_parser.normalize import normalize_sku, normalize_text, parse_inventory_date, parse_quantity


def _issue_codes(issues: list[object]) -> set[str]:
    return {issue.code for issue in issues}


def test_normalize_text_trims_and_reports_whitespace() -> None:
    """Text values should be stripped and flagged when outer whitespace exists."""
    value, issues = normalize_text("  Widget A  ", field="name")
    assert value == "Widget A"
    assert _issue_codes(issues) == {"whitespace_trimmed"}


def test_normalize_text_empty_or_missing_values() -> None:
    """Missing and blank text should normalize to None and emit missing_value."""
    missing_value, missing_issues = normalize_text(None, field="name")
    empty_value, empty_issues = normalize_text("   ", field="name")

    assert missing_value is None
    assert _issue_codes(missing_issues) == {"missing_value"}

    assert empty_value is None
    assert _issue_codes(empty_issues) == {"missing_value"}


def test_normalize_sku_handles_case_and_hyphen_normalization() -> None:
    """SKU normalization should fix case/spacing and add missing hyphen."""
    normalized_case, case_issues = normalize_sku(" sku-008 ")
    normalized_hyphen, hyphen_issues = normalize_sku("SKU005")

    assert normalized_case == "SKU-008"
    assert _issue_codes(case_issues) == {"whitespace_trimmed", "sku_format_normalized"}

    assert normalized_hyphen == "SKU-005"
    assert _issue_codes(hyphen_issues) == {"sku_format_normalized"}


def test_normalize_sku_reports_invalid_format() -> None:
    """Unexpected SKU formats should be retained and flagged as invalid."""
    normalized, issues = normalize_sku("bad-sku")
    assert normalized == "BAD-SKU"
    assert _issue_codes(issues) == {"invalid_sku_format"}


def test_parse_quantity_accepts_integer_and_flags_decimal_formatting() -> None:
    """Decimal-rendered integers should parse to int and be format-flagged."""
    parsed, issues = parse_quantity("80.00")
    assert parsed == 80
    assert _issue_codes(issues) == {"decimal_quantity_format"}


def test_parse_quantity_rejects_non_integral_and_non_numeric_values() -> None:
    """Non-integral and non-numeric quantities should fail with clear issue codes."""
    non_integral_value, non_integral_issues = parse_quantity("12.5")
    non_numeric_value, non_numeric_issues = parse_quantity("abc")

    assert non_integral_value is None
    assert _issue_codes(non_integral_issues) == {"non_integral_quantity"}

    assert non_numeric_value is None
    assert _issue_codes(non_numeric_issues) == {"invalid_quantity"}


def test_parse_quantity_flags_negative_values() -> None:
    """Negative integers are parsed but explicitly flagged."""
    parsed, issues = parse_quantity("-5")
    assert parsed == -5
    assert _issue_codes(issues) == {"negative_quantity"}


def test_parse_inventory_date_parses_iso_and_non_iso_formats() -> None:
    """ISO dates pass cleanly; alternate accepted format is flagged."""
    iso_date, iso_issues = parse_inventory_date("2024-01-15")
    non_iso_date, non_iso_issues = parse_inventory_date("01/15/2024")

    assert iso_date == date(2024, 1, 15)
    assert _issue_codes(iso_issues) == set()

    assert non_iso_date == date(2024, 1, 15)
    assert _issue_codes(non_iso_issues) == {"non_iso_date_format"}


def test_parse_inventory_date_reports_invalid_value() -> None:
    """Unparseable dates should return None with invalid_date issue."""
    parsed, issues = parse_inventory_date("2024/15/01")
    assert parsed is None
    assert _issue_codes(issues) == {"invalid_date"}
