from datetime import date
from decimal import Decimal

import pytest

from src.normalisation.values import parse_date, parse_decimal, quarter_of


@pytest.mark.parametrize("raw,expected", [
    ("$1,234.56", Decimal("1234.56")),
    ("1,234.567", Decimal("1234.567")),
    ("-$3,400.00", Decimal("-3400.00")),
    ("0.00", Decimal("0.00")),
    ("  12.30  ", Decimal("12.30")),
])
def test_parses_money(raw, expected):
    assert parse_decimal(raw) == expected


@pytest.mark.parametrize("raw", ["", "  ", "-", "n/a", "Not yet settled", None])
def test_rejects_non_numbers_rather_than_guessing(raw):
    assert parse_decimal(raw) is None


def test_decimal_not_float():
    """Values are summed and reconciled to the cent, so they must be exact."""
    assert parse_decimal("0.10") + parse_decimal("0.20") == Decimal("0.30")


@pytest.mark.parametrize("raw,expected", [
    ("12 Sep 2023", date(2023, 9, 12)),
    ("30 June 2026", date(2026, 6, 30)),
    ("01-May-2026", date(2026, 5, 1)),
    ("28-Jun-24", date(2024, 6, 28)),
    ("2024-06-28", date(2024, 6, 28)),
])
def test_parses_every_date_format_seen(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["Not yet settled", "", "-", "gibberish", None])
def test_unparseable_dates_return_none(raw):
    assert parse_date(raw) is None


def test_quarter_boundaries():
    assert quarter_of(date(2024, 1, 1)) == (2024, 1)
    assert quarter_of(date(2024, 3, 31)) == (2024, 1)
    assert quarter_of(date(2024, 4, 1)) == (2024, 2)
    assert quarter_of(date(2024, 12, 31)) == (2024, 4)
