"""Deterministic synthetic demo dataset (public release).

Generates a fictional portfolio's investment/cash transaction history in the
exact CSV shape the real Vanguard ingestion pipeline (src/ingestion/vanguard_csv/)
expects, then runs that SAME pipeline -- parse, cross-file trade match,
canonical candidate construction -- to seed a fresh SQLite database, and
rebuilds history through the existing HistoryStore. No financial figure here
is real; no financial figure is invented outside this generator (the engine
computes everything downstream exactly as it does for the real dataset).

~10 fictional years (2016-01 -> 2025-12) of a plausible retail investor:
irregular contributions (varying amounts, skipped periods, occasional larger
top-ups, one dishonoured/reversed deposit, several withdrawals including one
large one), five securities following different fictional "market regime"
price paths (so the portfolio shows genuine growth, corrections, a
substantial drawdown, sideways volatility and a recovery -- never every
security moving identically), and yield-based dividends/distributions that
vary with units actually held. Quarterly admin fees (one reversed) and
per-trade brokerage are preserved from the original, smaller demo.

Usage:
    ./venv/bin/python -m tools.generate_demo_data [--out demo-data/portfolio.demo.db]

Deterministic: every random choice is drawn from a `random.Random(DEMO_SEED)`
instance created fresh at the start of each build (never a module-level or
global instance), so running this twice -- even in the same process --
produces byte-for-byte identical transactions, prices, balances and holdings.
No system clock, no unseeded randomness, no financial figure computed by
anything other than the existing accounting/history engine.
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
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

DEMO_SEED = 42

START_DATE = date(2016, 1, 1)
END_DATE = date(2025, 12, 31)   # ~10 years of MAX history

# -- fictional securities -- no relation to any real fund or company -------
SECURITIES = [
    ("DAU", "Demo Australian Shares Index ETF", SecurityType.ETF),
    ("DIS", "Demo International Shares Index ETF", SecurityType.ETF),
    ("DFI", "Demo Fixed Interest Index ETF", SecurityType.ETF),
    ("DMN", "Demo Mining Group Ltd", SecurityType.SHARE),
    ("DTC", "Demo Technology Group Ltd", SecurityType.SHARE),
]
_TYPE_LABEL = {SecurityType.ETF: "ETF", SecurityType.SHARE: "Share"}
CODES = [code for code, _name, _kind in SECURITIES]

FAKE_ACCOUNT_NUMBER = "00000000"   # placeholder only; dropped by the parser

CENTS = Decimal("0.01")


def _fmt_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def _q2(x: Decimal) -> Decimal:
    return x.quantize(CENTS, rounding=ROUND_HALF_UP)


def _months(start: date, end: date):
    """First-of-month dates from `start` to `end` inclusive."""
    d = date(start.year, start.month, 1)
    while d <= end:
        yield d
        month = d.month + 1
        year = d.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        d = date(year, month, 1)


MONTHS = list(_months(START_DATE, END_DATE))

# ---------------------------------------------------------------------------
# Fictional market regimes -- purely synthetic simulation parameters, not a
# reproduction of any real market's history. Each is (start, monthly_drift,
# monthly_volatility, label); a month's regime is whichever entry's start is
# the latest one at or before it. Labels never appear in the UI -- they only
# steer the synthetic random walk below.
# ---------------------------------------------------------------------------
REGIMES = [
    (date(2016, 1, 1), Decimal("0.0060"), Decimal("0.020"), "moderate_growth"),
    (date(2018, 7, 1), Decimal("-0.0060"), Decimal("0.035"), "correction"),
    (date(2019, 7, 1), Decimal("0.0110"), Decimal("0.025"), "stronger_growth"),
    (date(2021, 7, 1), Decimal("-0.0300"), Decimal("0.060"), "drawdown"),
    (date(2023, 1, 1), Decimal("0.0010"), Decimal("0.030"), "sideways_volatile"),
    (date(2024, 1, 1), Decimal("0.0100"), Decimal("0.022"), "recovery_growth"),
]


def _regime_at(month: date) -> tuple[Decimal, Decimal, str]:
    current = REGIMES[0]
    for entry in REGIMES:
        if entry[0] <= month:
            current = entry
        else:
            break
    return current[1], current[2], current[3]


# Per-security behaviour: how strongly each reacts to the regime's drift and
# volatility, its fictional annual distribution yield, and how often it pays.
# Never identical across securities -- an ETF, a "defensive" bond-like ETF,
# and two cyclical/growth shares behave differently in every regime.
SECURITY_PROFILES: dict[str, dict] = {
    "DAU": {"drift_mult": Decimal("1.0"), "vol_mult": Decimal("1.0"),
            "yield": Decimal("0.035"), "dist_months": (3, 6, 9, 12), "defensive": False},
    "DIS": {"drift_mult": Decimal("1.15"), "vol_mult": Decimal("1.25"),
            "yield": Decimal("0.025"), "dist_months": (3, 6, 9, 12), "defensive": False},
    "DFI": {"drift_mult": Decimal("0.25"), "vol_mult": Decimal("0.30"),
            "yield": Decimal("0.032"), "dist_months": (3, 6, 9, 12), "defensive": True},
    "DMN": {"drift_mult": Decimal("1.4"), "vol_mult": Decimal("1.8"),
            "yield": Decimal("0.045"), "dist_months": (6, 12), "defensive": False},
    "DTC": {"drift_mult": Decimal("1.6"), "vol_mult": Decimal("2.0"),
            "yield": Decimal("0.008"), "dist_months": (6, 12), "defensive": False},
}

STARTING_PRICE = {
    "DAU": Decimal("50.00"), "DIS": Decimal("60.00"), "DFI": Decimal("40.00"),
    "DMN": Decimal("20.00"), "DTC": Decimal("35.00"),
}

_MIN_PRICE = Decimal("1.00")
_MAX_MONTHLY_MOVE = Decimal("0.28")   # clamp for plausibility, still lets DMN/DTC swing hard


def build_price_paths(rng: random.Random) -> dict[str, dict[date, Decimal]]:
    """One fictional monthly price per security per month in MONTHS. DFI
    (the "defensive" fixed-interest ETF) gets a flight-to-safety flip during
    the drawdown regime instead of following equities down -- the one
    explicit cross-security divergence beyond differing drift/vol
    multipliers, so the demo shows genuine diversification behaviour."""
    prices: dict[str, dict[date, Decimal]] = {code: {} for code in CODES}
    current = dict(STARTING_PRICE)
    for month in MONTHS:
        drift, vol, regime_label = _regime_at(month)
        for code in CODES:
            profile = SECURITY_PROFILES[code]
            if profile["defensive"] and regime_label == "drawdown":
                monthly_drift = Decimal("0.0045")
            else:
                monthly_drift = drift * profile["drift_mult"]
            monthly_vol = vol * profile["vol_mult"]
            noise = Decimal(str(round(rng.gauss(0.0, float(monthly_vol)), 6)))
            monthly_return = monthly_drift + noise
            monthly_return = max(-_MAX_MONTHLY_MOVE, min(_MAX_MONTHLY_MOVE, monthly_return))
            new_price = _q2(current[code] * (Decimal("1") + monthly_return))
            if new_price < _MIN_PRICE:
                new_price = _MIN_PRICE
            current[code] = new_price
            prices[code][month] = new_price
    return prices


def _month_of(d: date) -> date:
    return date(d.year, d.month, 1)


def _price_on(price_path: dict[str, dict[date, Decimal]], code: str, when: date) -> Decimal:
    """The generated price for the month containing `when` (prices only
    change monthly in this model)."""
    return price_path[code][_month_of(when)]


# ---------------------------------------------------------------------------
# Event generation -- a single deterministic forward pass over MONTHS.
#
# Cash is tracked as we go (ordinary Decimal arithmetic here, not a second
# accounting engine) purely so a randomly-chosen buy or withdrawal can be
# shrunk or skipped rather than ever driving the account negative -- the same
# thing a human investor \"can only spend what they have\" constraint would
# impose. The real accounting engine recomputes every figure independently,
# downstream, from the transactions this produces.
# ---------------------------------------------------------------------------

MIN_CASH_BUFFER = Decimal("25.00")
BOOTSTRAP_DEPOSIT_DATE = date(2016, 1, 10)
BOOTSTRAP_DEPOSIT = Decimal("11000.00")

# One dishonoured/reversed deposit, kept as a deterministic reconciliation
# edge case (not left to chance).
REVERSED_DEPOSIT_DATE = date(2016, 2, 10)
REVERSED_DEPOSIT_AMOUNT = Decimal("2000.00")
REVERSED_DEPOSIT_REVERSAL_DATE = date(2016, 2, 14)

# One deliberately large withdrawal, guaranteed rather than left to chance,
# sized against the simulated cash balance when the loop reaches it.
LARGE_WITHDRAWAL_MONTH = date(2022, 11, 1)
LARGE_WITHDRAWAL_TARGET = Decimal("8000.00")

TRADE_MONTHLY_PROB = 0.65
BUY_WEIGHTS = [3, 2, 2, 1.5, 1.5]   # DAU, DIS, DFI, DMN, DTC
BUY_MIN_TARGET = Decimal("300")
BUY_MAX_TARGET = Decimal("6000")


def _era_deposit_params(month: date) -> tuple[float, Decimal]:
    """Contribution frequency and base size both change across the decade --
    a higher, steadier cadence early, a quieter/more irregular stretch in the
    (fictional) 2020-2022 window, then a busier, larger-value stretch in the
    final recovery years. Never a flat, perfectly regular schedule."""
    year = month.year
    if year <= 2019:
        return 0.85, Decimal("450")
    if year <= 2022:
        return 0.55, Decimal("600")
    return 0.75, Decimal("850")


def build_events(rng: random.Random, price_path: dict[str, dict[date, Decimal]]) -> dict:
    cash = Decimal("0")
    units_held: dict[str, Decimal] = {code: Decimal("0") for code in CODES}

    trades: list[tuple] = []          # (date, side, code, units, price, brokerage)
    deposits: list[tuple[date, Decimal]] = []
    withdrawals: list[tuple[date, Decimal]] = []
    admin_fees: list[tuple[date, Decimal]] = []          # positive amounts; sign applied later
    admin_fee_reversal: tuple[date, Decimal] | None = None
    interest_rows: list[tuple[date, Decimal]] = []
    distribution_rows: list[tuple[date, str, Decimal]] = []

    # -- bootstrap: enough cash to fund the two opening positions -----------
    deposits.append((BOOTSTRAP_DEPOSIT_DATE, BOOTSTRAP_DEPOSIT))
    cash += BOOTSTRAP_DEPOSIT

    first_month = MONTHS[0]
    for code, units in (("DAU", Decimal(100)), ("DIS", Decimal(80))):
        price = price_path[code][first_month]
        trades.append((date(2016, 1, 15), "Buy", code, units, price, None))
        cash -= units * price
        units_held[code] += units

    admin_fee_month_count = 0
    for month_index, month in enumerate(MONTHS):
        year_idx = (month - START_DATE).days / 365.25

        # -- irregular contributions -----------------------------------
        prob, base = _era_deposit_params(month)
        if rng.random() < prob:
            jitter = Decimal(str(round(rng.uniform(0.7, 1.4), 3)))
            amount = _q2(base * jitter)
            if rng.random() < 0.08:   # occasional larger top-up (bonus, tax refund, ...)
                amount = _q2(amount * Decimal(str(round(rng.uniform(3.0, 6.0), 2))))
            d = date(month.year, month.month, rng.randint(5, 27))
            deposits.append((d, amount))
            cash += amount

        # -- occasional withdrawals, capped to what's actually available -
        if month == LARGE_WITHDRAWAL_MONTH:
            amount = min(LARGE_WITHDRAWAL_TARGET, max(Decimal("0"), cash - MIN_CASH_BUFFER))
            if amount > 0:
                d = date(month.year, month.month, 15)
                withdrawals.append((d, -amount))
                cash -= amount
        elif rng.random() < 0.05:
            target = Decimal(str(rng.choice([200, 350, 500, 800, 1200, 1500])))
            amount = min(target, max(Decimal("0"), cash - MIN_CASH_BUFFER))
            if amount >= Decimal("50"):
                d = date(month.year, month.month, rng.randint(5, 27))
                withdrawals.append((d, -amount))
                cash -= amount

        # -- trades: buys (cash-affordable) and sells (units-affordable) -
        if rng.random() < TRADE_MONTHLY_PROB:
            p_sell = min(0.55, max(0.05, 0.05 + 0.5 * (year_idx / 10)))
            held_codes = [c for c in CODES if units_held[c] > 0]
            if held_codes and rng.random() < p_sell:
                code = rng.choice(held_codes)
                price = price_path[code][month]
                held = units_held[code]
                sell_units = Decimal(rng.randint(1, max(1, int(held // 2) + 1)))
                sell_units = min(sell_units, held)
                brokerage = None if rng.random() < 0.15 else Decimal("9")
                d = date(month.year, month.month, rng.randint(5, 25))
                trades.append((d, "Sell", code, sell_units, price, brokerage))
                cash += sell_units * price - (brokerage or Decimal("0"))
                units_held[code] -= sell_units
            else:
                code = rng.choices(CODES, weights=BUY_WEIGHTS, k=1)[0]
                price = price_path[code][month]
                # Invest a random fraction of what's actually on hand, not a
                # fixed dollar amount -- a real DCA-plus-lump-sum investor
                # deploys accumulated cash rather than letting it pile up
                # regardless of balance, and this keeps the demo portfolio
                # meaningfully invested (not majority cash) across a decade.
                spendable = max(Decimal("0"), cash - MIN_CASH_BUFFER)
                fraction = Decimal(str(round(rng.uniform(0.35, 0.75), 3)))
                target = min(BUY_MAX_TARGET, max(BUY_MIN_TARGET, spendable * fraction))
                brokerage = None if rng.random() < 0.15 else Decimal("9")
                units = max(1, round(target / price))
                cost = units * price + (brokerage or Decimal("0"))
                if cost > cash - MIN_CASH_BUFFER:
                    affordable = int((cash - MIN_CASH_BUFFER - (brokerage or Decimal("0"))) / price)
                    units = affordable
                if units >= 1:
                    units = Decimal(units)
                    d = date(month.year, month.month, rng.randint(5, 25))
                    trades.append((d, "Buy", code, units, price, brokerage))
                    cash -= units * price + (brokerage or Decimal("0"))
                    units_held[code] += units

        # -- quarterly admin fee, growing slowly, one reversed -----------
        if month.month in (1, 4, 7, 10):
            admin_fee_month_count += 1
            fee = _q2(Decimal("3.00") + Decimal(admin_fee_month_count) * Decimal("0.12")
                     + Decimal(str(round(rng.uniform(-0.15, 0.15), 2))))
            fee = max(fee, Decimal("0.50"))
            d = date(month.year, month.month, 1)
            admin_fees.append((d, fee))
            cash -= fee
            if admin_fee_month_count == 5 and admin_fee_reversal is None:
                rev_d = d + timedelta(days=21)
                admin_fee_reversal = (rev_d, fee)
                cash += fee

        # -- interest: small, slowly growing, seeded jitter --------------
        interest = _q2(Decimal("0.30") + Decimal(str(year_idx)) * Decimal("0.18")
                       + Decimal(str(round(rng.uniform(-0.10, 0.10), 2))))
        interest = max(interest, Decimal("0.05"))
        d = date(month.year, month.month, 28)
        interest_rows.append((d, interest))
        cash += interest

        # -- distributions/dividends: yield * units actually held --------
        for code in CODES:
            profile = SECURITY_PROFILES[code]
            if month.month not in profile["dist_months"]:
                continue
            units = units_held[code]
            if units <= 0:
                continue
            price = price_path[code][month]
            freq = len(profile["dist_months"])
            jitter = Decimal(str(round(rng.uniform(0.85, 1.15), 3)))
            amount = _q2(units * price * profile["yield"] / Decimal(freq) * jitter)
            if amount <= 0:
                continue
            d = date(month.year, month.month, 20)
            distribution_rows.append((d, code, amount))
            cash += amount

    # -- deterministic reconciliation edge cases, added on top -----------
    deposits.append((REVERSED_DEPOSIT_DATE, REVERSED_DEPOSIT_AMOUNT))
    deposits.append((REVERSED_DEPOSIT_REVERSAL_DATE, -REVERSED_DEPOSIT_AMOUNT))
    if admin_fee_reversal is not None:
        rev_d, fee = admin_fee_reversal
        admin_fees_signed_reversal = (rev_d, fee)
    else:
        admin_fees_signed_reversal = None

    return {
        "trades": trades,
        "deposits": deposits,
        "withdrawals": withdrawals,
        "admin_fees": admin_fees,
        "admin_fee_reversal": admin_fees_signed_reversal,
        "interest": interest_rows,
        "distributions": distribution_rows,
        "final_cash": cash,
        "final_units_held": units_held,
    }


def build_csvs(events: dict) -> tuple[str, str]:
    inv_rows: list[str] = []
    cash_rows: list[str] = []
    security_by_code = {code: (name, kind) for code, name, kind in SECURITIES}

    for d, side, code, units, price, brokerage in events["trades"]:
        name, kind = security_by_code[code]
        value = _q2(units * price)
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

    for d, amount in events["deposits"]:
        cash_rows.append(f"{_fmt_date(d)},Deposit,Cash account,Demo Bank Transfer,CASH,,{amount}")
    for d, amount in events["withdrawals"]:
        cash_rows.append(f"{_fmt_date(d)},Withdrawal,Cash account,Demo Cash Withdrawal,CASH,,{amount}")

    for d, fee in events["admin_fees"]:
        cash_rows.append(f"{_fmt_date(d)},Fees and Charges,Cash account,OngoingAdminChargeByValue,CASH,,{-fee}")
    if events["admin_fee_reversal"] is not None:
        rev_d, fee = events["admin_fee_reversal"]
        cash_rows.append(
            f"{_fmt_date(rev_d)},Fees and Charges,Cash account,Reversal: OngoingAdminChargeByValue,CASH,,{fee}")

    for d, interest in events["interest"]:
        cash_rows.append(f"{_fmt_date(d)},Interest,Cash account,Demo Cash Account Interest,CASH,,{interest}")

    for d, code, amount in events["distributions"]:
        name, kind = security_by_code[code]
        product_id = code if kind is SecurityType.SHARE else ""
        cash_rows.append(f"{_fmt_date(d)},Distribution,{_TYPE_LABEL[kind]},{name},{product_id},,{amount}")

    inv_header = ("Account number,Investment,Product ID,Product Type,Trade Date,Type,"
                 "Unit Price,Quantity,Value,Brokerage")
    cash_header = "Date,Type,Product Type,Product Name,Product ID,Units,Total"
    inv_csv = inv_header + "\n" + "\n".join(inv_rows) + "\n"
    cash_csv = cash_header + "\n" + "\n".join(sorted(cash_rows, key=lambda r: r.split(",", 1)[0])) + "\n"
    return inv_csv, cash_csv


def build_valuation_snapshots(repo: Repository, price_path: dict[str, dict[date, Decimal]]) -> None:
    """Monthly Holding + PortfolioValuation rows, computed by replaying the
    (already-written) transactions through the existing HoldingsEngine /
    CashEngine -- the same engine the real dataset uses -- so "reported"
    figures here are exactly what the accounting layer itself calculates."""
    ledger = Ledger.from_repository(repo)
    holdings_engine = HoldingsEngine(DEFAULT_CONFIG)
    cash_engine = CashEngine()
    prov = Provenance(document_id=PROMOTED_DOCUMENT_ID, page=None,
                      extraction_method=PROMOTED_EXTRACTION_METHOD)

    valuation_dates = [date(m.year, m.month, 28) for m in MONTHS]

    holdings: list[Holding] = []
    valuations: list[PortfolioValuation] = []
    for when in valuation_dates:
        positions = holdings_engine.positions_at(ledger, when)
        securities_value = Decimal("0")
        for code in CODES:
            pos = positions.get(code)
            units = pos.units if pos else Decimal("0")
            if units == 0:
                continue
            price = _price_on(price_path, code, when)
            market_value = _q2(units * price)
            securities_value += market_value
            holdings.append(Holding(
                holding_id=make_id("HLD", when.isoformat(), code), account_id=ACCOUNT_ID,
                reporting_date=when, security_id=code, units=units, price=price,
                market_value=market_value, currency="AUD", provenance=prov,
            ))
        cash = cash_engine.balance_at(ledger, when)
        valuations.append(PortfolioValuation(
            valuation_id=make_id("VAL", when.isoformat()), account_id=ACCOUNT_ID,
            reporting_date=when, portfolio_value=_q2(securities_value + cash),
            cash_balance=_q2(cash), investment_value=securities_value,
            accrued_income=Decimal("0"), currency="AUD", provenance=prov,
        ))

    repo.upsert_holdings(holdings)
    repo.upsert_valuations(valuations)


def build_database(out_path: Path) -> None:
    rng = random.Random(DEMO_SEED)   # fresh instance every call -- see module docstring
    price_path = build_price_paths(rng)
    events = build_events(rng, price_path)
    inv_csv, cash_csv = build_csvs(events)

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
        extraction_method=PROMOTED_EXTRACTION_METHOD, imported_at="2016-01-01T00:00:00",
    ))
    repo.upsert_transactions(transactions)
    repo.commit()

    build_valuation_snapshots(repo, price_path)
    repo.commit()
    repo.close()
    print(f"wrote {out_path} ({len(transactions)} transactions, {len(MONTHS)} monthly valuations)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "demo-data" / "portfolio.demo.db")
    args = parser.parse_args()
    build_database(args.out)


if __name__ == "__main__":
    main()
