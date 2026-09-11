"""The cash ledger.

    opening + deposits + income + sale proceeds
           - purchases - withdrawals - fees - taxes = closing

Cash moves on settlement date. Purchases and sales enter here as their TRANSFER
rows -- the gross cash leg of a trade -- with brokerage as its own FEE row. The
BUY/SELL rows are deliberately excluded: their amounts are already net of
brokerage, so counting both sides would deduct every fee twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from src.engine.ledger import CASH_TYPES, Event, Ledger
from src.models import TxnType

ZERO = Decimal("0")


@dataclass
class CashFlows:
    deposits: Decimal = ZERO
    withdrawals: Decimal = ZERO
    income: Decimal = ZERO
    fees: Decimal = ZERO
    taxes: Decimal = ZERO
    trade_settlement: Decimal = ZERO      # net of buys and sells settling

    @property
    def net(self) -> Decimal:
        return (self.deposits + self.withdrawals + self.income
                + self.fees + self.taxes + self.trade_settlement)

    @property
    def external_net(self) -> Decimal:
        """Money crossing the portfolio boundary. Never performance."""
        return self.deposits + self.withdrawals


def opening_cash_for(repo) -> Decimal:
    """The cash balance the earliest statement opens on.

    Zero for a portfolio observed from inception; the earliest statement's
    own opening balance otherwise. Reconstructing cash from zero for a
    statement set that begins mid-life would be wrong by that amount for
    every day thereafter -- see docs/calculations.md.
    """
    rows = repo.rows(
        "SELECT opening_cash FROM statement_periods"
        " WHERE opening_cash IS NOT NULL AND period_start IS NOT NULL"
        " ORDER BY period_start LIMIT 1")
    return Decimal(rows[0]["opening_cash"]) if rows else ZERO


class CashEngine:
    """Cash balances and flows, keyed on settlement date.

    `opening` is the balance the ledger starts from. It is zero for a portfolio
    observed from inception, and the earliest statement's opening balance
    otherwise -- reconstructing from zero would understate cash for good.
    """

    def __init__(self, opening: Decimal = ZERO):
        self.opening = opening

    def _cash_events(self, ledger: Ledger, until: date | None = None):
        for event in ledger:
            if event.type not in CASH_TYPES:
                continue
            if until is not None and event.cash_date > until:
                continue
            yield event

    def flows(self, ledger: Ledger, start: date | None = None,
              end: date | None = None) -> CashFlows:
        totals = CashFlows()
        for event in self._cash_events(ledger):
            when = event.cash_date
            if start is not None and when <= start:
                continue
            if end is not None and when > end:
                continue
            amount = event.net_amount or ZERO
            if event.type is TxnType.DEPOSIT:
                totals.deposits += amount
            elif event.type is TxnType.WITHDRAWAL:
                totals.withdrawals += amount
            elif event.type in (TxnType.DIVIDEND, TxnType.DISTRIBUTION, TxnType.INTEREST):
                totals.income += amount
            elif event.type is TxnType.FEE:
                totals.fees += amount
            elif event.type is TxnType.TAX:
                totals.taxes += amount
            elif event.type is TxnType.TRANSFER:
                totals.trade_settlement += amount
        return totals

    def balances_over(self, ledger: Ledger, dates: list[date]):
        """Yield (date, balance, running flows) walking the ledger once."""
        events = sorted((e for e in ledger if e.type in CASH_TYPES),
                        key=lambda e: (e.cash_date, e.sort_key()))
        balance = self.opening
        totals = CashFlows()
        stream = iter(events)
        pending = next(stream, None)

        for when in dates:
            while pending is not None and pending.cash_date <= when:
                amount = pending.net_amount or ZERO
                balance += amount
                self._accumulate(totals, pending.type, amount)
                pending = next(stream, None)
            yield when, balance, CashFlows(**vars(totals))

    @staticmethod
    def _accumulate(totals: "CashFlows", kind: TxnType, amount: Decimal) -> None:
        if kind is TxnType.DEPOSIT:
            totals.deposits += amount
        elif kind is TxnType.WITHDRAWAL:
            totals.withdrawals += amount
        elif kind in (TxnType.DIVIDEND, TxnType.DISTRIBUTION, TxnType.INTEREST):
            totals.income += amount
        elif kind is TxnType.FEE:
            totals.fees += amount
        elif kind is TxnType.TAX:
            totals.taxes += amount
        elif kind is TxnType.TRANSFER:
            totals.trade_settlement += amount

    def balance_at(self, ledger: Ledger, when: date) -> Decimal:
        return self.opening + sum(
            (e.net_amount or ZERO for e in self._cash_events(ledger, when)), ZERO)

    def external_flows(self, ledger: Ledger) -> list[tuple[date, Decimal]]:
        """Dated contributions and withdrawals, for money-weighted return."""
        return sorted(
            (e.cash_date, e.net_amount or ZERO)
            for e in ledger if e.is_external_flow)
