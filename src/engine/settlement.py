"""Pending settlement detection.

The accounting contract requires the engine to be able to represent a gap
between a trade and its cash effect, rather than assuming one never exists.

For Vanguard Personal Investor, it empirically doesn't: the Cash Account ledger
dates a trade's cash entry on trade date, always -- confirmed across every
trade in this portfolio's history, and consistent with the statements' own
footnote that unsettled trades are excluded from the cash ledger rather than
shown against a later date. There is no liability/receivable to model between
trade and settlement for this data source, so nothing is added to
portfolio_value for a "pending" position: there has never been one.

This module exists so that claim is checked, not assumed. It pairs every
BUY/SELL with its cash-ledger TRANSFER and reports any trade left unmatched --
which would be a genuine pending settlement, and is exactly the case a future
statement (or a different account type) could produce.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.engine.ledger import Event, Ledger
from src.models import TxnType

ZERO = Decimal("0")
# Cash amounts are rounded to the cent; this only absorbs float/Decimal noise,
# not genuine partial fills.
AMOUNT_TOLERANCE = Decimal("0.01")


@dataclass(frozen=True)
class SettlementPairing:
    trade: Event
    transfer: Event | None

    @property
    def is_pending(self) -> bool:
        return self.transfer is None

    @property
    def cash_effective_date(self) -> date | None:
        """The date this trade's cash actually moved, if it has."""
        return self.transfer.trade_date if self.transfer else None

    @property
    def days_to_cash(self) -> int | None:
        """How long the trade's cash effect took, relative to the trade date."""
        if self.transfer is None:
            return None
        return (self.transfer.trade_date - self.trade.trade_date).days


def pair_trades_with_settlement(ledger: Ledger) -> list[SettlementPairing]:
    """Match every BUY/SELL to the TRANSFER that carries its cash effect.

    Matched by amount (a trade's net_amount is the negative of its transfer's)
    within a small date window, since nothing else links the two rows -- there
    is no shared identifier in the source statements. A trade matched to more
    than one candidate transfer, or to none, is reported rather than guessed at.
    """
    trades = [e for e in ledger.of_type(TxnType.BUY, TxnType.SELL)]
    transfers = list(ledger.of_type(TxnType.TRANSFER))
    used: set[str] = set()

    pairings: list[SettlementPairing] = []
    for trade in trades:
        # The cash ledger books a trade's principal separately from its
        # brokerage (a distinct FEE row), while a trade's own net_amount
        # already nets the fee in: BUY.net_amount includes the fee it cost to
        # acquire, SELL.net_amount has the fee already deducted from proceeds.
        # Adding the fee back recovers the principal the TRANSFER carries.
        target = -(trade.net_amount or ZERO) + (trade.fees or ZERO)
        candidates = [
            t for t in transfers
            if t.event_id not in used
            and (t.net_amount is not None)
            and (t.net_amount - target).copy_abs() <= AMOUNT_TOLERANCE
            and t.trade_date >= trade.trade_date
        ]
        candidates.sort(key=lambda t: (t.trade_date - trade.trade_date, t.event_id))
        match = candidates[0] if candidates else None
        if match:
            used.add(match.event_id)
        pairings.append(SettlementPairing(trade, match))
    return pairings


def pending_settlements(ledger: Ledger) -> list[SettlementPairing]:
    """Trades whose cash effect has not yet appeared in the cash ledger."""
    return [p for p in pair_trades_with_settlement(ledger) if p.is_pending]


def settlement_gaps(ledger: Ledger) -> list[SettlementPairing]:
    """Trades whose cash effect landed on a later date than the trade itself.

    Empirically empty for every statement seen so far -- see the module
    docstring. Kept as a check rather than an assumption: if a future import
    ever produces one, this is where it becomes visible.
    """
    return [p for p in pair_trades_with_settlement(ledger)
            if p.transfer is not None and p.transfer.trade_date != p.trade.trade_date]
