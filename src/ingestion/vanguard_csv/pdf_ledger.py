"""Privacy-safe loader for the PDF-derived canonical ledger (Step 9B, Stage 4).

Reads only date / type / security code / signed amount / units from the
existing `transactions` and `income_events` tables. **Never** reads a PDF
`description` -- in this dataset those still carry investor initials and bank
names from the PDF pipeline (a pre-existing privacy gap outside 9B's scope).
"""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.ingestion.vanguard_csv.reconcile import PdfEvent
from src.models import TxnType


def _d(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def load_pdf_events(db_path: str | Path) -> list[PdfEvent]:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    events: list[PdfEvent] = []

    # The canonical ledger. Income is already represented here as
    # DIVIDEND/DISTRIBUTION rows (the engine reads these); `income_events` is
    # the enriched-detail table for the same events and is NOT loaded, to
    # avoid double-counting income during reconciliation.
    for r in con.execute(
        "SELECT t.transaction_id, t.type, s.code, t.trade_date, t.net_amount, t.units "
        "FROM transactions t LEFT JOIN securities s USING (security_id)"
    ):
        events.append(PdfEvent(
            transaction_id=r["transaction_id"], type=TxnType(r["type"]),
            security_code=r["code"], trade_date=date.fromisoformat(r["trade_date"]),
            net_amount=_d(r["net_amount"]), units=_d(r["units"]),
        ))

    con.close()
    return events


def pdf_closing_cash(db_path: str | Path) -> Decimal:
    """The PDF-derived closing cash balance -- from the latest portfolio
    valuation (privacy-safe: a number)."""
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT cash_balance FROM portfolio_valuations "
        "ORDER BY reporting_date DESC LIMIT 1").fetchone()
    con.close()
    return Decimal(str(row["cash_balance"])) if row and row["cash_balance"] is not None else Decimal("0")
