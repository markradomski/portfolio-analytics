"""Step 9B, Stage 5 (MVP) -- promoting reconciled CSV candidates into the
active accounting projection."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.database.repository import Repository
from src.ingestion.vanguard_csv.canonical import CandidateSet, build_candidates
from src.ingestion.vanguard_csv.cash import parse_cash_csv
from src.ingestion.vanguard_csv.investment import parse_investment_csv
from src.ingestion.vanguard_csv.promote import (
    ACCOUNT_ID, apply_promotion, build_promotion_plan,
)
from src.ingestion.vanguard_csv.reconcile import (
    Authority, PdfEvent, ReconciliationReport, ReconStatus, reconcile,
)
from src.ingestion.vanguard_csv.securities_map import SecurityResolver
from src.ingestion.vanguard_csv.trade_match import match_trades
from src.models import Account, Document, DocumentKind, Provenance, Security, SecurityType, Transaction, TxnType
from src.ids import make_id
from tests.fixtures import vanguard_csv as fx


def _candidates(inv=fx.INVESTMENT_CSV, cash=fx.CASH_CSV) -> CandidateSet:
    ir = parse_investment_csv(inv)
    cr = parse_cash_csv(cash)
    res = SecurityResolver()
    res.seed_from_investment_records(ir.investment_records)
    return build_candidates(match_trades(ir.investment_records, cr.cash_records),
                            ir.investment_records, cr.cash_records, res)


def pdf(txn_id, type_, code, d, net, units=None):
    return PdfEvent(txn_id, type_, code, d, Decimal(str(net)),
                    None if units is None else Decimal(str(units)))


def _only(cs: CandidateSet, *, trades=None, cash=None) -> CandidateSet:
    return CandidateSet(cs.investment_file_sha256, cs.cash_file_sha256,
                        trades=trades or [], cash=cash or [])


def _force_ready(rep: ReconciliationReport) -> ReconciliationReport:
    """These promotion-boundary tests exercise build_promotion_plan()'s own
    logic (which PDF ids it supersedes/keeps, what it builds) against a
    deliberately partial candidate/PDF-event slice -- not reconcile()'s cash
    bridge, which needs a whole-ledger pdf_closing_cash to make sense and is
    covered on its own in test_reconcile.py. Forcing promotion_ready here
    isolates the boundary this file is actually testing."""
    rep.policy.promotion_ready = True
    rep.policy.blocking = ()
    for r in rep.results:
        r.resolved = True
    return rep


# --- refusal behaviour --------------------------------------------------

def test_promotion_refuses_when_reconciliation_is_not_ready():
    empty = ReconciliationReport()
    empty.bridge = None
    from src.ingestion.vanguard_csv.reconcile import SourceAuthorityPolicy
    empty.policy = SourceAuthorityPolicy(promotion_ready=False, blocking=("unresolved TRADE",))
    plan = build_promotion_plan(_candidates(), empty)
    assert not plan.ready
    assert plan.blocking and not plan.new_transactions


def test_promotion_refuses_when_a_preferred_result_is_unresolved():
    cs = _candidates()
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    rep = reconcile(_only(cs, trades=[vas]), [])
    # force promotion_ready True to isolate the per-result guard
    rep.policy.promotion_ready = True
    plan = build_promotion_plan(_only(cs, trades=[vas]), rep)
    assert not plan.ready
    assert "unresolved" in plan.blocking[0]


# --- trade promotion -----------------------------------------------------

def test_matched_trade_supersedes_pdf_buy_and_transfer_exactly_once():
    cs = _candidates()
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    pdf_events = [
        pdf("pdf-buy", TxnType.BUY, "VAS", date(2020, 9, 18), Decimal("1061.62"), 14),
        pdf("pdf-xfer", TxnType.TRANSFER, None, date(2020, 9, 18), Decimal("-1061.62")),
    ]
    rep = reconcile(_only(cs, trades=[vas]), pdf_events)
    plan = build_promotion_plan(_only(cs, trades=[vas]), rep)
    assert plan.ready
    assert plan.superseded_pdf_ids == {"pdf-buy", "pdf-xfer"}
    buys = [t for t in plan.new_transactions if t.type is TxnType.BUY]
    transfers = [t for t in plan.new_transactions if t.type is TxnType.TRANSFER]
    assert len(buys) == 1 and len(transfers) == 1
    assert transfers[0].net_amount == vas.cash_effect


def test_brokered_trade_promotes_one_buy_one_transfer_one_brokerage_fee():
    cs = _candidates()
    rio = next(t for t in cs.trades if t.security_id == "RIO")   # SELL, $9 brokerage
    fee = next(c for c in cs.cash if c.canonical_id == rio.brokerage_fee_id)
    pdf_events = [
        pdf("pdf-sell", TxnType.SELL, "RIO", date(2026, 5, 1), Decimal("-1543.23"), -9),
        pdf("pdf-xfer", TxnType.TRANSFER, None, date(2026, 5, 1), Decimal("1552.23")),
        pdf("pdf-brk", TxnType.FEE, "RIO", date(2026, 5, 3), Decimal("-9")),
    ]
    only = _only(cs, trades=[rio], cash=[fee])
    rep = reconcile(only, pdf_events)
    plan = build_promotion_plan(only, rep)
    assert plan.ready
    assert plan.superseded_pdf_ids == {"pdf-sell", "pdf-xfer", "pdf-brk"}
    assert len(plan.new_transactions) == 3   # SELL + TRANSFER + brokerage FEE
    # brokerage is not folded into the trade's cash effect a second time
    xfer = next(t for t in plan.new_transactions if t.type is TxnType.TRANSFER)
    assert xfer.net_amount == rio.gross_amount   # gross only, no brokerage
    brk = next(t for t in plan.new_transactions if t.type is TxnType.FEE)
    assert brk.net_amount == Decimal("-9")


# --- deposits ------------------------------------------------------

def test_pdf_only_pre_coverage_deposit_is_kept_not_superseded():
    cs = _candidates()
    dep = next(c for c in cs.cash if c.type is TxnType.DEPOSIT and c.signed_amount > 0)
    only = _only(cs, cash=[dep])
    # pdf_closing_cash = csv-side closing (dep.signed_amount) + the PDF-only
    # pre-coverage event (5000), so the coverage-difference residual resolves.
    rep = _force_ready(reconcile(only, [pdf("pre", TxnType.DEPOSIT, None, date(1999, 1, 1), Decimal("5000"))]))
    plan = build_promotion_plan(only, rep)
    assert plan.ready
    assert "pre" in plan.kept_pdf_ids
    assert "pre" not in plan.superseded_pdf_ids


def test_negative_deposit_reversal_promoted_as_signed_deposit_not_withdrawal():
    cash = (fx.CASH_HEADER + "\n"
            "11-Sep-2020,Deposit,Cash account,Funding,CASH,,1000\n"
            "15-Sep-2020,Deposit,Cash account,Dishonoured,CASH,,-1000\n")
    cs = _candidates(cash=cash)
    rep = _force_ready(reconcile(cs, []))
    plan = build_promotion_plan(cs, rep)
    assert plan.ready
    deposits = [t for t in plan.new_transactions if t.type is TxnType.DEPOSIT]
    assert len(deposits) == 2
    assert {t.net_amount for t in deposits} == {Decimal("1000"), Decimal("-1000")}
    assert not any(t.type is TxnType.WITHDRAWAL for t in plan.new_transactions)
    # signed sum nets to zero -- never inflates lifetime contributed capital
    assert sum(t.net_amount for t in deposits) == Decimal("0")


# --- fees ----------------------------------------------------------

def test_fee_reversal_stays_positive_and_post_window_fee_is_retained():
    cs = _candidates()
    rev = next(c for c in cs.cash if c.source_semantic == "FEE_REVERSAL")
    only = _only(cs, cash=[rev])
    rep = _force_ready(reconcile(only, []))
    plan = build_promotion_plan(only, rep)
    assert plan.ready
    fee = plan.new_transactions[0]
    assert fee.type is TxnType.FEE and fee.net_amount == Decimal("9.31")


# --- determinism / privacy -----------------------------------------

def test_promoted_transaction_ids_are_deterministic():
    cs = _candidates()
    plan_a = build_promotion_plan(cs, reconcile(cs, []))
    plan_b = build_promotion_plan(cs, reconcile(cs, []))
    assert sorted(t.transaction_id for t in plan_a.new_transactions) == \
        sorted(t.transaction_id for t in plan_b.new_transactions)


def test_promoted_output_has_no_account_number_or_identifier():
    from src.ingestion.vanguard_csv.sanitise import contains_identifier
    cs = _candidates()
    rep = reconcile(cs, [])
    plan = build_promotion_plan(cs, rep)
    for t in plan.new_transactions:
        assert not contains_identifier(t.description)
        assert "99999999" not in t.transaction_id and "12345678" not in t.transaction_id


# --- DB round-trip (uniqueness / exclusion) -------------------------

def _seed_pdf_db(repo: Repository) -> None:
    repo.upsert_account(Account(account_id=ACCOUNT_ID, label="primary"))
    repo.upsert_document(Document(
        document_id="PDF-DOC", filename="synthetic.pdf", kind=DocumentKind.QUARTERLY,
        period_start=None, period_end=None, page_count=1,
        content_sha256=make_id("DOC", "synthetic"), extraction_method="pdfplumber-text",
        imported_at="2024-01-01T00:00:00"))
    repo.upsert_securities([Security(security_id="VAS", code="VAS", name="Vanguard Australian Shares Index ETF",
                                     type=SecurityType.ETF)])
    prov = Provenance(document_id="PDF-DOC", page=1, extraction_method="pdfplumber-text")
    repo.upsert_transactions([
        Transaction("pdf-buy", ACCOUNT_ID, date(2020, 9, 18), None, TxnType.BUY, "VAS",
                   Decimal("14"), Decimal("75.83"), Decimal("1061.62"), Decimal("0"),
                   Decimal("1061.62"), "AUD", "Buy VAS", 0, prov),
        Transaction("pdf-xfer", ACCOUNT_ID, date(2020, 9, 18), None, TxnType.TRANSFER, None,
                   None, None, None, None, Decimal("-1061.62"), "AUD", "Buy transaction of VAS", 0, prov),
        Transaction("pdf-pre-deposit", ACCOUNT_ID, date(1999, 1, 1), None, TxnType.DEPOSIT, None,
                   None, None, None, None, Decimal("5000"), "AUD", "Pre-coverage deposit", 0, prov),
    ])
    repo.commit()


def test_db_round_trip_excludes_superseded_pdf_and_keeps_fallback(tmp_path):
    repo = Repository(tmp_path / "promote.db")
    _seed_pdf_db(repo)

    vas_buy_leg = next(r for r in fx.CASH_ROWS if ",Buy," in r and ",VAS," in r)
    cs = _candidates(inv=(fx.INVESTMENT_HEADER + "\n" + fx.INVESTMENT_ROWS[0] + "\n"),
                     cash=(fx.CASH_HEADER + "\n" + vas_buy_leg + "\n"))   # VAS buy pair only
    pdf_events = [
        pdf("pdf-buy", TxnType.BUY, "VAS", date(2020, 9, 18), Decimal("1061.62"), 14),
        pdf("pdf-xfer", TxnType.TRANSFER, None, date(2020, 9, 18), Decimal("-1061.62")),
        pdf("pdf-pre-deposit", TxnType.DEPOSIT, None, date(1999, 1, 1), Decimal("5000")),
    ]
    rep = _force_ready(reconcile(cs, pdf_events))
    plan = build_promotion_plan(cs, rep)
    assert plan.ready
    apply_promotion(repo, plan)

    rows = repo.rows("SELECT transaction_id, type FROM transactions")
    ids = {r["transaction_id"] for r in rows}
    assert "pdf-buy" not in ids and "pdf-xfer" not in ids          # superseded, gone from active
    assert "pdf-pre-deposit" in ids                                 # fallback, kept
    buys = [r for r in rows if r["type"] == "BUY"]
    transfers = [r for r in rows if r["type"] == "TRANSFER"]
    assert len(buys) == 1 and len(transfers) == 1                  # exactly one of each, not two
    repo.close()


def test_apply_promotion_refuses_a_non_ready_plan(tmp_path):
    repo = Repository(tmp_path / "refuse.db")
    from src.ingestion.vanguard_csv.promote import PromotionPlan
    with pytest.raises(ValueError):
        apply_promotion(repo, PromotionPlan(ready=False, blocking=("x",)))
    repo.close()


# --- real data --------------------------------------------------

def _root():
    """Prefers `portfolio.pre-csv-promotion.db` -- a local, gitignored snapshot
    of the PDF-only ledger taken before Stage 5 promotion -- because this
    test needs a genuine "before" baseline to promote *against*. After a real
    promotion, `portfolio.db` itself is the release artifact (already
    promoted), not a fresh baseline; falls back to it only if no snapshot
    was taken, e.g. in a checkout that has never run the promotion."""
    base = Path(__file__).resolve().parents[3]
    inv = next(iter(sorted((base / "statements").glob("investment_transactions_*.csv"))), None)
    cash = next(iter(sorted((base / "statements").glob("cash_transactions_*.csv"))), None)
    db = base / "data" / "processed" / "portfolio.pre-csv-promotion.db"
    if not db.exists():
        db = base / "data" / "processed" / "portfolio.db"
    if inv is None or cash is None or not db.exists():
        return None
    return inv, cash, db


def test_real_data_promotion_yields_expected_active_counts(tmp_path):
    root = _root()
    if root is None:
        pytest.skip("real exports / db not present")
    inv_f, cash_f, db_path = root
    import shutil
    import sqlite3
    from src.ingestion.vanguard_csv.pdf_ledger import load_pdf_events, pdf_closing_cash

    work_db = tmp_path / "promote-real.db"
    shutil.copy(db_path, work_db)

    ir = parse_investment_csv(inv_f)
    cr = parse_cash_csv(cash_f)
    res = SecurityResolver()
    res.seed_from_investment_records(ir.investment_records)
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    res.seed_from_repo_securities(con.execute("select code,name,type from securities"))
    con.close()
    cs = build_candidates(match_trades(ir.investment_records, cr.cash_records),
                          ir.investment_records, cr.cash_records, res)
    rep = reconcile(cs, load_pdf_events(db_path), pdf_closing_cash=pdf_closing_cash(db_path))
    plan = build_promotion_plan(cs, rep)
    assert plan.ready, plan.blocking

    repo = Repository(work_db)
    apply_promotion(repo, plan)

    def count(sql):
        return repo.rows(sql)[0][0]

    assert count("SELECT COUNT(*) FROM transactions WHERE type='BUY'") == 52
    assert count("SELECT COUNT(*) FROM transactions WHERE type='SELL'") == 24
    assert count("SELECT COUNT(*) FROM transactions WHERE type='WITHDRAWAL'") == 18
    assert count("SELECT COUNT(*) FROM transactions WHERE type='DIVIDEND'") == 15
    assert count("SELECT COUNT(*) FROM transactions WHERE type='DISTRIBUTION'") == 71
    assert count("SELECT COUNT(*) FROM transactions WHERE type='INTEREST'") == 35
    # 31 CSV deposits + 3 pre-coverage PDF-only fallback deposits = 34
    assert count("SELECT COUNT(*) FROM transactions WHERE type='DEPOSIT'") == 34
    # exactly 76 active TRANSFER rows (one CSV-sourced per trade, PDF ones superseded)
    assert count("SELECT COUNT(*) FROM transactions WHERE type='TRANSFER'") == 76
    assert count(
        "SELECT COUNT(*) FROM transactions WHERE source_document_id != 'CSV-PROMOTED'"
        " AND type='TRANSFER'") == 0
    repo.close()
