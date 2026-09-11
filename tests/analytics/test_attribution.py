"""Growth decomposition and attribution must reconcile back to the portfolio
-- the spec's own repeated requirement (sec 41, 42), and the source of three
real bugs found while building this module (double-counted brokerage in two
places, and a fee reversal treated as a second charge).

Uses a small hand-built ledger with a properly paired BUY/TRANSFER, rather
than the shared statement fixture: that fixture (built for Phase 1's PDF
parsing edge cases) has no TRANSFER row for either of its trades, so its
holdings and cash are not economically consistent with each other -- real
statements always pair the two (confirmed across all 76 trades in the real
portfolio). The real-history test at the bottom is the strongest evidence,
run against the actual six years of paired trades.
"""

from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from src.analytics.attribution import (growth_decomposition, reconcile_attribution,
                                       reconcile_growth, security_attribution)
from src.database.repository import Repository
from src.engine.ledger import Ledger
from src.engine.prices import PriceQuality, Quote
from src.engine.state import StateEngine
from src.models import TxnType as T

from tests.conftest import ev

TOLERANCE = D("0.05")
JAN, FEB = date(2024, 1, 1), date(2024, 2, 1)


class _Stub:
    """A price source with one flat quote everywhere -- enough to value a
    single security without needing a full statement fixture."""
    def __init__(self, price=D("110")):
        self.price = price

    def quote(self, sid, on):
        return Quote(self.price, PriceQuality.QUOTED, on)


def _paired_ledger():
    """Deposit, a fully-paired buy (BUY + TRANSFER + FEE, like a real
    statement), a dividend, and a withdrawal -- internally consistent."""
    return Ledger([
        ev(JAN, T.DEPOSIT, net=2000, eid="dep"),
        ev(JAN, T.BUY, code="AAA", units=10, price=100, net=1009, fees=9, eid="buy"),
        ev(JAN, T.TRANSFER, net=-1000, eid="tr"),
        ev(JAN, T.FEE, net=-9, eid="fee"),
        ev(date(2024, 1, 15), T.DISTRIBUTION, code="AAA", net=20, eid="div"),
        ev(date(2024, 1, 20), T.WITHDRAWAL, net=-200, eid="wd"),
    ])


def test_growth_reconciles_on_a_properly_paired_ledger():
    ledger = _paired_ledger()
    engine = StateEngine(_Stub())
    rec = reconcile_growth(engine, ledger, JAN, FEB)
    assert rec.status == "PASS", rec


def test_attribution_reconciles_on_a_properly_paired_ledger():
    ledger = _paired_ledger()
    engine = StateEngine(_Stub())
    rec = reconcile_attribution(engine, ledger, JAN, FEB)
    assert rec.status == "PASS", rec


def test_brokerage_is_not_double_counted():
    """Regression: brokerage is capitalised into cost basis by Phase 2, so
    growth_decomposition's separate fee line must exclude it, or a trade's
    brokerage is subtracted twice."""
    # Real statements record brokerage twice: once inside the BUY row itself
    # (its .fees field, used for cost basis) and once as its own FEE-type
    # cash-ledger transaction (the actual cash deduction). Both are needed
    # here for the test to reflect that shape.
    events = [
        ev(JAN, T.BUY, code="AAA", units=10, price=100, net=1009, fees=9),
        ev(JAN, T.FEE, net=-9, eid="brokerage_fee"),
    ]
    ledger = Ledger(events)
    engine = StateEngine(_Stub())
    # ledger.between() excludes its own start date, so the window must open
    # the day before the event, not on it.
    decomposition = growth_decomposition(engine, ledger, date(2023, 12, 31), date(2024, 1, 2))
    # Cost basis already includes the $9 brokerage; the fee line must not
    # subtract it again.
    assert decomposition.trade_costs == D("9")
    assert decomposition.fees == D("0")   # no account-level fee here


def test_fee_reversal_nets_against_the_original_charge():
    """Regression: abs() applied per-transaction turns a credit (a reversed
    fee) into a second charge instead of cancelling the first."""
    events = [
        ev(JAN, T.FEE, net=-10, eid="charge"),
        ev(date(2024, 1, 2), T.FEE, net=10, eid="reversal"),
    ]
    ledger = Ledger(events)
    engine = StateEngine(_Stub())
    decomposition = growth_decomposition(engine, ledger, date(2023, 12, 31), date(2024, 1, 3))
    assert decomposition.fees == D("0")   # fully reversed, not $20


def test_security_attribution_distinguishes_return_from_contribution():
    """A security's own return and its share of the portfolio's return
    answer different questions and must not be reported as the same number.
    SMALL is a tenth the size of BIG but returns 100% against BIG's 1% --
    small enough a position that its weight is far below BIG's, but its own
    return is far above it. Neither figure may be confused with the other,
    and the weight ordering must track position size regardless of return."""
    ledger = Ledger([
        ev(JAN, T.DEPOSIT, net=11000, eid="dep"),
        ev(JAN, T.BUY, code="BIG", units=100, price=100, net=10000, eid="buy_big"),
        ev(JAN, T.TRANSFER, net=-10000, eid="tr_big"),
        ev(JAN, T.BUY, code="SMALL", units=10, price=100, net=1000, eid="buy_small"),
        ev(JAN, T.TRANSFER, net=-1000, eid="tr_small"),
    ])

    class TwoPriceStub:
        """$100 at purchase, then BIG barely moves while SMALL doubles --
        needs to be date-aware, or opening and closing (both computed via
        state_at, which is inclusive of its own date) would see the same
        price and show no return at all."""
        def quote(self, sid, on):
            if on <= JAN:
                return Quote(D("100"), PriceQuality.QUOTED, on)
            return Quote(D("101") if sid == "BIG" else D("200"), PriceQuality.QUOTED, on)

    engine = StateEngine(TwoPriceStub())
    rows = {r.code: r for r in security_attribution(engine, ledger, JAN, FEB)}

    # Return ordering is the opposite of weight ordering -- the two figures
    # measure different things and neither may be reported as the other.
    assert rows["SMALL"].total_return > rows["BIG"].total_return
    assert rows["SMALL"].portfolio_weight < rows["BIG"].portfolio_weight
    assert rows["SMALL"].total_return != rows["SMALL"].portfolio_contribution
    assert rows["BIG"].total_return != rows["BIG"].portfolio_contribution

    # Contributions still sum to the portfolio's own return (Phase 2's
    # profit-share guarantee, sec 42), regardless of how they're split.
    from src.analytics.attribution import portfolio_attribution
    attribution = portfolio_attribution(engine, ledger, JAN, FEB)
    assert attribution.total_pct == pytest.approx(
        rows["SMALL"].portfolio_contribution + rows["BIG"].portfolio_contribution,
        abs=D("0.0001"))


def test_reconciliation_across_the_full_real_history():
    """The strongest evidence: every calendar year across this portfolio's
    real six-year history reconciles exactly, using its real (fully paired)
    trades. Skipped when the real database is not present (gitignored, like
    the source PDFs)."""
    db_path = Path(__file__).resolve().parents[2] / "data/processed/portfolio.db"
    if not db_path.exists():
        pytest.skip("real portfolio database not present in this checkout")

    from src.engine.cash import opening_cash_for
    from src.engine.prices import SnapshotPriceSource

    repo = Repository(db_path)
    try:
        ledger = Ledger.from_repository(repo)
        engine = StateEngine(SnapshotPriceSource.from_repository(repo),
                             opening_cash=opening_cash_for(repo))
        failures = []
        for year in range(2020, 2027):
            start, end = date(year, 1, 1), date(year, 12, 31)
            growth = reconcile_growth(engine, ledger, start, end)
            attribution = reconcile_attribution(engine, ledger, start, end)
            if growth.status != "PASS":
                failures.append(("growth", year, growth.difference))
            if attribution.status != "PASS":
                failures.append(("attribution", year, attribution.difference))
        assert failures == []
    finally:
        repo.close()
