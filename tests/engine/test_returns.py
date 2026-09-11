from datetime import date
from decimal import Decimal as D

import pytest

from src.engine.returns import (annualised, modified_dietz,
                                time_weighted_return, xirr)

START, END = date(2024, 1, 1), date(2024, 12, 31)


def test_return_with_no_flows_is_the_simple_gain():
    r = modified_dietz(D("100"), D("120"), [], START, END)
    assert r.ret == D("0.2")


def test_a_flow_is_weighted_by_time_invested():
    """100 at the start, 100 added halfway, ending 220: the added capital only
    worked for half the period, so the denominator is 150, not 200."""
    mid = START + (END - START) / 2
    r = modified_dietz(D("100"), D("220"), [(mid, D("100"))], START, END)
    assert r.gain == D("20")
    assert r.weighted_flow == pytest.approx(D("50"), abs=D("0.5"))
    assert r.ret == pytest.approx(D("0.1333"), abs=D("0.001"))


def test_a_contribution_is_never_counted_as_return():
    """Deposit the whole increase: the return must be zero, not +100%."""
    r = modified_dietz(D("100"), D("200"), [(START, D("100"))], START, END)
    assert r.gain == D("0")
    assert r.ret == D("0")


def test_period_with_no_capital_is_unmeasurable_not_zero():
    r = modified_dietz(D("0"), D("0"), [], START, END)
    assert r.ret is None


def test_returns_chain_multiplicatively():
    periods = [modified_dietz(D("100"), D("110"), [], START, END),
               modified_dietz(D("110"), D("121"), [], START, END)]
    assert time_weighted_return(periods) == pytest.approx(D("0.21"), abs=D("1e-9"))


def test_unmeasurable_periods_are_skipped_not_treated_as_zero():
    periods = [modified_dietz(D("100"), D("110"), [], START, END),
               modified_dietz(D("0"), D("0"), [], START, END)]
    assert time_weighted_return(periods) == D("0.1")


def test_annualising_a_multi_year_return():
    # 21% over two years is about 10% a year.
    result = annualised(D("0.21"), date(2020, 1, 1), date(2022, 1, 1))
    assert result == pytest.approx(D("0.1"), abs=D("0.002"))


def test_xirr_on_a_single_year_holding():
    flows = [(date(2024, 1, 1), D("-1000")), (date(2024, 12, 31), D("1100"))]
    assert xirr(flows) == pytest.approx(D("0.10"), abs=D("0.001"))


def test_xirr_handles_irregular_contributions():
    flows = [(date(2020, 1, 1), D("-1000")),
             (date(2020, 7, 15), D("-500")),
             (date(2021, 3, 2), D("-250")),
             (date(2022, 1, 1), D("1980"))]
    rate = xirr(flows)
    assert rate is not None and D("0.05") < rate < D("0.15")


def test_xirr_needs_flows_in_both_directions():
    assert xirr([(date(2024, 1, 1), D("-100")), (date(2024, 6, 1), D("-100"))]) is None


def test_xirr_is_deterministic():
    flows = [(date(2020, 1, 1), D("-1000")), (date(2023, 6, 30), D("1500"))]
    assert xirr(flows) == xirr(flows)
