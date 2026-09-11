"""Accounting invariants.

Errors here propagate into every later phase, so these are asserted over
generated event sequences rather than a single hand-built case.
"""

import random
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from src.engine.cash import CashEngine
from src.engine.ledger import CASH_TYPES, Ledger
from src.engine.state import StateEngine
from src.models import TxnType as T

from tests.conftest import ev, StubPrices

START = date(2020, 1, 1)


def _random_ledger(seed: int, days: int = 400):
    """A plausible sequence: deposits, buys, occasional sells and dividends."""
    rng = random.Random(seed)
    events, held, cash = [], D("0"), D("0")
    for offset in range(0, days, 20):
        when = START + timedelta(days=offset)
        if rng.random() < 0.4 or cash < D("1000"):
            amount = D(rng.randrange(1000, 5000))
            events.append(ev(when, T.DEPOSIT, net=amount, settle=when,
                             eid=f"dep{offset}"))
            events.append(ev(when, T.TRANSFER, net=-amount, settle=when,
                             eid=f"tr{offset}"))
            units = amount / D("100")
            events.append(ev(when, T.BUY, code="AAA", units=units, price=100,
                             net=amount, eid=f"buy{offset}"))
            held += units
        elif held > D("5") and rng.random() < 0.5:
            units = (held / D("2")).quantize(D("0.01"))
            proceeds = units * D("110")
            events.append(ev(when, T.SELL, code="AAA", units=-units, price=110,
                             net=-proceeds, eid=f"sell{offset}"))
            events.append(ev(when, T.TRANSFER, net=proceeds, settle=when,
                             eid=f"trs{offset}"))
            held -= units
        else:
            events.append(ev(when, T.DIVIDEND, code="AAA", net=D("25"),
                             settle=when, eid=f"div{offset}"))
        cash = sum((e.net_amount or D("0") for e in events
                    if e.type in CASH_TYPES), D("0"))
    return Ledger(events)


PRICES = StubPrices({"AAA": {START: D("100"),
                            START + timedelta(days=400): D("110")}})


@pytest.mark.parametrize("seed", range(8))
def test_units_never_go_negative(seed):
    ledger = _random_ledger(seed)
    engine = StateEngine(PRICES)
    for when in ledger.event_dates():
        for holding in engine.state_at(ledger, when).securities:
            assert holding.units >= 0, f"{holding.code} negative on {when}"


@pytest.mark.parametrize("seed", range(8))
def test_portfolio_value_equals_securities_plus_cash(seed):
    ledger = _random_ledger(seed)
    engine = StateEngine(PRICES)
    for when in ledger.event_dates():
        state = engine.state_at(ledger, when)
        assert state.total_value == state.securities_value + state.cash


@pytest.mark.parametrize("seed", range(8))
def test_opening_plus_transactions_equals_closing(seed):
    """Cash must only ever change by the cash events between two dates."""
    ledger = _random_ledger(seed)
    cash = CashEngine()
    dates = ledger.event_dates()
    for previous, current in zip(dates, dates[1:]):
        opening = cash.balance_at(ledger, previous)
        closing = cash.balance_at(ledger, current)
        moved = sum((e.net_amount or D("0") for e in ledger
                     if e.type in CASH_TYPES and previous < e.cash_date <= current),
                    D("0"))
        assert closing - opening == moved


@pytest.mark.parametrize("seed", range(8))
def test_cost_basis_never_negative(seed):
    ledger = _random_ledger(seed)
    engine = StateEngine(PRICES)
    for when in ledger.event_dates():
        for holding in engine.state_at(ledger, when).securities:
            assert holding.cost_basis >= 0


def test_brokerage_is_not_deducted_twice():
    """The cash leg carries gross proceeds with brokerage as its own fee row;
    the trade row is already net. Cash must reflect exactly one deduction."""
    when = date(2024, 5, 1)
    settled = date(2024, 5, 5)
    ledger = Ledger([
        ev(when, T.SELL, code="AAA", units=-22, price=55.175, net=-1204.85, fees=9),
        ev(when, T.TRANSFER, net=1213.85, settle=settled),
        ev(settled, T.FEE, net=-9, settle=settled),
    ])
    assert CashEngine().balance_at(ledger, settled) == D("1204.85")
