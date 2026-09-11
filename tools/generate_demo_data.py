"""Deterministic synthetic demo dataset (public release).

Generates a fictional portfolio's investment/cash transaction history in the
exact CSV shape the real Vanguard ingestion pipeline (src/ingestion/vanguard_csv/)
expects, then runs that SAME pipeline -- parse, cross-file trade match,
canonical candidate construction -- to seed a fresh SQLite database, and
rebuilds history through the existing HistoryStore. No financial figure here
is real; no financial figure is invented outside this generator (the engine
computes everything downstream exactly as it does for the real dataset).

Usage:
    ./venv/bin/python -m tools.generate_demo_data [--out demo-data/portfolio.demo.db]

Deterministic: fixed dates and formulas, no randomness, so the output (and
any screenshots taken against it) is exactly reproducible.
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database.repository import Repository
from src.engine.cash import CashEngine
from src.engine.config import DEFAULT_CONFIG
from src.engine.holdings import HoldingsEngine
from src.engine.ledger import Ledger
from src.ids import make_id
from src.ingestion.vanguard_csv.canonical import build_candidates
from src.ingestion.vanguard_csv.cash import parse_cash_csv
from src.ingestion.vanguard_csv.investment import parse_investment_csv
from src.ingestion.vanguard_csv.promote import (
    ACCOUNT_ID, PROMOTED_DOCUMENT_ID, PROMOTED_EXTRACTION_METHOD,
    seed_transactions_from_candidates,
)
from src.ingestion.vanguard_csv.securities_map import SecurityResolver
from src.ingestion.vanguard_csv.trade_match import match_trades
from src.models import (
    Account, Document, DocumentKind, Holding, PortfolioValuation, Provenance,
    Security, SecurityType,
)

# -- fictional securities -- no relation to any real fund or company -------
SECURITIES = [
    ("DAU", "Demo Australian Shares Index ETF", SecurityType.ETF),
    ("DIS", "Demo International Shares Index ETF", SecurityType.ETF),
    ("DFI", "Demo Fixed Interest Index ETF", SecurityType.ETF),
    ("DMN", "Demo Mining Group Ltd", SecurityType.SHARE),
    ("DTC", "Demo Technology Group Ltd", SecurityType.SHARE),
]
_TYPE_LABEL = {SecurityType.ETF: "ETF", SecurityType.SHARE: "Share"}

FAKE_ACCOUNT_NUMBER = "00000000"   # placeholder only; dropped by the parser


def _fmt_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def _months(start: date, end: date, step: int = 1):
    d = start
    while d <= end:
        yield d
        month = d.month - 1 + step
        year = d.year + month // 12
        month = month % 12 + 1
        d = date(year, month, min(d.day, 28))


# -- trades: (date, side, ticker, units, price, brokerage) ------------------
TRADES = [
    (date(2021, 1, 15), "Buy", "DAU", 100, Decimal("50.00"), None),
    (date(2021, 1, 15), "Buy", "DIS", 80, Decimal("60.00"), None),
    (date(2021, 4, 15), "Buy", "DFI", 50, Decimal("40.00"), None),
    (date(2021, 7, 15), "Buy", "DAU", 40, Decimal("55.00"), Decimal("9")),
    (date(2021, 10, 15), "Buy", "DMN", 30, Decimal("20.00"), Decimal("9")),
    (date(2022, 1, 15), "Buy", "DTC", 20, Decimal("35.00"), Decimal("9")),
    (date(2022, 4, 15), "Buy", "DIS", 30, Decimal("65.00"), Decimal("9")),
    (date(2022, 7, 15), "Buy", "DAU", 20, Decimal("58.00"), Decimal("9")),
    (date(2022, 10, 15), "Buy", "DFI", 25, Decimal("41.00"), None),
    (date(2023, 1, 15), "Buy", "DMN", 15, Decimal("22.00"), Decimal("9")),
    (date(2023, 4, 15), "Sell", "DMN", 20, Decimal("24.00"), Decimal("9")),
    (date(2023, 7, 15), "Sell", "DTC", 10, Decimal("38.00"), Decimal("9")),
    (date(2023, 10, 15), "Buy", "DAU", 15, Decimal("60.00"), None),
    (date(2024, 1, 15), "Sell", "DIS", 25, Decimal("68.00"), Decimal("9")),
    (date(2024, 4, 15), "Sell", "DFI", 30, Decimal("42.00"), None),
]

DEPOSITS = [
    (date(2021, 1, 10), Decimal("11000")),
    (date(2021, 2, 10), Decimal("2000")),
    (date(2021, 2, 14), Decimal("-2000")),   # dishonoured -- reverses the row above
    (date(2021, 4, 10), Decimal("2000")),
    (date(2021, 7, 10), Decimal("2200")),
    (date(2021, 10, 10), Decimal("600")),
    (date(2022, 1, 10), Decimal("700")),
    (date(2022, 4, 10), Decimal("2000")),
    (date(2022, 7, 10), Decimal("1200")),
    (date(2022, 10, 10), Decimal("1000")),
    (date(2023, 1, 10), Decimal("350")),
    (date(2023, 10, 10), Decimal("900")),
]

WITHDRAWALS = [
    (date(2023, 6, 1), Decimal("-1500")),
    (date(2024, 2, 1), Decimal("-3000")),
]

ADMIN_FEE_DATES = [date(2021, 4, 1), date(2021, 7, 1), date(2021, 10, 1),
                   date(2022, 1, 1), date(2022, 4, 1), date(2022, 7, 1),
                   date(2022, 10, 1), date(2023, 1, 1), date(2023, 4, 1),
                   date(2023, 7, 1), date(2023, 10, 1), date(2024, 1, 1),
                   date(2024, 4, 1)]
ADMIN_FEE_REVERSAL_INDEX = 4   # the 2022-07-01 charge is reversed 3 weeks later


# -- quarter-end price/valuation snapshots ----------------------------------
# Vanguard's own statements price a portfolio quarterly; this demo mirrors
# that cadence. Each security's price is a simple, clearly-synthetic 2%
# per-quarter drift from its first trade price -- not a market simulation,
# just enough movement for gains/losses and charts to be non-trivial.
QUARTER_ENDS = [date(y, m, d) for y in range(2021, 2025)
                for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))
                if date(y, m, d) <= date(2024, 6, 30)]

_GROWTH_PER_QUARTER = Decimal("1.02")


def _first_trade_price(code: str) -> tuple[date, Decimal]:
    for d, _side, c, _units, price, _brk in TRADES:
        if c == code:
            return d, price
    raise KeyError(code)


def _price_on(code: str, when: date) -> Decimal:
    first_date, base_price = _first_trade_price(code)
    quarters = max(0, sum(1 for q in QUARTER_ENDS if first_date <= q <= when))
    return (base_price * (_GROWTH_PER_QUARTER ** quarters)).quantize(Decimal("0.01"))


def build_valuation_snapshots(repo: Repository) -> None:
    """Quarter-end Holding + PortfolioValuation rows, computed by replaying
    the (already-written) transactions through the existing HoldingsEngine /
    CashEngine -- the same engine the real dataset uses -- so "reported"
    figures here are exactly what the accounting layer itself calculates,
    consistent with a synthetic dataset having no independent statement to
    differ from."""
    ledger = Ledger.from_repository(repo)
    holdings_engine = HoldingsEngine(DEFAULT_CONFIG)
    cash_engine = CashEngine()
    prov = Provenance(document_id=PROMOTED_DOCUMENT_ID, page=None,
                      extraction_method=PROMOTED_EXTRACTION_METHOD)

    holdings: list[Holding] = []
    valuations: list[PortfolioValuation] = []
    for when in QUARTER_ENDS:
        positions = holdings_engine.positions_at(ledger, when)
        securities_value = Decimal("0")
        for code, _name, _kind in SECURITIES:
            pos = positions.get(code)
            units = pos.units if pos else Decimal("0")
            if units == 0:
                continue
            price = _price_on(code, when)
            market_value = (units * price).quantize(Decimal("0.01"))
            securities_value += market_value
            holdings.append(Holding(
                holding_id=make_id("HLD", when.isoformat(), code), account_id=ACCOUNT_ID,
                reporting_date=when, security_id=code, units=units, price=price,
                market_value=market_value, currency="AUD", provenance=prov,
            ))
        cash = cash_engine.balance_at(ledger, when)
        valuations.append(PortfolioValuation(
            valuation_id=make_id("VAL", when.isoformat()), account_id=ACCOUNT_ID,
            reporting_date=when, portfolio_value=(securities_value + cash).quantize(Decimal("0.01")),
            cash_balance=cash.quantize(Decimal("0.01")), investment_value=securities_value,
            accrued_income=Decimal("0"), currency="AUD", provenance=prov,
        ))

    repo.upsert_holdings(holdings)
    repo.upsert_valuations(valuations)


def build_csvs() -> tuple[str, str]:
    inv_rows = []
    cash_rows = []
    security_by_code = {code: (name, kind) for code, name, kind in SECURITIES}

    for d, side, code, units, price, brokerage in TRADES:
        name, kind = security_by_code[code]
        value = (Decimal(units) * price).quantize(Decimal("0.01"))
        side_word = "Buy Trade" if side == "Buy" else "Sell trade"
        signed_units = units if side == "Buy" else -units
        inv_rows.append(
            f"{FAKE_ACCOUNT_NUMBER},{name},{code},{_TYPE_LABEL[kind]},{_fmt_date(d)},"
            f"{side_word},{price},{signed_units},{value},{brokerage or ''}"
        )
        cash_total = -value if side == "Buy" else value
        cash_units = -units if side == "Buy" else units
        cash_rows.append(
            f"{_fmt_date(d)},{side},{_TYPE_LABEL[kind]},{name},{code},{cash_units},{cash_total}"
        )
        if brokerage:
            fee_date = d + timedelta(days=2)
            cash_rows.append(
                f"{_fmt_date(fee_date)},Fees and Charges,Cash account,"
                f"{'Australian ETF' if kind is SecurityType.ETF else 'Australian Equity'}"
                f" Transaction fee for {name} {side},{code},,{-brokerage}"
            )

    for d, amount in DEPOSITS:
        cash_rows.append(f"{_fmt_date(d)},Deposit,Cash account,Demo Bank Transfer,CASH,,{amount}")
    for d, amount in WITHDRAWALS:
        cash_rows.append(f"{_fmt_date(d)},Withdrawal,Cash account,Demo Cash Withdrawal,CASH,,{amount}")

    for i, d in enumerate(ADMIN_FEE_DATES):
        amount = Decimal("2.50") + Decimal(i) * Decimal("0.10")
        cash_rows.append(f"{_fmt_date(d)},Fees and Charges,Cash account,OngoingAdminChargeByValue,CASH,,{-amount}")
        if i == ADMIN_FEE_REVERSAL_INDEX:
            rev_date = d + timedelta(days=21)
            cash_rows.append(
                f"{_fmt_date(rev_date)},Fees and Charges,Cash account,"
                f"Reversal: OngoingAdminChargeByValue,CASH,,{amount}")

    for d in _months(date(2021, 1, 28), date(2024, 6, 28)):
        interest = Decimal("0.40") + Decimal(d.month) * Decimal("0.05")
        cash_rows.append(f"{_fmt_date(d)},Interest,Cash account,Demo Cash Account Interest,CASH,,{interest}")

    quarter_starts = [date(y, m, 20) for y in range(2021, 2025) for m in (3, 6, 9, 12)
                      if date(y, m, 20) <= date(2024, 6, 28)]
    for d in quarter_starts:
        for code, name, kind in SECURITIES:
            amount = Decimal("15.00") if kind is SecurityType.ETF else Decimal("22.00")
            cash_rows.append(f"{_fmt_date(d)},Distribution,{_TYPE_LABEL[kind]},{name},{code if kind is SecurityType.SHARE else ''},,{amount}")

    inv_header = ("Account number,Investment,Product ID,Product Type,Trade Date,Type,"
                 "Unit Price,Quantity,Value,Brokerage")
    cash_header = "Date,Type,Product Type,Product Name,Product ID,Units,Total"
    inv_csv = inv_header + "\n" + "\n".join(inv_rows) + "\n"
    cash_csv = cash_header + "\n" + "\n".join(sorted(cash_rows, key=lambda r: r.split(",", 1)[0])) + "\n"
    return inv_csv, cash_csv


def build_database(out_path: Path) -> None:
    inv_csv, cash_csv = build_csvs()

    ir = parse_investment_csv(inv_csv)
    cr = parse_cash_csv(cash_csv)
    if ir.quarantined or cr.quarantined:
        raise SystemExit(f"synthetic data failed to parse cleanly: "
                         f"{[q.reason_code for q in ir.quarantined + cr.quarantined]}")

    resolver = SecurityResolver()
    resolver.seed_from_investment_records(ir.investment_records)

    match = match_trades(ir.investment_records, cr.cash_records)
    if not match.is_clean():
        raise SystemExit(f"synthetic trades did not match cleanly: {match.counts()}")

    candidates = build_candidates(match, ir.investment_records, cr.cash_records, resolver)
    transactions = seed_transactions_from_candidates(candidates)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    repo = Repository(out_path)
    repo.upsert_account(Account(account_id=ACCOUNT_ID, label="demo"))
    repo.upsert_securities([
        Security(security_id=code, code=code, name=name, type=kind)
        for code, name, kind in SECURITIES
    ])
    repo.upsert_document(Document(
        document_id=PROMOTED_DOCUMENT_ID, filename="synthetic-demo-dataset",
        kind=DocumentKind.OTHER, period_start=None, period_end=None, page_count=0,
        content_sha256=make_id("DEMO_DOC", "synthetic"),
        extraction_method=PROMOTED_EXTRACTION_METHOD, imported_at="2024-01-01T00:00:00",
    ))
    repo.upsert_transactions(transactions)
    repo.commit()

    build_valuation_snapshots(repo)
    repo.commit()
    repo.close()
    print(f"wrote {out_path} ({len(transactions)} transactions, {len(QUARTER_ENDS)} quarterly valuations)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "demo-data" / "portfolio.demo.db")
    args = parser.parse_args()
    build_database(args.out)


if __name__ == "__main__":
    main()
