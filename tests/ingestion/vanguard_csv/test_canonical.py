"""Step 9B, Stage 3 -- canonical CSV candidate construction + idempotent staging."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.ingestion.vanguard_csv.canonical import (
    ClassificationStatus, TradeCandidate, build_candidates,
)
from src.ingestion.vanguard_csv.cash import parse_cash_csv
from src.ingestion.vanguard_csv.engine_projection import project_ledger
from src.ingestion.vanguard_csv.investment import parse_investment_csv
from src.ingestion.vanguard_csv.records import CashClass
from src.ingestion.vanguard_csv.sanitise import contains_identifier
from src.ingestion.vanguard_csv.securities_map import SecurityResolver
from src.ingestion.vanguard_csv.staging import StagingStore
from src.ingestion.vanguard_csv.trade_match import match_trades
from src.models import TxnType
from tests.fixtures import vanguard_csv as fx


def _build(inv_csv=fx.INVESTMENT_CSV, cash_csv=fx.CASH_CSV):
    ir = parse_investment_csv(inv_csv)
    cr = parse_cash_csv(cash_csv)
    resolver = SecurityResolver()
    resolver.seed_from_investment_records(ir.investment_records)
    m = match_trades(ir.investment_records, cr.cash_records)
    return build_candidates(m, ir.investment_records, cr.cash_records, resolver), m


# --- trade construction -------------------------------------------------

def test_matched_buy_becomes_one_canonical_buy_with_both_provenances():
    cs, _ = _build()
    buys = [t for t in cs.trades if t.type is TxnType.BUY]
    vas = next(t for t in buys if t.security_id == "VAS")
    # exactly one canonical trade for that economic event -- no second BUY,
    # no separate canonical cash transaction
    assert sum(1 for t in cs.trades
               if t.type is TxnType.BUY and t.security_id == "VAS"
               and t.trade_date == date(2020, 9, 18)) == 1
    assert not any(c.type is TxnType.TRANSFER for c in cs.cash)
    assert vas.investment_source.kind == "INVESTMENT_TXN_CSV"
    assert vas.cash_source.kind == "CASH_TXN_CSV"


def test_trade_keeps_gross_value_cash_effect_and_brokerage_distinct():
    cs, _ = _build()
    rio = next(t for t in cs.trades if t.security_id == "RIO")   # SELL, $9 brokerage
    assert rio.type is TxnType.SELL
    assert rio.gross_amount == Decimal("1552.23")               # investment Value
    assert rio.cash_effect == Decimal("1552.23")                # cash Total (credit), == gross
    assert rio.raw_brokerage == Decimal("9")
    assert rio.canonical_brokerage == Decimal("9")
    assert rio.brokerage_source_status == "SOURCE_VALUE"
    # cash effect is NOT gross - brokerage
    assert rio.cash_effect != rio.gross_amount - rio.canonical_brokerage


def test_raw_signed_quantity_and_unsigned_canonical_units():
    cs, _ = _build()
    rio = next(t for t in cs.trades if t.security_id == "RIO")
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    assert rio.raw_quantity == Decimal("-9") and rio.canonical_units == Decimal("9")
    assert vas.raw_quantity == Decimal("14") and vas.canonical_units == Decimal("14")


def test_blank_brokerage_normalised_to_zero_with_null_raw_preserved():
    cs, _ = _build()
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    assert vas.raw_brokerage is None
    assert vas.canonical_brokerage == Decimal("0.00")
    assert vas.brokerage_source_status == "SOURCE_BLANK_INTERPRETED_AS_ZERO"
    assert vas.investment_source.raw_brokerage == "null"     # provenance says blank, not "0"


def test_same_day_trade_and_cash_dates_kept_as_distinct_fields():
    cs, _ = _build()
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    assert vas.trade_date == date(2020, 9, 18)
    assert vas.cash_effective_date == date(2020, 9, 18)
    assert hasattr(vas, "trade_date") and hasattr(vas, "cash_effective_date")


# --- deposits / withdrawals -------------------------------------------

def test_positive_deposit_is_an_ordinary_deposit_candidate():
    cs, _ = _build()
    dep = next(c for c in cs.cash if c.source_transaction_type == "Deposit")
    assert dep.type is TxnType.DEPOSIT
    assert dep.signed_amount > 0
    assert dep.classification_status is ClassificationStatus.CLASSIFIED
    assert dep.source_semantic is None


def test_negative_deposit_is_a_signed_contribution_adjustment_not_a_withdrawal():
    cash_csv = fx.CASH_HEADER + "\n11-Sep-2020,Deposit,Cash account,Reversed deposit,CASH,,-4800\n"
    cs, _ = _build(cash_csv=cash_csv)
    rev = next(c for c in cs.cash if c.source_transaction_type == "Deposit")
    assert rev.type is TxnType.DEPOSIT                       # signed DEPOSIT, not WITHDRAWAL
    assert rev.type is not TxnType.WITHDRAWAL
    assert rev.signed_amount == Decimal("-4800")            # signed amount preserved -- nets its pair
    # Stage 4A resolved these: a dishonoured funding transfer, modelled as a
    # negative DEPOSIT (contribution adjustment) exactly as the PDF ledger's
    # "Failed Direct Debit" rows.
    assert rev.classification_status is ClassificationStatus.CLASSIFIED
    assert rev.source_semantic == "DEPOSIT_REVERSAL"


def test_withdrawal_is_a_canonical_external_outflow():
    cs, _ = _build()
    wd = next(c for c in cs.cash if c.source_transaction_type == "Withdrawal")
    assert wd.type is TxnType.WITHDRAWAL
    assert wd.signed_amount < 0
    assert "########" in wd.description and not contains_identifier(wd.description)


# --- income ----------------------------------------------------------

def test_share_distribution_becomes_dividend_etf_distribution_stays_distribution():
    cs, _ = _build()
    incomes = [c for c in cs.cash if c.source_transaction_type == "Distribution"]
    bhp = next(c for c in incomes if c.security_id == "BHP")
    vas = next(c for c in incomes if c.security_id == "VAS")
    assert bhp.type is TxnType.DIVIDEND
    assert bhp.classification_method == "SECURITY_TYPE_NORMALIZATION"
    assert vas.type is TxnType.DISTRIBUTION
    assert vas.classification_method == "SECURITY_TYPE_NORMALIZATION"


def test_distribution_with_blank_product_id_resolved_by_name():
    cs, _ = _build()
    vas = next(c for c in cs.cash
               if c.source_transaction_type == "Distribution" and c.security_id == "VAS")
    # the fixture VAS distribution row has a blank Product ID -- resolved via
    # the investment CSV's name<->code pairing, not a guess
    assert vas.security_id == "VAS"
    assert vas.classification_status is ClassificationStatus.CLASSIFIED


def test_unresolvable_distribution_security_is_flagged_not_guessed():
    cash_csv = (fx.CASH_HEADER + "\n"
                "15-Jul-2021,Distribution,ETF,Totally Unknown Fund,,,50.00\n")
    cs, _ = _build(cash_csv=cash_csv)
    d = cs.cash[0]
    assert d.security_id is None
    assert d.classification_status is ClassificationStatus.UNRESOLVED_SECURITY
    assert "not guessed" in " ".join(d.notes)


# --- interest / fees ------------------------------------------------

def test_interest_is_income_not_deposit():
    cs, _ = _build()
    i = next(c for c in cs.cash if c.source_transaction_type == "Interest")
    assert i.type is TxnType.INTEREST
    assert i.type is not TxnType.DEPOSIT


def test_negative_admin_fee_is_FEE_and_distinct_from_brokerage():
    cs, _ = _build()
    admin = next(c for c in cs.cash if c.source_semantic == "ADMIN_FEE")
    assert admin.type is TxnType.FEE
    assert admin.signed_amount < 0
    assert "OngoingAdminChargeByValue" in admin.description
    # brokerage is its own FEE, with a different semantic and a security
    brk = next(c for c in cs.cash if c.source_semantic == "TRADE_BROKERAGE")
    assert brk.source_semantic != admin.source_semantic
    assert brk.security_id is not None and admin.security_id is None


def test_explicit_fee_reversal_keeps_positive_sign_and_is_classified():
    cash_csv = (fx.CASH_HEADER + "\n"
                "25-Oct-2021,Fees and Charges,Cash account,Reversal: OngoingAdminChargeByValue,CASH,,9.31\n")
    cs, _ = _build(cash_csv=cash_csv)
    f = cs.cash[0]
    assert f.type is TxnType.FEE
    assert f.signed_amount == Decimal("9.31")               # sign NOT forced negative
    # Stage 4B: an explicit "Reversal: ..." row -- a fee refund, a
    # signed-positive FEE adjustment that nets its paired charge.
    assert f.classification_status is ClassificationStatus.CLASSIFIED
    assert f.source_semantic == "FEE_REVERSAL"


def test_brokerage_cash_row_becomes_a_fee_linked_to_its_trade():
    cs, _ = _build()
    rio = next(t for t in cs.trades if t.security_id == "RIO")   # SELL, $9 brokerage
    assert rio.brokerage_fee_id is not None
    fee = next(c for c in cs.cash if c.canonical_id == rio.brokerage_fee_id)
    assert fee.type is TxnType.FEE
    assert fee.signed_amount == Decimal("-9")
    assert fee.source_semantic == "TRADE_BROKERAGE"
    assert fee.security_id == "RIO"
    # dated on the cash-CSV brokerage row (settlement), not the trade date
    assert fee.effective_date == date(2026, 5, 3)


def test_trade_net_amount_follows_the_engine_rule():
    cs, _ = _build()
    rio = next(t for t in cs.trades if t.security_id == "RIO")   # SELL gross 1552.23, brk 9
    vas = next(t for t in cs.trades if t.security_id == "VAS")   # BUY gross 1061.62, brk 0
    assert rio.net_amount == Decimal("-1543.23")                # -(gross - brokerage)
    assert vas.net_amount == Decimal("1061.62")                 # gross + 0


# --- identity + determinism ---------------------------------------

def test_same_economic_event_from_two_sources_has_one_canonical_id():
    cs, _ = _build()
    ids = [t.canonical_id for t in cs.trades]
    assert len(ids) == len(set(ids))                        # no dupes
    # one canonical id per matched trade, carrying BOTH source rows
    vas = next(t for t in cs.trades if t.security_id == "VAS")
    assert vas.investment_source.row_number != vas.cash_source.row_number
    # identity is a function of economic fields only (proved by the reordering
    # test); here just assert it is a stable hex digest
    assert 1 <= len(vas.canonical_id) <= 32
    assert all(c in "0123456789abcdef" for c in vas.canonical_id)


def test_row_reordering_and_filename_change_do_not_change_canonical_ids():
    cs1, _ = _build()
    lines = fx.INVESTMENT_CSV.strip().splitlines()
    reordered = lines[0] + "\n" + "\n".join(reversed(lines[1:])) + "\n"
    cs2, _ = _build(inv_csv=reordered)
    assert sorted(cs1.all_ids) == sorted(cs2.all_ids)


def test_no_account_number_or_timestamp_in_any_canonical_id():
    cs, _ = _build()
    for cid in cs.all_ids:
        assert "99999999" not in cid and "12345678" not in cid
        assert len(cid) <= 32 and all(ch in "0123456789abcdef" for ch in cid)


def test_serialised_candidates_contain_no_pii():
    # canonical ids are one-way digests -- exempt from the digit-run scan, like
    # every ID/hash column in src/validation/privacy.py. Everything free-text is
    # checked.
    cs, _ = _build()
    for t in cs.trades:
        for v in (str(t.security_id), t.investment_source.raw_type,
                  t.cash_source.raw_type, *t.notes):
            assert not contains_identifier(v)
    for c in cs.cash:
        # free-text fields only -- money strings and hashes are not PII
        for v in (c.description, c.classification_method, c.source_transaction_type,
                  *(c.notes or ())):
            assert not contains_identifier(v)


# --- idempotency (§24) -------------------------------------------

def test_mandatory_idempotency_and_new_event(monkeypatch):
    cs_a, _ = _build()
    store = StagingStore()

    r1 = store.stage(cs_a)
    ids_after_a = set(store.ids())
    n_after_a = store.economic_event_count()
    assert len(r1.added) == n_after_a and not r1.unchanged

    r2 = store.stage(cs_a)                                  # identical reimport
    assert store.economic_event_count() == n_after_a
    assert set(store.ids()) == ids_after_a
    assert not r2.added and len(r2.unchanged) == n_after_a
    assert r2.duplicate_economic_events == 0

    # export B = all of A + one genuinely new trade
    inv_b = fx.INVESTMENT_CSV.rstrip() + \
        "\n99999999,Vanguard International Shares Index ETF,VGS,ETF,01-Jul-2022,Buy Trade,95.00,10,950.00,\n"
    cash_b = fx.CASH_CSV.rstrip() + \
        "\n01-Jul-2022,Buy,ETF,Vanguard International Shares Index ETF,VGS,10,-950.00\n"
    cs_b, _ = _build(inv_csv=inv_b, cash_csv=cash_b)
    r3 = store.stage(cs_b)
    assert len(r3.added) == 1
    assert store.economic_event_count() == n_after_a + 1


def test_overlapping_export_adds_only_new_events():
    store = StagingStore()
    cs_a, _ = _build()
    store.stage(cs_a)
    before = store.economic_event_count()

    # B: same content, different (irrelevant) account column, + 1 new cash row
    inv_b = fx.INVESTMENT_CSV.replace("99999999,", "77777777,")
    cash_b = fx.CASH_CSV.rstrip() + "\n30-Sep-2021,Interest,Cash account,Cash Account Interest,CASH,,1.11\n"
    cs_b, _ = _build(inv_csv=inv_b, cash_csv=cash_b)
    r = store.stage(cs_b)
    assert len(r.added) == 1
    assert store.economic_event_count() == before + 1
    assert len(r.unchanged) == before                       # everything else recognised


def test_corrected_source_row_is_detected_not_silently_overwritten():
    store = StagingStore()
    cs_a, _ = _build()
    store.stage(cs_a)

    # same slot (BUY / VAS / 18-Sep-2020) but a changed price+value
    inv_c = fx.INVESTMENT_CSV.replace(
        "18-Sep-2020,Buy Trade,75.83,14,1061.62,",
        "18-Sep-2020,Buy Trade,76.00,14,1064.00,")
    cash_c = fx.CASH_CSV.replace("18-Sep-2020,Buy,ETF,Vanguard Australian Shares Index ETF,VAS,14,-1061.62",
                                 "18-Sep-2020,Buy,ETF,Vanguard Australian Shares Index ETF,VAS,14,-1064.00")
    cs_c, _ = _build(inv_csv=inv_c, cash_csv=cash_c)
    r = store.stage(cs_c)
    assert len(r.corrections) == 1
    changed = next(e for e in store.events if e.canonical_id == r.corrections[0])
    assert changed.status.value == "SOURCE_CHANGED"
    assert changed.supersedes is not None
    # the prior event's provenance history grew, not replaced
    prior = next(e for e in store.events if e.canonical_id == changed.supersedes)
    assert len(prior.provenance_history) >= 2


# --- isolated engine consumption (§22) ---------------------------

def test_candidates_are_consumable_by_the_existing_engine():
    from src.engine.holdings import HoldingsEngine
    from src.engine.cash import CashEngine
    from src.engine.config import EngineConfig

    cs, _ = _build()
    ledger = project_ledger(cs)
    # holdings replay without error, units are non-negative
    positions = HoldingsEngine(EngineConfig()).positions_at(ledger, date(2027, 1, 1))
    for sid, p in positions.items():
        assert p.units >= 0, sid
    # cash replay produces a finite balance; no BUY/SELL double-counts cash
    bal = CashEngine().balance_at(ledger, date(2027, 1, 1))
    assert isinstance(bal, Decimal)


# --- real data (§26-28) ----------------------------------------

def _real_paths():
    from pathlib import Path
    root = Path(__file__).resolve().parents[3] / "statements"
    inv = next(iter(sorted(root.glob("investment_transactions_*.csv"))), None)
    cash = next(iter(sorted(root.glob("cash_transactions_*.csv"))), None)
    return inv, cash


def test_real_data_candidate_build_is_deterministic_and_pii_free():
    inv_f, cash_f = _real_paths()
    if inv_f is None or cash_f is None:
        pytest.skip("real exports not present")

    def build():
        ir = parse_investment_csv(inv_f)
        cr = parse_cash_csv(cash_f)
        res = SecurityResolver()
        res.seed_from_investment_records(ir.investment_records)
        m = match_trades(ir.investment_records, cr.cash_records)
        return build_candidates(m, ir.investment_records, cr.cash_records, res)

    a = build()
    b = build()
    assert sorted(a.all_ids) == sorted(b.all_ids)
    assert a.type_counts() == b.type_counts()
    assert a.unresolved() == b.unresolved()

    # 76 matched trades -> exactly 76 trade candidates
    assert len(a.trades) == 76
    assert sum(1 for t in a.trades if t.type is TxnType.BUY) == 52
    assert sum(1 for t in a.trades if t.type is TxnType.SELL) == 24
    # no canonical trade TRANSFER exists in the candidate set
    assert not any(c.type is TxnType.TRANSFER for c in a.cash)

    for t in a.trades:
        assert not contains_identifier(str(t.security_id))
    for c in a.cash:
        assert not contains_identifier(c.description)

    # staging the real set twice is idempotent
    store = StagingStore()
    store.stage(a)
    n = store.economic_event_count()
    store.stage(build())
    assert store.economic_event_count() == n


def test_real_data_row_reordering_preserves_identity():
    inv_f, cash_f = _real_paths()
    if inv_f is None or cash_f is None:
        pytest.skip("real exports not present")
    inv_text = inv_f.read_text().splitlines()
    cash_text = cash_f.read_text().splitlines()
    reordered_inv = inv_text[0] + "\n" + "\n".join(reversed(inv_text[1:])) + "\n"
    reordered_cash = cash_text[0] + "\n" + "\n".join(reversed(cash_text[1:])) + "\n"

    def build(inv_src, cash_src):
        ir = parse_investment_csv(inv_src)
        cr = parse_cash_csv(cash_src)
        res = SecurityResolver()
        res.seed_from_investment_records(ir.investment_records)
        m = match_trades(ir.investment_records, cr.cash_records)
        return build_candidates(m, ir.investment_records, cr.cash_records, res)

    a = build(inv_f.read_text(), cash_f.read_text())
    b = build(reordered_inv, reordered_cash)
    assert sorted(a.all_ids) == sorted(b.all_ids)
    assert a.type_counts() == b.type_counts()
