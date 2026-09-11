"""The daily series, and its honesty about what it knows."""

from datetime import date
from decimal import Decimal as D

import pytest

from src.history.config import ValuationStatus
from src.history.generator import HistoryGenerator


@pytest.fixture
def rows(built):
    repo, _ = built
    return {r.date: r for r in HistoryGenerator(repo).generate()}


def test_state_on_the_statement_date_matches_what_was_reported(rows):
    """1,500 of holdings + 390 cash; the reported 1,910 includes 20 accrued."""
    row = rows[date(2024, 9, 30)]
    assert row.total_value == D("1890.00")
    assert row.cash == D("390.00")
    assert row.securities_value == D("1500.00")


def test_holdings_change_after_a_purchase(rows):
    """Nothing held before the trade date, 10 units after, 15 after the second."""
    assert rows[date(2024, 7, 25)].holdings == []
    assert rows[date(2024, 7, 26)].holdings[0].units == D("10.00")
    assert rows[date(2024, 9, 28)].holdings[0].units == D("15.00")


def test_contributions_are_tracked_apart_from_value(rows):
    row = rows[date(2024, 9, 30)]
    assert row.cumulative_contributions == D("500.00")
    assert row.cumulative_withdrawals == D("-200.00")
    assert row.invested_capital == D("300.00")


def test_income_is_counted_once(rows):
    """The distribution appears in income on its payment date and never again."""
    before = rows[date(2024, 7, 18)].income
    after = rows[date(2024, 7, 19)].income
    assert after - before == D("20.00")
    assert rows[date(2024, 9, 30)].income == after


def test_days_without_a_price_are_gaps_not_zeros(rows):
    """A partial sum would understate the portfolio while looking real."""
    unpriced = [r for r in rows.values()
                if r.valuation_status is ValuationStatus.UNAVAILABLE]
    assert unpriced, "expected some days before the first price"
    assert all(r.total_value is None for r in unpriced)
    assert all(r.securities_value is None for r in unpriced)
    # Cash and flows come from the ledger and stay exact regardless.
    assert all(r.cash is not None for r in unpriced)


def test_estimated_days_say_which_price_they_used(rows):
    """Traceability: an estimated value names the date its price came from."""
    estimated = [r for r in rows.values()
                 if r.valuation_status is ValuationStatus.ESTIMATED]
    for row in estimated:
        assert row.price_as_at is not None
        assert row.price_as_at < row.date


def test_prices_are_never_taken_from_the_future(rows):
    for row in rows.values():
        if row.price_as_at:
            assert row.price_as_at <= row.date


def test_allocation_sums_to_the_portfolio(rows):
    row = rows[date(2024, 9, 30)]
    allocated = sum(h.market_value for h in row.holdings)
    assert allocated + row.cash == row.total_value


def test_asset_class_comes_from_configuration_not_the_engine(rows):
    row = rows[date(2024, 9, 30)]
    # TST is not in the ticker map and has no type fallback -- genuinely
    # unclassified, not positively identified as "other" (hardening sec 6).
    assert row.holdings[0].asset_class.value == "unknown"
