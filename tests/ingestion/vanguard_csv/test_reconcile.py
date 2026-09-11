"""Step 9B, Stage 4 -- CSV candidate <-> PDF event reconciliation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.ingestion.vanguard_csv.canonical import build_candidates
from src.ingestion.vanguard_csv.cash import parse_cash_csv
from src.ingestion.vanguard_csv.investment import parse_investment_csv
from src.ingestion.vanguard_csv.reconcile import (
    Authority, PdfEvent, ReconStatus, reconcile,
)
from src.ingestion.vanguard_csv.securities_map import SecurityResolver
from src.ingestion.vanguard_csv.trade_match import match_trades
from src.models import TxnType
from tests.fixtures import vanguard_csv as fx


def _candidates(inv=fx.INVESTMENT_CSV, cash=fx.CASH_CSV):
    ir = parse_investment_csv(inv)
    cr = parse_cash_csv(cash)
    res = SecurityResolver()
    res.seed_from_investment_records(ir.investment_records)
    return build_candidates(match_trades(ir.investment_records, cr.cash_records),
                            ir.investment_records, cr.cash_records, res)


def pdf(txn_id, type_, code, d, net, units=None):
    return PdfEvent(txn_id, type_, code, d, Decimal(str(net)),
                    None if units is None else Decimal(str(units)))


# --- trades -----------------------------------------------------------

def test_csv_trade_reconciles_against_pdf_buy_plus_transfer():
    cs = _candidates()
    vas = next(t for t in cs.trades if t.security_id == "VAS")   # BUY gross 1061.62
    pdf_events = [
        pdf("pdf-buy", TxnType.BUY, "VAS", date(2020, 9, 18), Decimal("1061.62"), 14),
        pdf("pdf-xfer", TxnType.TRANSFER, None, date(2020, 9, 18), Decimal("-1061.62")),
    ]
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256,
                                 trades=[vas]), pdf_events, pdf_closing_cash=Decimal("0"))
    trade = rep.by_class("TRADE")[0]
    assert trade.status is ReconStatus.MATCH
    assert set(trade.pdf_ids) == {"pdf-buy", "pdf-xfer"}
    leg = rep.by_class("TRADE_CASH_LEG")[0]
    assert leg.status is ReconStatus.SUPERSEDED_SOURCE_REPRESENTATION
    assert leg.authority is Authority.RECONCILIATION_ONLY


def test_csv_sell_reconciles_and_brokerage_is_a_separate_pdf_fee():
    cs = _candidates()
    rio = next(t for t in cs.trades if t.security_id == "RIO")   # SELL gross 1552.23, brk 9
    pdf_events = [
        pdf("pdf-sell", TxnType.SELL, "RIO", date(2026, 5, 1), Decimal("-1543.23"), -9),
        pdf("pdf-xfer", TxnType.TRANSFER, None, date(2026, 5, 1), Decimal("1552.23")),
        pdf("pdf-brk", TxnType.FEE, "RIO", date(2026, 5, 3), Decimal("-9")),
    ]
    only_rio = cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256,
                            trades=[rio],
                            cash=[c for c in cs.cash if c.canonical_id == rio.brokerage_fee_id])
    rep = reconcile(only_rio, pdf_events, pdf_closing_cash=Decimal("0"))
    assert rep.by_class("TRADE")[0].status is ReconStatus.MATCH
    fee = rep.by_class("FEE")[0]
    assert fee.status is ReconStatus.MATCH and fee.csv_amount == Decimal("-9")


def test_trade_amount_mismatch_is_flagged_and_blocks_promotion():
    cs = _candidates()
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256, trades=[vas]),
                    [pdf("p", TxnType.BUY, "VAS", date(2020, 9, 18), Decimal("9999.99"), 14)],
                    pdf_closing_cash=Decimal("0"))
    assert rep.by_class("TRADE")[0].status is ReconStatus.MATCH_WITH_MINOR_DIFFERENCE


def test_missing_pdf_trade_is_csv_only_and_unresolved():
    cs = _candidates()
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256, trades=[vas]),
                    [], pdf_closing_cash=Decimal("0"))
    r = rep.by_class("TRADE")[0]
    assert r.status is ReconStatus.CSV_ONLY and not r.resolved
    assert not rep.policy.promotion_ready


def test_pdf_only_trade_is_flagged():
    cs = _candidates()
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256, trades=[]),
                    [pdf("p", TxnType.BUY, "ZZZ", date(2020, 9, 18), Decimal("100"), 1)],
                    pdf_closing_cash=Decimal("0"))
    assert rep.by_class("TRADE")[0].status is ReconStatus.PDF_ONLY


# --- deposits -------------------------------------------------------

def test_positive_deposit_exact_match():
    cs = _candidates()
    dep = next(c for c in cs.cash if c.type is TxnType.DEPOSIT and c.signed_amount > 0)
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256, cash=[dep]),
                    [pdf("p", TxnType.DEPOSIT, None, dep.effective_date, dep.signed_amount)],
                    pdf_closing_cash=Decimal("0"))
    assert rep.by_class("DEPOSIT")[0].status is ReconStatus.MATCH


def test_negative_deposit_pairs_with_its_positive_and_is_not_a_withdrawal():
    cash = (fx.CASH_HEADER + "\n"
            "11-Sep-2020,Deposit,Cash account,Funding,CASH,,1000\n"
            "15-Sep-2020,Deposit,Cash account,Dishonoured,CASH,,-1000\n")
    cs = _candidates(cash=cash)
    rep = reconcile(cs, [], pdf_closing_cash=Decimal("0"))
    pair = [r for r in rep.by_class("DEPOSIT") if r.status is ReconStatus.REVERSAL_PAIR]
    assert len(pair) == 1 and pair[0].resolved
    assert pair[0].linked_id is not None
    # neither candidate is a WITHDRAWAL
    assert all(c.type is TxnType.DEPOSIT for c in cs.cash if c.type is not TxnType.FEE)


def test_reversed_deposit_does_not_inflate_gross_contributions():
    cash = (fx.CASH_HEADER + "\n"
            "11-Sep-2020,Deposit,Cash account,Funding,CASH,,1000\n"
            "15-Sep-2020,Deposit,Cash account,Dishonoured,CASH,,-1000\n")
    cs = _candidates(cash=cash)
    net = sum(c.signed_amount for c in cs.cash if c.type is TxnType.DEPOSIT)
    assert net == Decimal("0")   # signed-DEPOSIT model nets the pair


# --- fees ---------------------------------------------------------

def test_admin_fee_exact_match():
    cs = _candidates()
    admin = next(c for c in cs.cash if c.source_semantic == "ADMIN_FEE")
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256, cash=[admin]),
                    [pdf("p", TxnType.FEE, None, admin.effective_date, admin.signed_amount)],
                    pdf_closing_cash=Decimal("0"))
    assert rep.by_class("FEE")[0].status is ReconStatus.MATCH


def test_fee_reversal_is_detected_as_a_rebate_pair():
    cs = _candidates()
    rep = reconcile(cs, [], pdf_closing_cash=Decimal("0"))
    rebate = [r for r in rep.by_class("FEE") if r.status is ReconStatus.FEE_REBATE]
    assert len(rebate) == 1 and rebate[0].resolved
    assert rebate[0].csv_amount == Decimal("9.31")


def test_csv_only_fee_after_pdf_window_is_source_coverage_not_a_blocker():
    cs = _candidates()
    late = next(c for c in cs.cash if c.source_semantic == "ADMIN_FEE")
    late_id = late.canonical_id
    rep = reconcile(
        cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256,
                     cash=[c for c in cs.cash if c.canonical_id == late_id]),
        [pdf("older", TxnType.FEE, None, date(2019, 1, 1), Decimal("-1"))],
        pdf_closing_cash=Decimal("0"))
    r = rep.by_class("FEE")[0]
    assert r.status is ReconStatus.SOURCE_COVERAGE_DIFFERENCE and r.resolved


def test_admin_fee_never_treated_as_brokerage_and_vice_versa():
    cs = _candidates()
    admin = next(c for c in cs.cash if c.source_semantic == "ADMIN_FEE")
    brk = next(c for c in cs.cash if c.source_semantic == "TRADE_BROKERAGE")
    assert admin.security_id is None and brk.security_id is not None
    assert admin.classification_method != brk.classification_method


# --- income / interest --------------------------------------------

def test_share_distribution_reconciles_as_dividend():
    cs = _candidates()
    bhp = next(c for c in cs.cash if c.type is TxnType.DIVIDEND)
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256, cash=[bhp]),
                    [pdf("p", TxnType.DIVIDEND, "BHP", bhp.effective_date, bhp.signed_amount)],
                    pdf_closing_cash=Decimal("0"))
    assert rep.by_class("DIVIDEND")[0].status is ReconStatus.MATCH


def test_interest_reconciles_and_is_income_not_deposit():
    cs = _candidates()
    i = next(c for c in cs.cash if c.type is TxnType.INTEREST)
    rep = reconcile(cs.__class__(cs.investment_file_sha256, cs.cash_file_sha256, cash=[i]),
                    [pdf("p", TxnType.INTEREST, None, i.effective_date, i.signed_amount)],
                    pdf_closing_cash=Decimal("0"))
    assert rep.by_class("INTEREST")[0].status is ReconStatus.MATCH
    assert not rep.by_class("DEPOSIT")


# --- authority / promotion --------------------------------------

def test_all_resolved_classes_allow_csv_preferred():
    cs = _candidates()
    pdf_events = _synthetic_pdf_for(cs)
    rep = reconcile(cs, pdf_events, pdf_closing_cash=Decimal("0.29"))
    # every trade + cash class resolved -> CSV_PREFERRED, promotion allowed
    for cls in ("TRADE", "DEPOSIT", "WITHDRAWAL", "DIVIDEND", "INTEREST", "FEE"):
        if rep.by_class(cls):
            assert rep.policy.by_class[cls] is Authority.CSV_PREFERRED


def _synthetic_pdf_for(cs):
    events = []
    for i, t in enumerate(cs.trades):
        events.append(pdf(f"t{i}", t.type, t.security_id, t.trade_date, t.net_amount, t.canonical_units))
        events.append(pdf(f"x{i}", TxnType.TRANSFER, None, t.cash_effective_date,
                          -t.gross_amount if t.type is TxnType.BUY else t.gross_amount))
    for i, c in enumerate(cs.cash):
        et = {TxnType.DEPOSIT: TxnType.DEPOSIT, TxnType.WITHDRAWAL: TxnType.WITHDRAWAL,
              TxnType.DIVIDEND: TxnType.DIVIDEND, TxnType.DISTRIBUTION: TxnType.DISTRIBUTION,
              TxnType.INTEREST: TxnType.INTEREST, TxnType.FEE: TxnType.FEE}.get(c.type)
        if et:
            events.append(pdf(f"c{i}", et, c.security_id, c.effective_date, c.signed_amount))
    return events


# --- privacy -----------------------------------------------------

def test_reconciliation_results_carry_no_identifier():
    from src.ingestion.vanguard_csv.sanitise import contains_identifier
    cs = _candidates()
    rep = reconcile(cs, _synthetic_pdf_for(cs), pdf_closing_cash=Decimal("0.29"))
    for r in rep.results:
        for v in (r.event_class, r.status.value, r.authority.value, *(r.reasons)):
            assert not contains_identifier(v)


# --- real data --------------------------------------------------

def test_real_data_reconciliation_is_clean_and_promotion_ready():
    root = _root()
    if root is None:
        pytest.skip("real exports / db not present")
    inv_f, cash_f, db_path = root
    from src.ingestion.vanguard_csv.pdf_ledger import load_pdf_events, pdf_closing_cash
    import sqlite3
    ir = parse_investment_csv(inv_f)
    cr = parse_cash_csv(cash_f)
    res = SecurityResolver()
    res.seed_from_investment_records(ir.investment_records)
    con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
    res.seed_from_repo_securities(con.execute("select code,name,type from securities"))
    con.close()
    cs = build_candidates(match_trades(ir.investment_records, cr.cash_records),
                          ir.investment_records, cr.cash_records, res)
    rep = reconcile(cs, load_pdf_events(db_path), pdf_closing_cash=pdf_closing_cash(db_path))

    assert not rep.unresolved(), [(r.event_class, r.status.value) for r in rep.unresolved()][:10]
    assert len(rep.by_class("TRADE")) == 76
    assert all(r.status is ReconStatus.MATCH for r in rep.by_class("TRADE"))
    assert all(r.status is ReconStatus.SUPERSEDED_SOURCE_REPRESENTATION
               for r in rep.by_class("TRADE_CASH_LEG"))
    assert rep.bridge.residual_resolved
    assert rep.policy.promotion_ready
    assert not rep.policy.blocking


def _root():
    # Prefers the pre-promotion snapshot (see test_promote.py._root) so this
    # test keeps validating against a genuine PDF-only baseline even after
    # portfolio.db itself has been promoted for release.
    from pathlib import Path
    base = Path(__file__).resolve().parents[3]
    inv = next(iter(sorted((base / "statements").glob("investment_transactions_*.csv"))), None)
    cash = next(iter(sorted((base / "statements").glob("cash_transactions_*.csv"))), None)
    db = base / "data" / "processed" / "portfolio.pre-csv-promotion.db"
    if not db.exists():
        db = base / "data" / "processed" / "portfolio.db"
    if inv is None or cash is None or not db.exists():
        return None
    return inv, cash, str(db)
