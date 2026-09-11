"""Validation over the stored dataset.

Checks run against what was actually persisted rather than against in-memory
parse results, so they also catch anything lost in storage. Nothing here
repairs data: every check reports, and Phase 2 decides what to do about it.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from src.database.repository import Repository
from src.models import Issue, Severity
from src.validation import privacy
from src.normalisation.values import quarter_of

# Reported totals are rounded to cents; allow a cent of slack per component.
TOLERANCE = Decimal("0.05")
EARLIEST_PLAUSIBLE = date(1990, 1, 1)


def _dec(value) -> Decimal | None:
    return None if value is None else Decimal(value)


def _date(value) -> date | None:
    return None if value is None else date.fromisoformat(value)


def check_holding_signs(repo: Repository) -> list[Issue]:
    """Units and market values are quantities; neither may be negative."""
    issues = []
    for row in repo.rows(
        "SELECT h.holding_id, h.reporting_date, s.code, h.units, h.market_value,"
        " h.price, h.source_document_id, h.source_page"
        " FROM holdings h JOIN securities s USING (security_id)"
    ):
        for field in ("units", "market_value", "price"):
            value = _dec(row[field])
            if value is not None and value < 0:
                issues.append(Issue(
                    Severity.ERROR, "HOLDING_NEGATIVE",
                    f"{row['code']} at {row['reporting_date']}: {field} is {value}",
                    document_id=row["source_document_id"], page=row["source_page"]))
    return issues


def check_valuation_totals(repo: Repository) -> list[Issue]:
    """Reported portfolio value = securities + cash + income declared but unpaid."""
    issues = []
    by_date: dict[str, Decimal] = defaultdict(Decimal)
    for row in repo.rows("SELECT reporting_date, market_value FROM holdings"):
        by_date[row["reporting_date"]] += Decimal(row["market_value"])

    for row in repo.rows(
        "SELECT reporting_date, portfolio_value, cash_balance, accrued_income,"
        " source_document_id, source_page FROM portfolio_valuations"
    ):
        reported = _dec(row["portfolio_value"])
        cash = _dec(row["cash_balance"]) or Decimal(0)
        accrued = _dec(row["accrued_income"]) or Decimal(0)
        computed = by_date.get(row["reporting_date"], Decimal(0)) + cash + accrued
        if reported is None:
            continue
        drift = (computed - reported).copy_abs()
        if drift > TOLERANCE:
            issues.append(Issue(
                Severity.ERROR, "VALUATION_MISMATCH",
                f"{row['reporting_date']}: holdings+cash+accrued {computed} vs reported "
                f"{reported} (drift {computed - reported})",
                document_id=row["source_document_id"], page=row["source_page"]))
    return issues


def check_period_identity(repo: Repository) -> list[Issue]:
    """closing = opening + flows + change in value + income - tax - fees."""
    issues = []
    for row in repo.rows(
        "SELECT period_id, kind, period_start, period_end, opening_value,"
        " closing_value, deposits, withdrawals, transfers_in, transfers_out,"
        " change_in_value, income, withholding_tax, fees, source_document_id"
        " FROM statement_periods"
    ):
        opening, closing = _dec(row["opening_value"]), _dec(row["closing_value"])
        if opening is None or closing is None:
            issues.append(Issue(
                Severity.WARNING, "PERIOD_SUMMARY_INCOMPLETE",
                f"{row['kind']} period ending {row['period_end']} is missing"
                " opening or closing value",
                document_id=row["source_document_id"]))
            continue

        def part(name: str) -> Decimal:
            return _dec(row[name]) or Decimal(0)

        computed = (opening + part("deposits") + part("withdrawals")
                    + part("transfers_in") - part("transfers_out")
                    + part("change_in_value") + part("income")
                    - part("withholding_tax") - part("fees"))
        drift = computed - closing
        if drift.copy_abs() > TOLERANCE:
            issues.append(Issue(
                Severity.ERROR, "PERIOD_IDENTITY_DRIFT",
                f"{row['kind']} period ending {row['period_end']}: computed"
                f" closing {computed} vs reported {closing} (drift {drift})",
                document_id=row["source_document_id"]))
    return issues


def check_unit_continuity(repo: Repository) -> list[Issue]:
    """Buys must increase units and sells decrease them.

    Between two consecutive snapshots, reported units should move by exactly the
    net traded quantity. Drift means a missed trade, an unrecognised corporate
    action, or a distribution reinvested as units.
    """
    issues = []
    trades: dict[str, list[tuple[date, Decimal]]] = defaultdict(list)
    for row in repo.rows(
        "SELECT security_id, trade_date, units FROM transactions"
        " WHERE type IN ('BUY','SELL') AND units IS NOT NULL AND security_id IS NOT NULL"
    ):
        trades[row["security_id"]].append((_date(row["trade_date"]), Decimal(row["units"])))

    snapshots: dict[str, list[tuple[date, Decimal, str, str, int]]] = defaultdict(list)
    for row in repo.rows(
        "SELECT h.security_id, s.code, h.reporting_date, h.units,"
        " h.source_document_id, h.source_page FROM holdings h"
        " JOIN securities s USING (security_id)"
    ):
        snapshots[row["security_id"]].append(
            (_date(row["reporting_date"]), Decimal(row["units"]), row["code"],
             row["source_document_id"], row["source_page"]))

    for security_id, rows in snapshots.items():
        rows.sort(key=lambda r: r[0])
        previous_date, previous_units = None, Decimal(0)
        for when, units, code, doc_id, page in rows:
            traded = sum((qty for traded_on, qty in trades.get(security_id, [])
                          if (previous_date is None or traded_on > previous_date)
                          and traded_on <= when), Decimal(0))
            expected = previous_units + traded
            if (expected - units).copy_abs() > TOLERANCE:
                issues.append(Issue(
                    Severity.WARNING, "UNIT_CONTINUITY_DRIFT",
                    f"{code} at {when}: expected {expected} units from prior"
                    f" snapshot {previous_units} plus {traded} traded, reported {units}",
                    document_id=doc_id, page=page))
            previous_date, previous_units = when, units
    return issues


def check_timeline(repo: Repository) -> list[Issue]:
    """Missing quarters, duplicate periods, and dates that cannot be real."""
    issues = []
    ends = [_date(r["period_end"]) for r in repo.rows(
        "SELECT period_end FROM statement_periods WHERE kind='QUARTERLY'"
        " ORDER BY period_end")]
    ends = [e for e in ends if e]

    seen = set()
    for end in ends:
        if end in seen:
            issues.append(Issue(Severity.WARNING, "DUPLICATE_PERIOD",
                                f"More than one quarterly period ends {end}"))
        seen.add(end)

    if ends:
        expected = quarter_of(ends[0])
        present = {quarter_of(e) for e in ends}
        last = quarter_of(ends[-1])
        while expected <= last:
            if expected not in present:
                issues.append(Issue(Severity.WARNING, "MISSING_QUARTER",
                                    f"No quarterly statement for {expected[0]} Q{expected[1]}"))
            year, quarter = expected
            expected = (year + 1, 1) if quarter == 4 else (year, quarter + 1)

    today = date.today()
    for table, column, label in (("transactions", "trade_date", "transaction"),
                                 ("holdings", "reporting_date", "holding"),
                                 ("income_events", "payment_date", "income event")):
        for row in repo.rows(
            f"SELECT {column} AS d, source_document_id, source_page FROM {table}"
        ):
            when = _date(row["d"])
            if when and (when > today or when < EARLIEST_PLAUSIBLE):
                issues.append(Issue(
                    Severity.ERROR, "IMPOSSIBLE_DATE",
                    f"{label} dated {when} is outside any plausible range",
                    document_id=row["source_document_id"], page=row["source_page"]))
    return issues


def check_transaction_windows(repo: Repository) -> list[Issue]:
    """Transactions should fall inside a reported statement period."""
    windows = [(_date(r["period_start"]), _date(r["period_end"])) for r in repo.rows(
        "SELECT period_start, period_end FROM statement_periods")]
    windows = [(s, e) for s, e in windows if s and e]
    if not windows:
        return []
    issues = []
    for row in repo.rows(
        "SELECT trade_date, description, source_document_id, source_page"
        " FROM transactions"
    ):
        when = _date(row["trade_date"])
        if when and not any(start <= when <= end for start, end in windows):
            issues.append(Issue(
                Severity.WARNING, "TRANSACTION_OUTSIDE_PERIOD",
                f"{when}: '{row['description'][:50]}' falls outside every"
                " reported statement period",
                document_id=row["source_document_id"], page=row["source_page"]))
    return issues


def check_missing_identifiers(repo: Repository) -> list[Issue]:
    """Trades with no recoverable security cannot be attributed in Phase 2."""
    return [Issue(
        Severity.WARNING, "MISSING_SECURITY",
        f"{row['trade_date']}: {row['type']} '{row['description'][:50]}' has no"
        " security identifier",
        document_id=row["source_document_id"], page=row["source_page"])
        for row in repo.rows(
            "SELECT trade_date, type, description, source_document_id, source_page"
            " FROM transactions WHERE security_id IS NULL"
            " AND type IN ('BUY','SELL','DIVIDEND','DISTRIBUTION')")]


def check_tax_totals(repo: Repository) -> list[Issue]:
    """Per-security tax detail must add up to the report's own totals.

    The annual report states both the breakdown and the totals, so they check
    each other: a row missed by the parser shows up here as a shortfall.
    """
    issues = []
    for row in repo.rows(
        "SELECT financial_year, dividend_franking_credits,"
        " trust_franking_credits, source_document_id FROM tax_summaries"
    ):
        year = row["financial_year"]

        trust = sum((_dec(r["franking_credit"]) or Decimal(0) for r in repo.rows(
            "SELECT franking_credit FROM security_tax_details"
            " WHERE financial_year = ?", (year,))), Decimal(0))
        reported_trust = _dec(row["trust_franking_credits"])
        if reported_trust is not None and (trust - reported_trust).copy_abs() > TOLERANCE:
            issues.append(Issue(
                Severity.ERROR, "TAX_TRUST_FRANKING_DRIFT",
                f"FY{year}: per-security trust franking credits total {trust}"
                f" but the report states {reported_trust}",
                document_id=row["source_document_id"]))

        # Australian financial year: 1 July to 30 June.
        dividends = sum((_dec(r["franking_credit"]) or Decimal(0) for r in repo.rows(
            "SELECT franking_credit FROM income_events"
            " WHERE franking_credit IS NOT NULL"
            "   AND payment_date > ? AND payment_date <= ?",
            (f"{year - 1}-06-30", f"{year}-06-30"))), Decimal(0))
        reported_dividends = _dec(row["dividend_franking_credits"])
        if (reported_dividends is not None
                and (dividends - reported_dividends).copy_abs() > TOLERANCE):
            issues.append(Issue(
                Severity.WARNING, "TAX_DIVIDEND_FRANKING_DRIFT",
                f"FY{year}: franking credits attached to income events total"
                f" {dividends} but the report states {reported_dividends}",
                document_id=row["source_document_id"]))
    return issues


def check_trade_settlement_pairing(repo: Repository) -> list[Issue]:
    """Every trade's cash effect must be traceable to a cash-ledger entry.

    A trade with no matching TRANSFER is not necessarily wrong -- it may simply
    not have settled as of the most recent statement -- but it must be visible
    rather than silently absorbed, per the timing contract in docs/timing.md.
    A trade whose cash effect landed on a different date than the trade itself
    would contradict the empirical pattern this portfolio has shown every time
    (cash moves same-day, always) and is flagged as an error rather than a
    warning, since it would mean the assumption has broken.
    """
    from src.engine.ledger import Ledger
    from src.engine.settlement import pair_trades_with_settlement

    ledger = Ledger.from_repository(repo)
    issues = []
    for pairing in pair_trades_with_settlement(ledger):
        if pairing.is_pending:
            issues.append(Issue(
                Severity.INFO, "SETTLEMENT_PENDING",
                f"{pairing.trade.trade_date} {pairing.trade.type.value}"
                f" {pairing.trade.code}: no matching cash-ledger entry yet"
                " (may simply not have settled as of the latest statement)"))
        elif pairing.transfer.trade_date != pairing.trade.trade_date:
            issues.append(Issue(
                Severity.ERROR, "SETTLEMENT_DATE_MISMATCH",
                f"{pairing.trade.trade_date} {pairing.trade.type.value}"
                f" {pairing.trade.code}: cash effect landed on"
                f" {pairing.transfer.trade_date}, not the trade date -- this"
                " contradicts the settlement-timing assumption in docs/timing.md"))
    return issues


ALL_CHECKS = (
    privacy.scan,
    check_holding_signs,
    check_valuation_totals,
    check_period_identity,
    check_unit_continuity,
    check_timeline,
    check_transaction_windows,
    check_missing_identifiers,
    check_tax_totals,
    check_trade_settlement_pairing,
)


def run_all(repo: Repository) -> list[Issue]:
    issues: list[Issue] = []
    for check in ALL_CHECKS:
        issues.extend(check(repo))
    return issues
