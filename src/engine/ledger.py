"""The canonical transaction ledger.

Events are immutable and loaded once. Corrections are never applied by mutating
history: an adjustment event is appended instead, so the ledger always explains
how it reached a figure.

Ordering is fully determined by (date, kind, id) rather than by database row
order, so replaying the ledger twice always produces the same state.

Two conventions matter, and both are forced by how the statements are written:

* A trade appears twice -- once in the investment table (BUY/SELL, dated on the
  trade date, amount net of brokerage) and once in the cash ledger (TRANSFER,
  dated on settlement, gross, with brokerage as a separate FEE row). Holdings
  and cost basis come from the trade rows; cash comes from the cash rows. Using
  both for either double-counts brokerage.
* External flows are DEPOSIT and WITHDRAWAL only. Everything else moves money
  around inside the portfolio and must never look like performance.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Iterable, Sequence

from src.database.repository import Repository
from src.models import TxnType

# Corporate actions must be applied before anything else on their date -- a
# split or consolidation changes the unit count that a same-day buy/sell then
# acts on. Deposits precede buys/sells so contributed cash exists before it is
# invested. Withdrawals are last among cash movements, and valuation (outside
# this ledger, in the state engine) always happens after every same-day event.

# Events on the same date are applied in this order: money arrives, securities
# are bought or sold, then costs are taken out.
TYPE_ORDER = {
    TxnType.CORPORATE_ACTION: 0,
    TxnType.DEPOSIT: 1,
    TxnType.TRANSFER: 2,
    TxnType.BUY: 3,
    TxnType.SELL: 4,
    TxnType.DIVIDEND: 5,
    TxnType.DISTRIBUTION: 6,
    TxnType.INTEREST: 7,
    TxnType.TAX: 8,
    TxnType.FEE: 9,
    TxnType.WITHDRAWAL: 10,
    TxnType.OTHER: 11,
}

# Money crossing the portfolio boundary. Never investment performance.
EXTERNAL_FLOW_TYPES = frozenset({TxnType.DEPOSIT, TxnType.WITHDRAWAL})

# Shape the holdings and cost basis.
POSITION_TYPES = frozenset({TxnType.BUY, TxnType.SELL, TxnType.CORPORATE_ACTION})

# Investment income, as opposed to capital movement.
INCOME_TYPES = frozenset({TxnType.DIVIDEND, TxnType.DISTRIBUTION, TxnType.INTEREST})

# Move the cash balance. Deliberately excludes BUY/SELL: the cash side of a
# trade is its TRANSFER row, and the brokerage its own FEE row.
CASH_TYPES = frozenset(
    {TxnType.DEPOSIT, TxnType.WITHDRAWAL, TxnType.TRANSFER, TxnType.FEE,
     TxnType.TAX} | INCOME_TYPES)


def _dec(value) -> Decimal | None:
    return None if value is None else Decimal(value)


def _date(value) -> date | None:
    return None if value is None else date.fromisoformat(value)


@dataclass(frozen=True)
class Event:
    """One immutable financial event."""
    event_id: str
    trade_date: date
    settlement_date: date | None
    type: TxnType
    security_id: str | None
    code: str | None
    units: Decimal | None
    price: Decimal | None
    gross_amount: Decimal | None
    fees: Decimal | None
    net_amount: Decimal | None
    description: str
    is_adjustment: bool = False

    @property
    def effective_date(self) -> date:
        """The authoritative economic date: when this event affects the
        portfolio. For every event type currently modelled, this is trade_date
        -- for a BUY/SELL that is literally the trade date; for everything else
        (deposits, withdrawals, dividends, fees, tax, interest) trade_date
        already holds the cash-ledger's own date, which *is* the economic date
        for those types. See docs/timing.md."""
        return self.trade_date

    @property
    def cash_effective_date(self) -> date | None:
        """The date this event itself moves settled cash, or None when it does
        not move cash directly.

        BUY and SELL have no direct cash effect in this model: the cash side of
        a trade is represented by its paired TRANSFER event, which already
        carries the correct date (see docs/timing.md -- Vanguard's own cash
        ledger dates that entry on trade date, never on the settlement date
        printed in the investment-transaction table). Returning None here
        rather than a guess keeps that reallocation explicit instead of buried
        in a fallback.
        """
        if self.type in POSITION_TYPES:
            return None
        return self.trade_date

    @property
    def cash_date(self) -> date:
        """cash_effective_date, for callers that only ever see cash-moving
        events (everything in CASH_TYPES always has one). Raises if called on
        a BUY/SELL/CORPORATE_ACTION, where there is no single cash date to
        return -- callers there should use effective_date and look at the
        paired TRANSFER instead (see src/engine/settlement.py)."""
        if self.cash_effective_date is None:
            raise ValueError(
                f"{self.type.value} has no direct cash effect; its cash date"
                " belongs to a paired TRANSFER event, not to this one")
        return self.cash_effective_date

    @property
    def is_external_flow(self) -> bool:
        return self.type in EXTERNAL_FLOW_TYPES

    def sort_key(self) -> tuple:
        return (self.trade_date, TYPE_ORDER.get(self.type, 99), self.event_id)


def _from_row(row) -> Event:
    return Event(
        event_id=row["transaction_id"],
        trade_date=_date(row["trade_date"]),
        settlement_date=_date(row["settlement_date"]),
        type=TxnType(row["type"]),
        security_id=row["security_id"],
        code=row["code"],
        units=_dec(row["units"]),
        price=_dec(row["price"]),
        gross_amount=_dec(row["gross_amount"]),
        fees=_dec(row["fees"]),
        net_amount=_dec(row["net_amount"]),
        description=row["description"],
    )


class Ledger:
    """An immutable, deterministically ordered sequence of events."""

    def __init__(self, events: Sequence[Event]):
        self._events = tuple(sorted(events, key=lambda e: e.sort_key()))

    @classmethod
    def from_repository(cls, repo: Repository) -> "Ledger":
        rows = repo.rows(
            "SELECT t.*, s.code FROM transactions t"
            " LEFT JOIN securities s USING (security_id)")
        return cls([_from_row(r) for r in rows])

    def with_adjustments(self, adjustments: Iterable[Event]) -> "Ledger":
        """Append corrections as new events. History is never rewritten."""
        marked = [replace(a, is_adjustment=True) for a in adjustments]
        return Ledger(list(self._events) + marked)

    # -- access --------------------------------------------------------------

    def __iter__(self):
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    @property
    def events(self) -> tuple[Event, ...]:
        return self._events

    def up_to(self, when: date) -> tuple[Event, ...]:
        return tuple(e for e in self._events if e.trade_date <= when)

    def between(self, start: date, end: date) -> tuple[Event, ...]:
        return tuple(e for e in self._events if start < e.trade_date <= end)

    def of_type(self, *types: TxnType) -> tuple[Event, ...]:
        wanted = frozenset(types)
        return tuple(e for e in self._events if e.type in wanted)

    def for_security(self, security_id: str) -> tuple[Event, ...]:
        return tuple(e for e in self._events if e.security_id == security_id)

    @property
    def start(self) -> date | None:
        return self._events[0].trade_date if self._events else None

    @property
    def end(self) -> date | None:
        return self._events[-1].trade_date if self._events else None

    def event_dates(self) -> tuple[date, ...]:
        return tuple(sorted({e.trade_date for e in self._events}))
