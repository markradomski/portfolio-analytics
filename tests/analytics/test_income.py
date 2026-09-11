"""Income yield methodology must state its own denominator explicitly, and
income must never be counted twice (sec 10-12, 43)."""

from datetime import date
from decimal import Decimal as D

from src.analytics.income import (forward_income_yield, income_by,
                                  security_income_yield, trailing_income_yield)
from src.analytics.result import DataQuality
from src.history.config import Granularity


def test_income_appears_exactly_once_across_the_year(history):
    """The one distribution in the synthetic statement must appear once in
    the yearly total, not duplicated across a monthly/yearly join."""
    yearly = income_by(history, Granularity.YEARLY)
    monthly = income_by(history, Granularity.MONTHLY)
    assert sum(D(r["gross_income"]) for r in yearly) == D("20.00")
    assert sum(D(r["gross_income"]) for r in monthly) == D("20.00")


def test_trailing_yield_states_its_denominator(history):
    result = trailing_income_yield(history, as_at=date(2024, 9, 30))
    assert "average_portfolio_value" in result.methodology
    assert "average_portfolio_value" not in result.methodology.replace(
        "average_portfolio_value", "", 1)   # appears exactly once, not typo'd twice


def test_forward_yield_is_honestly_unavailable(history):
    """No distribution forecast exists in Vanguard statement data -- must
    never be extrapolated from the trailing figure and presented as a
    genuine forward-looking number."""
    result = forward_income_yield(history)
    assert result.data_quality is DataQuality.UNAVAILABLE
    assert result.value is None


def test_security_yield_uses_the_securitys_own_average_value(history):
    result = security_income_yield(history, "TST", as_at=date(2024, 9, 30))
    assert "average_holding_value" in result.methodology


def test_yield_is_never_income_over_current_value_alone(history):
    """The methodology string must name 'average', distinguishing it from
    the (different, easily confused) income/current_value convention."""
    result = trailing_income_yield(history, as_at=date(2024, 9, 30))
    assert "average" in result.methodology
