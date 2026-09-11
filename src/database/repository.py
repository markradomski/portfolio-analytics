"""SQLite persistence.

All writes are INSERT OR REPLACE keyed on deterministic IDs, so importing the
same document twice overwrites identical rows rather than duplicating them.
That is what makes the pipeline safe to re-run.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from src.database.schema import DDL, SCHEMA_VERSION
from src.models import (Account, Document, Holding, IncomeEvent, Issue,
                        ParsedDocument, PortfolioValuation, Security,
                        StatementPeriod, Transaction)


def _text(value: Any) -> str | None:
    """Decimals and dates are stored as exact strings."""
    if value is None:
        return None
    if isinstance(value, (Decimal, date, datetime)):
        return str(value)
    if hasattr(value, "value"):      # Enum
        return str(value.value)
    return str(value)


def _row(*values: Any) -> tuple:
    return tuple(_text(v) for v in values)


class Repository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(DDL)
        self.conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', ?)",
            (str(SCHEMA_VERSION),))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- writes --------------------------------------------------------------

    def upsert_account(self, account: Account) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO accounts(account_id, label, base_currency)"
            " VALUES (?,?,?)",
            _row(account.account_id, account.label, account.base_currency))

    def upsert_document(self, doc: Document) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO documents(document_id, filename, kind,"
            " period_start, period_end, page_count, content_sha256,"
            " extraction_method, imported_at) VALUES (?,?,?,?,?,?,?,?,?)",
            _row(doc.document_id, doc.filename, doc.kind, doc.period_start,
                 doc.period_end, doc.page_count, doc.content_sha256,
                 doc.extraction_method, doc.imported_at))

    def upsert_securities(self, securities: Iterable[Security]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO securities(security_id, code, name, type,"
            " currency) VALUES (?,?,?,?,?)",
            [_row(s.security_id, s.code, s.name, s.type, s.currency)
             for s in securities])

    def upsert_transactions(self, rows: Iterable[Transaction]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO transactions(transaction_id, account_id,"
            " trade_date, settlement_date, type, security_id, units, price,"
            " gross_amount, fees, net_amount, currency, description, ordinal,"
            " source_document_id, source_page, extraction_method)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(t.transaction_id, t.account_id, t.trade_date, t.settlement_date,
                  t.type, t.security_id, t.units, t.price, t.gross_amount, t.fees,
                  t.net_amount, t.currency, t.description, t.ordinal,
                  t.provenance.document_id, t.provenance.page,
                  t.provenance.extraction_method) for t in rows])

    def delete_transactions(self, transaction_ids: Iterable[str]) -> None:
        """Remove specific transaction rows by id.

        Used only by the Vanguard CSV promotion step (Step 9B, Stage 5) to
        retire the PDF-derived rows a reconciled structured event supersedes
        -- never to repair or tidy data outside that documented workflow.
        Every other table (documents, holdings, income_events,
        portfolio_valuations, statement_periods, record_sources) is
        untouched, so full PDF source evidence remains intact for audit.
        """
        ids = list(transaction_ids)
        if not ids:
            return
        self.conn.executemany(
            "DELETE FROM transactions WHERE transaction_id = ?", [(i,) for i in ids])

    def upsert_holdings(self, rows: Iterable[Holding]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO holdings(holding_id, account_id,"
            " reporting_date, security_id, units, price, market_value, currency,"
            " source_document_id, source_page, extraction_method)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [_row(h.holding_id, h.account_id, h.reporting_date, h.security_id,
                  h.units, h.price, h.market_value, h.currency,
                  h.provenance.document_id, h.provenance.page,
                  h.provenance.extraction_method) for h in rows])

    def upsert_income(self, rows: Iterable[IncomeEvent]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO income_events(income_id, account_id,"
            " payment_date, security_id, amount, rate_per_unit, franking_credit,"
            " tax_withheld, ex_date, currency, source_document_id, source_page,"
            " extraction_method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(i.income_id, i.account_id, i.payment_date, i.security_id,
                  i.amount, i.rate_per_unit, i.franking_credit, i.tax_withheld,
                  i.ex_date, i.currency, i.provenance.document_id,
                  i.provenance.page, i.provenance.extraction_method) for i in rows])

    def upsert_valuations(self, rows: Iterable[PortfolioValuation]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO portfolio_valuations(valuation_id, account_id,"
            " reporting_date, portfolio_value, cash_balance, investment_value,"
            " accrued_income, currency, source_document_id, source_page,"
            " extraction_method) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [_row(v.valuation_id, v.account_id, v.reporting_date,
                  v.portfolio_value, v.cash_balance, v.investment_value,
                  v.accrued_income,
                  v.currency, v.provenance.document_id, v.provenance.page,
                  v.provenance.extraction_method) for v in rows])

    def upsert_periods(self, rows: Iterable[StatementPeriod]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO statement_periods(period_id, account_id, kind,"
            " period_start, period_end, opening_value, closing_value, deposits,"
            " withdrawals, transfers_in, transfers_out, change_in_value, income,"
            " withholding_tax, fees, reported_return, opening_cash,"
            " source_document_id, source_page, extraction_method)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(p.period_id, p.account_id, p.kind, p.period_start, p.period_end,
                  p.opening_value, p.closing_value, p.deposits, p.withdrawals,
                  p.transfers_in, p.transfers_out, p.change_in_value, p.income,
                  p.withholding_tax, p.fees, p.reported_return, p.opening_cash,
                  p.provenance.document_id, p.provenance.page,
                  p.provenance.extraction_method) for p in rows])

    def write_parsed(self, parsed: ParsedDocument) -> None:
        self.upsert_document(parsed.document)
        if parsed.tax_summary is not None:
            method = parsed.document.extraction_method
            self.ensure_securities_for_tax(parsed.security_tax)
            self.upsert_tax_summary(parsed.tax_summary,
                                    parsed.document.document_id, method)
            self.upsert_security_tax(parsed.security_tax,
                                     parsed.document.document_id, method)
        self.upsert_securities(parsed.securities)
        self.upsert_transactions(parsed.transactions)
        self.upsert_holdings(parsed.holdings)
        self.upsert_income(parsed.income)
        self.upsert_valuations(parsed.valuations)
        self.upsert_periods(parsed.periods)

    def start_run(self, run_id: str, source_path: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO import_runs(run_id, started_at, source_path)"
            " VALUES (?,?,?)", (run_id, datetime.now().isoformat(), source_path))

    def finish_run(self, run_id: str, documents_seen: int,
                   issues: Iterable[Issue]) -> None:
        self.conn.execute(
            "UPDATE import_runs SET finished_at=?, documents_seen=? WHERE run_id=?",
            (datetime.now().isoformat(), documents_seen, run_id))
        self.conn.execute("DELETE FROM issues WHERE run_id=?", (run_id,))
        self.conn.executemany(
            "INSERT OR REPLACE INTO issues(issue_id, run_id, severity, code,"
            " message, document_id, filename, page) VALUES (?,?,?,?,?,?,?,?)",
            [(f"{run_id}-{n}", run_id, i.severity.value, i.code, i.message,
              i.document_id, i.filename, i.page) for n, i in enumerate(issues)])
        self.conn.commit()

    # -- reads ---------------------------------------------------------------

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]

    def rows(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def commit(self) -> None:
        self.conn.commit()

    # -- provenance ----------------------------------------------------------

    RECORD_TABLES = {
        "transaction": ("transactions", "transaction_id"),
        "holding": ("holdings", "holding_id"),
        "income": ("income_events", "income_id"),
        "valuation": ("portfolio_valuations", "valuation_id"),
        "period": ("statement_periods", "period_id"),
    }

    def record_sources(self, parsed: ParsedDocument) -> None:
        """Note every document a record appears in, not just the latest."""
        doc = parsed.document.document_id
        rows = (
            [("transaction", t.transaction_id, doc, t.provenance.page) for t in parsed.transactions]
            + [("holding", h.holding_id, doc, h.provenance.page) for h in parsed.holdings]
            + [("income", i.income_id, doc, i.provenance.page) for i in parsed.income]
            + [("valuation", v.valuation_id, doc, v.provenance.page) for v in parsed.valuations]
            + [("period", p.period_id, doc, p.provenance.page) for p in parsed.periods]
        )
        self.conn.executemany(
            "INSERT OR REPLACE INTO record_sources(record_type, record_id,"
            " document_id, page) VALUES (?,?,?,?)", rows)

    def resolve_canonical_sources(self) -> None:
        """Point every record at its earliest source document.

        Which document a record is attributed to must not depend on the order
        files happened to be imported in, so 'earliest' is defined by the
        document's own reporting period, then its filename as a tie-break.
        """
        for record_type, (table, key) in self.RECORD_TABLES.items():
            self.conn.execute(
                f"""UPDATE {table} SET
                        source_document_id = (
                            SELECT s.document_id FROM record_sources s
                            JOIN documents d ON d.document_id = s.document_id
                            WHERE s.record_type = ? AND s.record_id = {table}.{key}
                            ORDER BY d.period_end IS NULL, d.period_end, d.filename
                            LIMIT 1),
                        source_page = (
                            SELECT s.page FROM record_sources s
                            JOIN documents d ON d.document_id = s.document_id
                            WHERE s.record_type = ? AND s.record_id = {table}.{key}
                            ORDER BY d.period_end IS NULL, d.period_end, d.filename
                            LIMIT 1)
                    WHERE EXISTS (SELECT 1 FROM record_sources s
                                  WHERE s.record_type = ? AND s.record_id = {table}.{key})""",
                (record_type, record_type, record_type))

    def sources_for(self, record_type: str, record_id: str) -> list[sqlite3.Row]:
        """Every document a record appears in, earliest first."""
        return self.rows(
            "SELECT d.filename, d.kind, d.period_end, s.page FROM record_sources s"
            " JOIN documents d ON d.document_id = s.document_id"
            " WHERE s.record_type = ? AND s.record_id = ?"
            " ORDER BY d.period_end IS NULL, d.period_end, d.filename",
            (record_type, record_id))

    # -- tax reports ---------------------------------------------------------

    TAX_SUMMARY_COLUMNS = (
        "gross_income", "net_income_received", "dividend_franking_credits",
        "trust_franking_credits", "foreign_income_tax_offsets",
        "total_tax_offsets", "withholding_tax", "total_fees",
        "gross_capital_gains", "net_capital_gain", "discounted_capital_gains",
        "cgt_concession", "capital_losses_carried_forward",
    )

    def upsert_tax_summary(self, summary, document_id: str, method: str) -> None:
        columns = ("tax_summary_id", "financial_year", "period_start",
                   "period_end", *self.TAX_SUMMARY_COLUMNS,
                   "source_document_id", "source_page", "extraction_method")
        values = _row(summary.tax_summary_id, summary.financial_year,
                      summary.period_start, summary.period_end,
                      *(getattr(summary, c) for c in self.TAX_SUMMARY_COLUMNS),
                      document_id, None, method)
        self.conn.execute(
            f"INSERT OR REPLACE INTO tax_summaries({','.join(columns)})"
            f" VALUES ({','.join('?' * len(columns))})", values)

    def upsert_security_tax(self, rows, document_id: str, method: str) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO security_tax_details(security_tax_id,"
            " financial_year, security_id, franked_amount, unfranked_amount,"
            " franking_credit, interest_income, other_deductions,"
            " source_document_id, source_page, extraction_method)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [_row(r.security_tax_id, r.financial_year, r.security_id,
                  r.franked_amount, r.unfranked_amount, r.franking_credit,
                  r.interest_income, r.other_deductions, document_id, r.page,
                  method) for r in rows])

    def ensure_securities_for_tax(self, rows) -> None:
        """A security may appear in a tax report before any statement holds it."""
        self.conn.executemany(
            "INSERT OR IGNORE INTO securities(security_id, code, name, type,"
            " currency) VALUES (?,?,?,?,?)",
            [(r.security_id, r.code, r.code, "ETF", "AUD") for r in rows])

    def enrich_income_from_tax(self, details, match_days: int = 7) -> tuple[int, list]:
        """Attach franking credits and ex dates to the matching income events.

        The statements and the tax report disagree about payment dates by a day
        or two, so a row is matched on security and amount within a small date
        window rather than on an exact date. A row that matches nothing, or more
        than one event, is left alone and reported.
        """
        matched, unmatched = 0, []
        for detail in details:
            if detail.payment_date is None:
                unmatched.append((detail, "no payment date"))
                continue
            cash = (detail.franked_amount or Decimal(0)) + (
                detail.unfranked_amount or Decimal(0))
            candidates = self.rows(
                "SELECT i.income_id FROM income_events i"
                " JOIN securities s USING (security_id)"
                " WHERE s.code = ? AND CAST(i.amount AS REAL) BETWEEN ? AND ?"
                "   AND ABS(JULIANDAY(i.payment_date) - JULIANDAY(?)) <= ?",
                (detail.code, float(cash) - 0.005, float(cash) + 0.005,
                 detail.payment_date.isoformat(), match_days))
            if len(candidates) != 1:
                unmatched.append(
                    (detail, "no match" if not candidates else "ambiguous"))
                continue
            self.conn.execute(
                "UPDATE income_events SET franking_credit = ?, ex_date = ?"
                " WHERE income_id = ?",
                (_text(detail.franking_credit),
                 _text(detail.ex_date), candidates[0]["income_id"]))
            matched += 1
        return matched, unmatched
