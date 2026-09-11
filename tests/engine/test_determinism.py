"""The engine must produce identical output from identical input."""

import random
from datetime import date
from decimal import Decimal as D

from src.engine.ledger import Ledger
from src.engine.state import StateEngine
from src.models import TxnType as T

from tests.conftest import ev, StubPrices

JAN, JUN = date(2024, 1, 1), date(2024, 6, 1)

EVENTS = [
    ev(JAN, T.DEPOSIT, net=10000, settle=JAN, eid="a"),
    ev(JAN, T.TRANSFER, net=-10000, settle=JAN, eid="b"),
    ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000, eid="c"),
    ev(JUN, T.DIVIDEND, code="AAA", net=250, settle=JUN, eid="d"),
    ev(JUN, T.SELL, code="AAA", units=-40, price=120, net=-4800, eid="e"),
]
PRICES = StubPrices({"AAA": {JAN: D("100"), JUN: D("120")}})


def _fingerprint(state):
    return (state.total_value, state.cash, state.realised_gain,
            tuple((s.code, s.units, s.cost_basis, s.market_value)
                  for s in state.securities))


def test_same_input_gives_same_output():
    engine = StateEngine(PRICES)
    first = engine.state_at(Ledger(EVENTS), JUN)
    second = engine.state_at(Ledger(EVENTS), JUN)
    assert _fingerprint(first) == _fingerprint(second)


def test_result_does_not_depend_on_input_ordering():
    """Database row order must not change a single figure."""
    engine = StateEngine(PRICES)
    expected = _fingerprint(engine.state_at(Ledger(EVENTS), JUN))
    for seed in range(10):
        shuffled = EVENTS[:]
        random.Random(seed).shuffle(shuffled)
        assert _fingerprint(engine.state_at(Ledger(shuffled), JUN)) == expected


def test_ledger_ordering_is_total_and_stable():
    keys = [e.sort_key() for e in Ledger(EVENTS)]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)


def test_history_is_never_rewritten_by_an_adjustment():
    original = Ledger(EVENTS)
    correction = ev(JUN, T.FEE, net=-15, settle=JUN, eid="adj")
    adjusted = original.with_adjustments([correction])

    assert len(original) == len(EVENTS)          # untouched
    assert len(adjusted) == len(EVENTS) + 1
    assert any(e.is_adjustment for e in adjusted)
    assert not any(e.is_adjustment for e in original)
