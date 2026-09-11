"""Calendar summaries and standard-period returns."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from src.history.config import Granularity, ValuationStatus
from src.history.periods import performance_periods, summarise

from tests.history.conftest import row


def _year(values, contributions="0", withdrawals="0"):
    """One row per month-end through 2024, with a running index."""
    rows = []
    for n, level in enumerate(values):
        when = date(2024, 1, 1) + timedelta(days=n)
        rows.append(row(when, value=level, index=level,
                        contributions=contributions, withdrawals=withdrawals))
    return rows


def test_summary_deltas_come_from_the_daily_series():
    rows = [row(date(2024, 1, 31), value=100, contributions="100", income="5"),
            row(date(2024, 2, 29), value=150, contributions="130", income="8")]
    summaries = summarise(rows, Granularity.MONTHLY, [])
    february = next(s for s in summaries if s.period_start.month == 2)
    assert february.contributions == D("30")
    assert february.income == D("3")


def test_a_contribution_is_not_investment_gain():
    """Value rises by exactly the contribution: the gain must be zero."""
    rows = [row(date(2024, 1, 31), value=100, contributions="100"),
            row(date(2024, 2, 29), value=150, contributions="150")]
    february = next(s for s in summarise(rows, Granularity.MONTHLY, [])
                    if s.period_start.month == 2)
    assert february.investment_gain == D("0")


def test_a_withdrawal_is_not_an_investment_loss():
    rows = [row(date(2024, 1, 31), value=100, withdrawals="0"),
            row(date(2024, 2, 29), value=60, withdrawals="-40")]
    february = next(s for s in summarise(rows, Granularity.MONTHLY, [])
                    if s.period_start.month == 2)
    assert february.investment_gain == D("0")


def test_periods_bucket_by_calendar_not_by_row_count():
    rows = [row(date(2024, 3, 31), value=100), row(date(2024, 4, 1), value=110)]
    quarters = summarise(rows, Granularity.QUARTERLY, [])
    assert [q.period_start for q in quarters] == [date(2024, 1, 1), date(2024, 4, 1)]


def test_yearly_and_monthly_agree_at_the_year_end():
    rows = _year([100 + n for n in range(90)])
    monthly = summarise(rows, Granularity.MONTHLY, [])
    yearly = summarise(rows, Granularity.YEARLY, [])
    assert yearly[-1].closing_value == monthly[-1].closing_value


def test_a_window_shorter_than_the_gap_between_valuations_is_refused():
    """A quarter of movement must never be reported as a one-day return."""
    rows = [row(date(2024, 3, 31), value=100, index=100),
            *[row(date(2024, 3, 31) + timedelta(days=n), value=100, index=100,
                  index_as_at=date(2024, 3, 31)) for n in range(1, 91)],
            row(date(2024, 6, 30), value=125, index=125)]
    periods = {p.label: p for p in performance_periods(rows, [])}
    assert periods["1D"].status is ValuationStatus.UNAVAILABLE
    assert periods["1D"].twrr is None
    assert "no market movement" in periods["1D"].note or "window" in periods["1D"].note


def test_a_period_that_predates_the_portfolio_is_refused():
    rows = [row(date(2024, 6, 29), value=100, index=100),
            row(date(2024, 6, 30), value=110, index=110)]
    periods = {p.label: p for p in performance_periods(rows, [])}
    assert periods["5Y"].status is ValuationStatus.UNAVAILABLE
    assert "before the portfolio existed" in periods["5Y"].note


def test_inception_measures_from_the_first_valuable_date():
    rows = [row(date(2024, 1, 1), value=None),
            row(date(2024, 1, 2), value=100, index=100),
            row(date(2024, 6, 30), value=150, index=150)]
    inception = next(p for p in performance_periods(rows, [])
                     if p.label == "INCEPTION")
    assert inception.twrr == D("0.5")
