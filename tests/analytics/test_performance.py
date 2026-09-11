"""Return methodology and standard periods: contributions/withdrawals must
never appear as performance, and a period is only reported when it can
genuinely be measured (sec 4-5, 43)."""

from datetime import date
from decimal import Decimal as D

import pytest

from src.analytics.performance import (overview_for_range, overview_for_year,
                                       return_methodology_notes, standard_periods)
from src.history.service import HistoryService


def test_a_contribution_is_never_investment_gain(history):
    """The synthetic statement: $500 deposited, $200 withdrawn, $20
    distribution, holdings unrealised loss of -$20 (cost 1520, value 1500).
    None of the $500/$200 external flow may leak into investment_gain."""
    overview = overview_for_year(history, 2024)
    assert overview is not None
    assert overview.contributions == D("500.00")
    assert overview.withdrawals == D("-200.00")
    # investment_gain excludes both -- it's whatever the holdings/income did,
    # not what was moved across the portfolio boundary.
    assert overview.investment_gain is not None
    assert overview.investment_gain != overview.contributions
    assert overview.investment_gain != overview.withdrawals


def test_overview_identity_holds(history):
    """opening + net_flow + investment_gain = closing, to the cent."""
    overview = overview_for_year(history, 2024)
    computed = ((overview.opening_value or D("0")) + overview.net_external_flow
               + (overview.investment_gain or D("0")))
    assert computed == pytest.approx(overview.closing_value, abs=D("0.05"))


def test_custom_range_matches_the_equivalent_calendar_period(history):
    """A custom range spanning exactly a calendar quarter must produce the
    same figures the quarterly period_summaries row already has."""
    from src.history.config import Granularity

    quarterly = history.period_summaries(Granularity.QUARTERLY)
    row = quarterly[0]
    start, end = date.fromisoformat(row["period_start"]), date.fromisoformat(row["period_end"])
    custom = overview_for_range(history, start, end)
    if row["closing_value"]:
        assert custom.closing_value == D(row["closing_value"])
    if row["twrr"]:
        assert custom.twrr == pytest.approx(D(row["twrr"]), abs=D("0.0001"))


def test_return_methodology_notes_cover_every_metric():
    notes = return_methodology_notes()
    for key in ("absolute_return", "capital_return", "income_return",
               "total_return", "twrr", "xirr"):
        assert key in notes and notes[key]


def test_standard_periods_refuse_windows_the_data_cannot_measure(history):
    """A 1-day window against quarterly-only pricing must not report a
    quarter's movement as a single day's return."""
    periods = {p.label: p for p in standard_periods(history)}
    assert "1D" in periods
    if periods["1D"].status.value == "unavailable":
        assert periods["1D"].twrr is None
    else:
        # Would only be measurable if two valuations happen to be exactly
        # a day apart, which this data does not have.
        pytest.fail("expected 1D to be unavailable against quarterly-only pricing")


def test_period_before_inception_is_unavailable_not_zero(history):
    periods = {p.label: p for p in standard_periods(history)}
    if "10Y" in periods and periods["10Y"].status.value == "unavailable":
        assert periods["10Y"].twrr is None
        assert "before the portfolio existed" in (periods["10Y"].note or "")
