from datetime import date
from decimal import Decimal as D

from src.engine.cash import CashEngine
from src.engine.ledger import EXTERNAL_FLOW_TYPES, Ledger
from src.models import TxnType as T

from tests.conftest import ev

JAN, FEB = date(2024, 1, 10), date(2024, 2, 10)


def test_only_deposits_and_withdrawals_cross_the_boundary():
    assert EXTERNAL_FLOW_TYPES == {T.DEPOSIT, T.WITHDRAWAL}


def test_same_day_events_apply_in_accounting_order():
    """Money must arrive before it is spent, and costs come out last."""
    ledger = Ledger([
        ev(JAN, T.FEE, net=-10, settle=JAN, eid="fee"),
        ev(JAN, T.BUY, code="AAA", units=1, price=100, net=100, eid="buy"),
        ev(JAN, T.DEPOSIT, net=1000, settle=JAN, eid="dep"),
    ])
    assert [e.type for e in ledger] == [T.DEPOSIT, T.BUY, T.FEE]


def test_cash_moves_on_its_own_recorded_date():
    """A TRANSFER carries its own cash date -- Vanguard's cash ledger dates
    these directly, never via a separate settlement_date. See docs/timing.md
    for the empirical finding behind this."""
    ledger = Ledger([ev(JAN, T.TRANSFER, net=500, settle=None)])
    cash = CashEngine()
    assert cash.balance_at(ledger, date(2023, 12, 31)) == D("0")
    assert cash.balance_at(ledger, JAN) == D("500")


def test_settlement_date_is_irrelevant_for_non_trade_events():
    """settlement_date only means anything for BUY/SELL; a TRANSFER's own date
    is authoritative for cash regardless of what settlement_date holds."""
    ledger = Ledger([ev(JAN, T.TRANSFER, net=500, settle=FEB)])
    assert CashEngine().balance_at(ledger, JAN) == D("500")
    assert CashEngine().balance_at(ledger, FEB) == D("500")   # unchanged


def test_buy_and_sell_rows_do_not_move_cash():
    """Their cash effect is the TRANSFER row; counting both double-counts."""
    ledger = Ledger([
        ev(JAN, T.BUY, code="AAA", units=10, price=100, net=1000),
        ev(JAN, T.SELL, code="AAA", units=-5, price=110, net=-550),
    ])
    assert CashEngine().balance_at(ledger, JAN) == D("0")


def test_external_flows_are_dated_on_their_own_recorded_date():
    """A deposit's settle= is not meaningful; its own date is the cash date."""
    ledger = Ledger([ev(JAN, T.DEPOSIT, net=100, settle=FEB)])
    assert CashEngine().external_flows(ledger) == [(JAN, D("100"))]


def test_flows_split_income_from_capital():
    ledger = Ledger([
        ev(JAN, T.DEPOSIT, net=1000, settle=JAN),
        ev(JAN, T.DIVIDEND, code="AAA", net=50, settle=JAN),
        ev(JAN, T.INTEREST, net=2, settle=JAN),
        ev(JAN, T.FEE, net=-5, settle=JAN),
        ev(JAN, T.WITHDRAWAL, net=-200, settle=JAN),
    ])
    flows = CashEngine().flows(ledger)
    assert flows.deposits == D("1000")
    assert flows.withdrawals == D("-200")
    assert flows.income == D("52")
    assert flows.fees == D("-5")
    assert flows.external_net == D("800")
