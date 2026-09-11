"""Dedicated income + reinvestment double-counting test (hardening sec 4).

Dividend -> cash increases -> reinvestment -> units increase -> the security
later gains value. Verifies all seven points the spec lists, for both a
dividend (company) and a distribution (fund) reinvestment, using the
accounting engine directly so there is no ambiguity about which layer is
responsible for each figure.
"""

from datetime import date
from decimal import Decimal as D

import pytest

from src.engine.cash import CashEngine
from src.engine.ledger import Ledger
from src.engine.prices import PriceQuality, Quote
from src.engine.state import StateEngine
from src.models import TxnType as T

from tests.conftest import ev

JAN, FEB, MAR = date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)


class _Stub:
    """$100 up to FEB, $110 from FEB onward -- a real capital gain the
    reinvested units must correctly participate in."""
    def quote(self, sid, on):
        price = D("100") if on < FEB else D("110")
        return Quote(price, PriceQuality.QUOTED, on)


def _reinvestment_ledger(income_type: T) -> Ledger:
    return Ledger([
        ev(JAN, T.DEPOSIT, net=10000, eid="dep"),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000, eid="buy"),
        ev(JAN, T.TRANSFER, net=-10000, eid="tr"),
        # Dividend/distribution paid...
        ev(date(2024, 1, 15), income_type, code="AAA", net=500, eid="income"),
        # ...then reinvested a few days later at the (still $100) price.
        ev(date(2024, 1, 20), T.BUY, code="AAA", units=5, price=100, net=500, eid="reinvest_buy"),
        ev(date(2024, 1, 20), T.TRANSFER, net=-500, eid="reinvest_tr"),
    ])


@pytest.mark.parametrize("income_type", [T.DIVIDEND, T.DISTRIBUTION])
def test_reinvestment_does_not_double_count(income_type):
    ledger = _reinvestment_ledger(income_type)
    engine = StateEngine(_Stub())
    cash = CashEngine()

    # 1. Income is recognised exactly once.
    income_events = [e for e in ledger.of_type(income_type)]
    assert len(income_events) == 1
    assert income_events[0].net_amount == D("500")

    # 2. Dividend cash is recognised exactly once (not fabricated a second
    #    time when it's reinvested).
    flows = cash.flows(ledger, end=MAR)
    assert flows.income == D("500")

    # 3. Reinvestment is not an external contribution.
    assert flows.deposits == D("10000")   # only the original deposit
    external = cash.external_flows(ledger)
    assert external == [(JAN, D("10000"))]

    # 4. Reinvestment does not create artificial investment return: cash ends
    #    at exactly 0 (10000 deposited - 10000 bought + 500 income - 500
    #    reinvested), not inflated by counting the $500 twice.
    assert cash.balance_at(ledger, MAR) == D("0")

    # 5. The newly acquired 5 units are reflected in market value.
    state = engine.state_at(ledger, date(2024, 1, 25))
    holding = state.securities[0]
    assert holding.units == D("105")            # 100 original + 5 reinvested

    # 6. Subsequent capital gain reflects all 105 units at the new price.
    later = engine.state_at(ledger, MAR)
    later_holding = later.securities[0]
    assert later_holding.market_value == D("105") * D("110")   # 11,550
    # Cost basis: 100 units @ $100 + 5 units @ $100 = $10,500.
    assert later_holding.cost_basis == D("10500")
    assert later_holding.unrealised_gain == D("11550") - D("10500")   # $1,050

    # 7. Total portfolio growth reconciles: opening (genuinely before any
    #    event -- state_at is inclusive of its own date, so JAN itself
    #    already contains the deposit/buy) -> deposit 10,000 -> income 500
    #    (all reinvested, cash returns to 0) -> capital gain 1,050.
    before_anything = date(2023, 12, 31)
    opening = engine.state_at(ledger, before_anything).total_value
    closing = engine.state_at(ledger, MAR).total_value
    external_total = sum(a for _, a in external)
    capital_gain = later_holding.unrealised_gain
    income = flows.income
    assert opening == D("0")
    # opening + external flows + capital gain + income = closing. Income and
    # capital gain are separate additive components of total return (the
    # same decomposition growth_decomposition uses) -- the $500 income is not
    # already inside capital_gain merely because it was reinvested.
    assert opening + external_total + capital_gain + income == closing
