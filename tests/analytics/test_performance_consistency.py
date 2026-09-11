"""GET /api/portfolio/performance (overview_for_range) and the matching entry
of GET /api/portfolio/performance/periods (standard_periods ->
performance_periods) must report consistent figures for an identical
[start, end] window.

They historically disagreed: overview_for_range() took the daily row *strictly*
before ``start`` as its opening anchor with no fallback, so whenever the day
before the window was an unpriced gap -- which is routine, because carry-forward
from the previous quarter's valuation expires before the next real valuation
lands -- it returned a null opening and a TWRR measured from a stale
carried-forward index, while performance_periods() anchored to the nearest real
valuation and produced full figures.
"""

from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from src.analytics.performance import overview_for_range, standard_periods
from src.database.repository import Repository
from src.history.config import Granularity
from src.history.service import HistoryService

REAL_DB = Path(__file__).resolve().parents[2] / "data/processed/portfolio.db"

_EXACT_FIELDS = ("total_return", "capital_return", "income_return", "twrr", "xirr")


def _assert_consistent(overview, period):
    assert overview.opening_value is not None
    assert overview.closing_value is not None
    for field in _EXACT_FIELDS:
        ov, pv = getattr(overview, field), getattr(period, field)
        assert (ov is None) == (pv is None), f"{field}: {ov!r} vs {pv!r}"
        if ov is not None:
            assert ov == pytest.approx(pv, abs=D("1e-12")), (
                f"{field}: overview={ov} period={pv}")


@pytest.mark.skipif(not REAL_DB.exists(),
                    reason="real portfolio database not present in this checkout")
def test_range_and_period_endpoints_agree_on_the_real_portfolio():
    repo = Repository(REAL_DB)
    try:
        history = HistoryService(repo)
        periods = standard_periods(history)
        # Only the windows performance_periods reports as an exact measurement
        # (start/end land on real valuations) are expected to reconcile to the
        # last decimal; an ESTIMATED entry measured over a shifted span is a
        # different window by construction.
        exact = [p for p in periods
                 if p.start_date is not None and p.end_date is not None
                 and p.note is None and p.total_return is not None]
        if not exact:
            # An opportunistic bonus check against whatever real checkout
            # happens to be present -- not the regression's primary guard
            # (the synthetic fixture below reproduces the actual bug
            # pattern and always runs). The real database's transaction
            # coverage can legitimately extend a little past its last
            # actual valuation (e.g. a structured-source event dated after
            # the newest statement -- see Step 9B Stage 5), which makes
            # every "as of latest data" standard period an ESTIMATED
            # measurement rather than an exact one. That is not a bug.
            pytest.skip("no exactly-measured standard period in this checkout's "
                       "current data (transaction coverage extends past the "
                       "last valuation) -- the synthetic regression test above covers the bug pattern")
        for period in exact:
            overview = overview_for_range(history, period.start_date, period.end_date)
            _assert_consistent(overview, period)
    finally:
        repo.close()


# --- synthetic fixture reproducing the pre-valuation gap --------------------

_VALUATIONS = {
    date(2023, 3, 31): (D("40000"), D("100")),
    date(2023, 6, 30): (D("42000"), D("105")),
    date(2023, 9, 30): (D("43000"), D("107")),
    date(2023, 12, 31): (D("45000"), D("112")),
    date(2024, 3, 31): (D("47000"), D("118")),
    date(2024, 6, 30): (D("50000"), D("125")),
}
_GAP = {date(2023, 6, 26), date(2023, 6, 27), date(2023, 6, 28), date(2023, 6, 29)}
_CONTRIBUTION_DAY = date(2023, 11, 15)
_CONTRIBUTION = D("1000")


def _daily_rows():
    start, end = date(2023, 3, 31), date(2024, 6, 30)
    anchor_date = start
    anchor_value, anchor_index = _VALUATIONS[start]
    cumulative_income = D("0")
    cumulative_contributions = D("0")
    rows = []
    day = start
    while day <= end:
        cumulative_income += D("2")
        if day == _CONTRIBUTION_DAY:
            cumulative_contributions += _CONTRIBUTION
        if day in _VALUATIONS:
            anchor_value, anchor_index = _VALUATIONS[day]
            anchor_date = day
            value, status = anchor_value, "actual"
        elif day in _GAP:
            value, status = None, "unavailable"
        else:
            value, status = anchor_value, "estimated"
        rows.append({
            "date": day.isoformat(),
            "total_value": None if value is None else str(value),
            "securities_value": None if value is None else str(value),
            "cash": "0", "cost_basis": "0",
            "invested_capital": str(cumulative_contributions),
            "realised_gain": "0", "unrealised_gain": "0",
            "income": str(cumulative_income), "fees": "0",
            "cumulative_contributions": str(cumulative_contributions),
            "cumulative_withdrawals": "0",
            "high_water_mark": str(anchor_value),
            "drawdown_value": "0", "drawdown_pct": None,
            "return_index": str(anchor_index),
            "index_as_at": anchor_date.isoformat(),
            "return_high_water": None, "return_drawdown_pct": None,
            "valuation_status": status,
            "valuation_source": "VANGUARD" if status == "actual"
            else "VANGUARD_SECURITY_PRICE",
            "price_as_at": anchor_date.isoformat(),
            "source_count": 0,
        })
        day += timedelta(days=1)
    return rows


class _FakeHistory:
    def __init__(self, rows):
        self._rows = rows

    def portfolio_history(self):
        return self._rows

    def contribution_history(self, granularity=Granularity.DAILY):
        return [{
            "period_end": r["date"],
            "contributions": (str(_CONTRIBUTION)
                              if r["date"] == _CONTRIBUTION_DAY.isoformat()
                              else "0"),
            "withdrawals": "0",
        } for r in self._rows]


def test_gap_before_a_real_valuation_does_not_null_the_overview():
    history = _FakeHistory(_daily_rows())

    # 2023-06-25..29 precede the 2023-06-30 valuation and are unpriced gaps.
    rows_by_date = {r["date"]: r for r in history.portfolio_history()}
    assert rows_by_date["2023-06-29"]["total_value"] is None
    assert rows_by_date["2023-06-30"]["valuation_status"] == "actual"

    as_at = date(2024, 6, 30)
    period = {p.label: p for p in standard_periods(history, as_at)}["1Y"]
    assert period.start_date == date(2023, 6, 30)
    assert period.total_return is not None

    overview = overview_for_range(history, period.start_date, period.end_date)
    _assert_consistent(overview, period)
    assert overview.opening_value == D("42000")


def test_overview_for_range_before_the_fix_would_have_returned_nulls():
    """Documents the exact failure mode: the strictly-preceding row is a gap."""
    history = _FakeHistory(_daily_rows())
    overview = overview_for_range(history, date(2023, 6, 30), date(2024, 6, 30))
    # Anchored to the 2023-06-30 valuation, not the 2023-06-29 gap.
    assert overview.opening_value == D("42000")
    assert overview.twrr == D("125") / D("105") - D("1")
