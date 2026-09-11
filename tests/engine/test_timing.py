"""The authoritative date/timing contract: effective_date, cash_effective_date,
event ordering, and the separation of trade timing from cash timing.
"""

from datetime import date
from decimal import Decimal as D

import pytest

from src.engine.ledger import Ledger, TYPE_ORDER
from src.models import TxnType as T

from tests.conftest import ev

JAN, FEB = date(2024, 1, 10), date(2024, 2, 13)


# -- effective_date / cash_effective_date ------------------------------------

def test_effective_date_is_trade_date_for_every_type():
    """Every event type's effective_date is its own trade_date -- for a trade
    that's literally the trade date; for everything else trade_date already
    holds the cash-ledger's own date, which is that type's economic date."""
    for kind in (T.BUY, T.SELL, T.DEPOSIT, T.WITHDRAWAL, T.DIVIDEND,
                 T.DISTRIBUTION, T.FEE, T.TAX, T.INTEREST, T.TRANSFER):
        event = ev(JAN, kind, net=100, code="AAA" if kind in (T.BUY, T.SELL) else None,
                   units=1 if kind in (T.BUY, T.SELL) else None, price=100)
        assert event.effective_date == JAN, kind


def test_cash_effective_date_is_none_for_trades():
    """A BUY/SELL has no direct cash effect in this model -- that belongs to
    its paired TRANSFER, which already carries the correct date."""
    buy = ev(JAN, T.BUY, code="AAA", units=10, price=100, net=1000, settle=FEB)
    assert buy.cash_effective_date is None


def test_cash_effective_date_ignores_settlement_date_for_non_trades():
    """settlement_date is only meaningful for BUY/SELL; a TRANSFER's own date
    is its cash_effective_date regardless of what settle= holds."""
    transfer = ev(JAN, T.TRANSFER, net=500, settle=FEB)
    assert transfer.cash_effective_date == JAN


def test_cash_date_raises_on_a_trade_rather_than_guessing():
    """Calling the cash-only accessor on a BUY/SELL is a caller error: there is
    no single cash date to return, and guessing (e.g. falling back to
    settlement_date) would silently reintroduce the wrong assumption."""
    buy = ev(JAN, T.BUY, code="AAA", units=10, price=100, net=1000, settle=FEB)
    with pytest.raises(ValueError):
        buy.cash_date


# -- ordering -----------------------------------------------------------------

def test_canonical_same_day_order():
    """Corporate actions first (a split must apply before a same-day trade
    acts on the resulting units), deposits before trades (contributed cash
    must exist before it's invested), income before fees/tax, withdrawals
    last among cash movements."""
    events = [
        ev(JAN, T.WITHDRAWAL, net=-50, eid="w"),
        ev(JAN, T.FEE, net=-5, eid="f"),
        ev(JAN, T.TAX, net=-3, eid="t"),
        ev(JAN, T.DISTRIBUTION, net=20, code="AAA", eid="di"),
        ev(JAN, T.DIVIDEND, net=10, code="BBB", eid="dv"),
        ev(JAN, T.SELL, code="AAA", units=-5, price=100, net=-500, eid="s"),
        ev(JAN, T.BUY, code="AAA", units=10, price=100, net=1000, eid="b"),
        ev(JAN, T.TRANSFER, net=-1000, eid="tr"),
        ev(JAN, T.DEPOSIT, net=2000, eid="dep"),
        ev(JAN, T.CORPORATE_ACTION, code="AAA", units=5, eid="ca"),
    ]
    ledger = Ledger(events)
    order = [e.type for e in ledger]
    assert order == [
        T.CORPORATE_ACTION, T.DEPOSIT, T.TRANSFER, T.BUY, T.SELL,
        T.DIVIDEND, T.DISTRIBUTION, T.TAX, T.FEE, T.WITHDRAWAL,
    ]


def test_type_order_covers_every_type():
    assert set(TYPE_ORDER) == set(T)
