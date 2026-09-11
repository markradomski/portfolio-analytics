"""Isolated engine read-model for CSV-backed candidates (Step 9B, Stage 3 §22).

Purpose: prove the canonical candidate set is *consumable by the existing
accounting engine* -- nothing more. This is a read model, not a second
canonical representation and not persisted:

* one `TradeCandidate` expands into the (BUY/SELL, TRANSFER) pair the current
  engine already expects (holdings from the trade row, cash from the transfer);
  no separate canonical trade transaction is created in the candidate set;
* brokerage is left on the trade row's `fees` (as the PDF pipeline does) and is
  NOT turned into a cash movement -- the cash CSV shows none, and Stage 3 must
  not invent one;
* `net_amount` is left `None` on BUY/SELL so the engine applies its own
  `abs(units * price)` rule -- Stage 3 fabricates no net field.

The PDF-derived ledger is untouched; this builds a fresh in-memory `Ledger`
from candidates alone.
"""

from __future__ import annotations

from decimal import Decimal

from src.engine.ledger import Event, Ledger
from src.ingestion.vanguard_csv.canonical import CandidateSet, TradeCandidate
from src.models import TxnType

ZERO = Decimal("0")


def _trade_events(t: TradeCandidate) -> list[Event]:
    trade = Event(
        event_id=f"{t.canonical_id}:trade",
        trade_date=t.trade_date, settlement_date=t.cash_effective_date,
        type=t.type, security_id=t.security_id, code=t.security_id,
        units=t.canonical_units, price=t.price, gross_amount=t.gross_amount,
        fees=t.canonical_brokerage, net_amount=t.net_amount,
        description=f"{t.type.value} {t.security_id} (STRUCTURED_CSV)",
    )
    transfer = Event(
        event_id=f"{t.canonical_id}:transfer",
        trade_date=t.cash_effective_date, settlement_date=None,
        type=TxnType.TRANSFER, security_id=None, code=None,
        units=None, price=None, gross_amount=None, fees=None,
        net_amount=t.cash_effect,           # signed source cash movement (== -/+ gross)
        description=f"cash leg of {t.type.value} {t.security_id} (STRUCTURED_CSV)",
    )
    return [trade, transfer]


def project_events(cs: CandidateSet, *, include_reconciliation_pending: bool = False) -> list[Event]:
    """Candidate set -> engine `Event`s.

    `include_reconciliation_pending=False` (default) drops the events whose
    economic classification is still a Stage 4 question -- the 5 negative
    Deposit reversals and the positive fee row -- so the isolated ledger
    reflects only what Stage 3 can classify with confidence.
    """
    events: list[Event] = []

    for t in cs.trades:
        events.extend(_trade_events(t))

    for c in cs.cash:
        if (not include_reconciliation_pending
                and c.classification_status.value == "NEEDS_RECONCILIATION"):
            continue
        events.append(Event(
            event_id=c.canonical_id,
            trade_date=c.effective_date, settlement_date=None,
            type=c.type, security_id=c.security_id, code=c.security_id,
            units=None, price=None, gross_amount=None, fees=None,
            net_amount=c.signed_amount,
            description=f"{c.source_transaction_type} (STRUCTURED_CSV)",
        ))

    return events


def project_ledger(cs: CandidateSet, **kw) -> Ledger:
    return Ledger(project_events(cs, **kw))
