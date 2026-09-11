"""The accounting scenarios that define correct behaviour.

Each one isolates a way the engine could confuse money put in with money made.
"""

from datetime import date
from decimal import Decimal as D

import pytest

from src.engine.cash import CashEngine
from src.engine.ledger import Ledger
from src.engine.state import StateEngine
from src.models import TxnType as T

from tests.conftest import ev, StubPrices

JAN, FEB, JUN, DEC = (date(2024, 1, 1), date(2024, 2, 1),
                      date(2024, 6, 1), date(2024, 12, 31))


def build(events, prices):
    return Ledger(events), StateEngine(prices)


def test_simple_purchase():
    """$10,000 deposited and fully invested: no cash, no gain, no return."""
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=10000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-10000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
    ], StubPrices({"AAA": {JAN: D("100")}}))

    state = engine.state_at(ledger, JAN)
    assert state.cash == D("0")
    assert state.securities_value == D("10000")
    assert state.total_value == D("10000")
    assert state.unrealised_gain == D("0")
    assert CashEngine().flows(ledger).deposits == D("10000")


def test_market_increase_is_an_unrealised_gain():
    """$10,000 becomes $12,000: +$2,000, +20%, none of it realised."""
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=10000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-10000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
    ], StubPrices({"AAA": {JAN: D("100"), DEC: D("120")}}))

    state = engine.state_at(ledger, DEC)
    holding = state.securities[0]
    assert state.total_value == D("12000")
    assert holding.unrealised_gain == D("2000")
    assert holding.unrealised_gain_pct == D("0.2")
    assert state.realised_gain == D("0")


def test_dividend_is_income_and_is_not_double_counted():
    """A $500 dividend adds $500 of cash. It must not also inflate the holding."""
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=10000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-10000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
        ev(JUN, T.DIVIDEND, code="AAA", net=500, settle=JUN),
    ], StubPrices({"AAA": {JAN: D("100")}}))

    state = engine.state_at(ledger, DEC)
    assert state.cash == D("500")
    assert state.securities_value == D("10000")      # unchanged by the dividend
    assert state.total_value == D("10500")
    assert state.dividends == D("500")
    assert state.securities[0].cost_basis == D("10000")


def test_additional_contribution_is_not_investment_return():
    """$10,000 grows to $12,000, then $5,000 more is added. The portfolio is
    worth $17,000 but only $2,000 of that was earned."""
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=10000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-10000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
        ev(JUN, T.DEPOSIT, net=5000, settle=JUN),
    ], StubPrices({"AAA": {JAN: D("100"), JUN: D("120")}}))

    state = engine.state_at(ledger, JUN)
    flows = CashEngine().flows(ledger)
    assert state.total_value == D("17000")
    assert flows.deposits == D("15000")
    assert state.unrealised_gain == D("2000")
    # The part that was earned, as opposed to paid in.
    assert state.total_value - flows.deposits == D("2000")


def test_partial_sale():
    """100 units at $80; sell 40 at $110. 60 remain."""
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=8000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-8000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=80, net=8000),
        ev(JUN, T.SELL, code="AAA", units=-40, price=110, net=-4400),
        ev(JUN, T.TRANSFER, net=4400, settle=JUN),
    ], StubPrices({"AAA": {JAN: D("80"), JUN: D("110")}}))

    state = engine.state_at(ledger, JUN)
    holding = state.securities[0]
    assert holding.units == D("60")
    assert holding.cost_basis == D("4800")
    assert holding.realised_gain == D("1200")
    assert holding.market_value == D("6600")
    assert holding.unrealised_gain == D("1800")
    assert state.cash == D("4400")


def test_withdrawal_is_an_external_flow_not_a_loss():
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=10000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-10000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
        ev(JUN, T.SELL, code="AAA", units=-100, price=100, net=-10000),
        ev(JUN, T.TRANSFER, net=10000, settle=JUN),
        ev(DEC, T.WITHDRAWAL, net=-10000, settle=DEC),
    ], StubPrices({"AAA": {JAN: D("100"), JUN: D("100")}}))

    state = engine.state_at(ledger, DEC)
    assert state.cash == D("0")
    assert state.realised_gain == D("0")          # sold at cost: no loss
    assert CashEngine().flows(ledger).withdrawals == D("-10000")


def test_multiple_securities_with_different_outcomes():
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=20000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-20000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
        ev(FEB, T.BUY, code="BBB", units=200, price=50, net=10000),
        ev(JUN, T.DIVIDEND, code="AAA", net=300, settle=JUN),
    ], StubPrices({"AAA": {JAN: D("100"), DEC: D("130")},
                   "BBB": {FEB: D("50"), DEC: D("40")}}))

    state = engine.state_at(ledger, DEC)
    by_code = {s.code: s for s in state.securities}
    assert by_code["AAA"].unrealised_gain == D("3000")
    assert by_code["BBB"].unrealised_gain == D("-2000")
    assert state.unrealised_gain == D("1000")
    assert state.securities_value == D("21000")
    assert state.cash == D("300")


def test_zero_cost_holding_does_not_produce_infinity():
    """Units received without consideration have no cost to divide by."""
    ledger, engine = build([
        ev(JAN, T.CORPORATE_ACTION, code="AAA", units=10),
    ], StubPrices({"AAA": {JAN: D("5")}}))

    holding = engine.state_at(ledger, JAN).securities[0]
    assert holding.cost_basis == D("0")
    assert holding.unrealised_gain == D("50")
    assert holding.unrealised_gain_pct is None      # not infinity, not NaN


def test_same_day_contribution_and_trade_are_not_netted():
    """Spec worked example (Trade & Cash Timing Model, sec 21/33): a $10,000
    deposit funding a same-day $10,000 purchase must show as +$10,000
    external contribution and $0 net cash change, never as a single netted
    event that hides the contribution from TWRR/XIRR."""
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=10000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-10000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
    ], StubPrices({"AAA": {JAN: D("100")}}))

    flows = CashEngine().flows(ledger)
    assert flows.deposits == D("10000")
    assert flows.net == D("0")          # cash unchanged: contribution in, buy out
    state = engine.state_at(ledger, JAN)
    assert state.cash == D("0")
    assert state.securities_value == D("10000")


def test_same_day_withdrawal_and_sale_are_not_netted():
    """Sale proceeds must never be classified as the withdrawal itself."""
    ledger, engine = build([
        ev(JAN, T.DEPOSIT, net=10000, settle=JAN),
        ev(JAN, T.TRANSFER, net=-10000, settle=JAN),
        ev(JAN, T.BUY, code="AAA", units=100, price=100, net=10000),
        ev(JUN, T.SELL, code="AAA", units=-100, price=100, net=-10000),
        ev(JUN, T.TRANSFER, net=10000, settle=JUN),
        ev(JUN, T.WITHDRAWAL, net=-8000, settle=JUN),
    ], StubPrices({"AAA": {JAN: D("100"), JUN: D("100")}}))

    flows = CashEngine().flows(ledger)
    assert flows.withdrawals == D("-8000")           # only the withdrawal
    assert flows.trade_settlement == D("0")           # sale nets against the buy
    state = engine.state_at(ledger, JUN)
    assert state.cash == D("2000")                    # 10000 proceeds - 8000 out
    assert state.realised_gain == D("0")               # sold at cost


def test_dividend_reinvestment_is_not_a_second_contribution():
    """Spec worked example: a dividend paid then reinvested must show exactly
    one external-flow total (the original deposit), not two."""
    ledger, engine = build([
        ev(date(2024, 5, 10), T.DEPOSIT, net=20000, settle=date(2024, 5, 10)),
        ev(date(2024, 5, 10), T.TRANSFER, net=-10000, settle=date(2024, 5, 10)),
        ev(date(2024, 5, 10), T.BUY, code="AAA", units=100, price=100, net=10000),
        ev(date(2024, 5, 20), T.DIVIDEND, code="AAA", net=150,
          settle=date(2024, 5, 20)),
        ev(date(2024, 5, 21), T.BUY, code="AAA", units=1, price=150, net=150),
        ev(date(2024, 5, 21), T.TRANSFER, net=-150, settle=date(2024, 5, 21)),
    ], StubPrices({"AAA": {date(2024, 5, 10): D("100")}}))

    flows = CashEngine().flows(ledger)
    assert flows.deposits == D("20000")               # not 20150
    assert flows.income == D("150")
    state = engine.state_at(ledger, date(2024, 5, 21))
    # 20000 deposited, 10000 spent on the original buy, 150 in as dividend,
    # 150 straight back out as the reinvestment: net 10000 cash remaining.
    assert state.cash == D("10000")
    # Market value uses the last quoted price ($100), carried forward -- not
    # the reinvestment's own purchase price. Confirms the engine never assumes
    # a transaction price equals market value (spec sec 7).
    assert state.securities_value == D("10100")       # 101 units x $100 estimated
    assert state.securities[0].units == D("101")
    assert flows.deposits + flows.withdrawals == D("20000")  # the only external flow
