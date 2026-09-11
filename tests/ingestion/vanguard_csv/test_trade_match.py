"""Step 9B, Stage 2 -- deterministic cross-file BUY/SELL matching."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.ingestion.vanguard_csv.cash import parse_cash_csv
from src.ingestion.vanguard_csv.investment import parse_investment_csv
from src.ingestion.vanguard_csv.records import (
    BrokerageSourceStatus, CashClass, CashSourceRecord, InvestmentSourceRecord,
    SourceKind, SourceLocation, TradeSide,
)
from src.ingestion.vanguard_csv.sanitise import contains_identifier
from src.ingestion.vanguard_csv.trade_match import (
    DateRelation, MatchStatus, match_trades,
)


def inv(row, *, side=TradeSide.BUY, pid="VAS", d=date(2020, 9, 18),
        units=Decimal("14"), price=Decimal("75.83"), value=Decimal("1061.62"),
        raw_brk=None, canon_brk=Decimal("0.00"),
        status=BrokerageSourceStatus.SOURCE_BLANK_INTERPRETED_AS_ZERO, name="VAS ETF"):
    raw_qty = units if side is TradeSide.BUY else -units
    return InvestmentSourceRecord(
        security_name=name, product_id=pid, product_type="ETF", trade_date=d,
        raw_type="Buy Trade" if side is TradeSide.BUY else "Sell trade", side=side,
        raw_quantity=raw_qty, canonical_units=units, unit_price=price, gross_value=value,
        raw_brokerage=raw_brk, canonical_brokerage=canon_brk, brokerage_source_status=status,
        location=SourceLocation(SourceKind.INVESTMENT_TXN_CSV, "invhash", row),
        sanitised_cells={},
    )


def cash(row, *, cls=CashClass.TRADE_BUY_CASH, pid="VAS", d=date(2020, 9, 18),
         total=Decimal("-1061.62"), units=Decimal("14"), name="VAS ETF"):
    return CashSourceRecord(
        date=d, raw_type="Buy", cash_class=cls, product_name=name, product_id=pid,
        units=units, signed_total=total,
        location=SourceLocation(SourceKind.CASH_TXN_CSV, "cashhash", row),
        sanitised_cells={},
    )


# --- exact matches -------------------------------------------------------

def test_exact_buy_match():
    r = match_trades([inv(1)], [cash(1)])
    r.assert_all_trade_rows_accounted()
    r.assert_one_to_one()
    assert [c.status for c in r.candidates] == [MatchStatus.MATCH]
    c = r.candidates[0]
    assert c.side is TradeSide.BUY and c.date_relation is DateRelation.SAME_DAY
    assert "gross_value_exact" in c.match_reasons
    assert "brokerage_excluded_from_match_amount" in c.match_reasons
    assert r.is_clean()


def test_exact_sell_match_sign_relationship():
    # SELL: investment Value +1552.23 gross, cash Total +1552.23 (credit)
    r = match_trades(
        [inv(1, side=TradeSide.SELL, pid="RIO", d=date(2026, 5, 1),
             units=Decimal("9"), price=Decimal("172.47"), value=Decimal("1552.23"))],
        [cash(1, cls=CashClass.TRADE_SELL_CASH, pid="RIO", d=date(2026, 5, 1),
              total=Decimal("1552.23"), units=Decimal("-9"))],
    )
    assert r.candidates[0].status is MatchStatus.MATCH
    assert r.candidates[0].raw_quantity == Decimal("-9")           # raw signed preserved
    assert r.candidates[0].canonical_units_candidate == Decimal("9")


def test_brokerage_excluded_from_the_match_amount():
    # $9 brokerage on the investment side; cash Total is the *gross* value, no +/- 9.
    r = match_trades(
        [inv(1, side=TradeSide.SELL, pid="BHP", value=Decimal("1213.85"),
             raw_brk=Decimal("9"), canon_brk=Decimal("9"),
             status=BrokerageSourceStatus.SOURCE_VALUE, units=Decimal("22"))],
        [cash(1, cls=CashClass.TRADE_SELL_CASH, pid="BHP",
              total=Decimal("1213.85"), units=Decimal("-22"))],
    )
    c = r.candidates[0]
    assert c.status is MatchStatus.MATCH               # gross==gross, brokerage ignored
    assert c.raw_brokerage == Decimal("9")             # still available for Stage 3
    assert c.canonical_brokerage == Decimal("9")
    assert c.brokerage_source_status == "SOURCE_VALUE"
    # A matcher that added brokerage would have looked for |total| == 1204.85 or 1222.85.


def test_blank_brokerage_provenance_survives_the_match():
    r = match_trades([inv(1)], [cash(1)])
    c = r.candidates[0]
    assert c.raw_brokerage is None
    assert c.canonical_brokerage == Decimal("0.00")
    assert c.brokerage_source_status == "SOURCE_BLANK_INTERPRETED_AS_ZERO"


# --- date semantics -----------------------------------------------------

def test_same_day_and_nonzero_delta_are_classified():
    same = match_trades([inv(1)], [cash(1)])
    assert same.candidates[0].date_relation is DateRelation.SAME_DAY
    assert same.candidates[0].status is MatchStatus.MATCH

    plus1 = match_trades([inv(1)], [cash(1, d=date(2020, 9, 19))])
    c = plus1.candidates[0]
    assert c.date_delta_days == 1 and c.date_relation is DateRelation.NEXT_DAY
    assert c.status is MatchStatus.MATCH_WITH_MINOR_DIFFERENCE


# --- mismatches -------------------------------------------------------

def test_product_id_mismatch_is_not_matched():
    r = match_trades([inv(1, pid="VAS")], [cash(1, pid="VGS", name="VGS ETF")])
    assert r.candidates[0].status is MatchStatus.UNMATCHED_INVESTMENT
    assert r.by_status(MatchStatus.UNMATCHED_CASH)          # the cash row is surfaced too


def test_security_name_confirms_when_cash_lacks_product_id():
    r = match_trades([inv(1, pid="VAS", name="Vanguard Australian Shares Index ETF")],
                     [cash(1, pid=None, name="Vanguard Australian Shares Index ETF")])
    assert r.candidates[0].status is MatchStatus.MATCH
    assert "security_name_confirmed" in r.candidates[0].match_reasons


def test_value_mismatch_beyond_tolerance_is_unmatched():
    r = match_trades([inv(1, value=Decimal("1061.62"))],
                     [cash(1, total=Decimal("-2000.00"))])
    assert r.candidates[0].status is MatchStatus.UNMATCHED_INVESTMENT


def test_quantity_mismatch_flagged_when_both_sides_have_quantity():
    r = match_trades([inv(1, units=Decimal("14"))],
                     [cash(1, units=Decimal("99"))])   # value still matches
    assert r.candidates[0].status is MatchStatus.QUANTITY_MISMATCH
    assert not r.is_clean()


def test_unmatched_investment_and_unmatched_cash():
    r = match_trades([inv(1, d=date(2019, 1, 1))], [cash(1, d=date(2022, 1, 1))])
    statuses = {c.status for c in r.candidates}
    assert MatchStatus.UNMATCHED_INVESTMENT in statuses
    assert MatchStatus.UNMATCHED_CASH in statuses
    assert not r.is_clean()


# --- ambiguity + one-to-one -------------------------------------------

def test_ambiguous_when_two_cash_rows_equally_match():
    r = match_trades([inv(1)], [cash(1), cash(2)])
    assert r.candidates[0].status is MatchStatus.AMBIGUOUS
    assert "2_equally_plausible_cash_rows" in r.candidates[0].match_reasons
    assert not r.is_clean()


def test_ambiguous_when_two_investment_rows_want_one_cash_row():
    r = match_trades([inv(1), inv(2)], [cash(1)])
    assert [c.status for c in r.candidates if c.investment_row != -1] == [
        MatchStatus.AMBIGUOUS, MatchStatus.AMBIGUOUS]
    assert not r.is_clean()


def test_one_to_one_enforced_on_a_clean_multi_trade_set():
    invs = [inv(1, d=date(2020, 1, 1)), inv(2, d=date(2021, 1, 1)), inv(3, d=date(2022, 1, 1))]
    cashes = [cash(1, d=date(2020, 1, 1)), cash(2, d=date(2021, 1, 1)), cash(3, d=date(2022, 1, 1))]
    r = match_trades(invs, cashes)
    r.assert_one_to_one()
    assert len(r.matched) == 3 and r.is_clean()


def test_genuinely_distinct_identical_same_day_trades_both_match():
    invs = [inv(1), inv(2)]
    cashes = [cash(1), cash(2)]
    r = match_trades(invs, cashes)
    # two identical BUYs, two identical cash legs -> both AMBIGUOUS (the source
    # gives no way to tell which leg belongs to which order). The gate then
    # correctly refuses promotion.
    assert all(c.status is MatchStatus.AMBIGUOUS for c in r.candidates if c.investment_row != -1)


# --- determinism -------------------------------------------------------

def test_match_identity_is_deterministic():
    a = match_trades([inv(1)], [cash(1)])
    b = match_trades([inv(1)], [cash(1)])
    assert a.candidates[0].match_id == b.candidates[0].match_id


def test_source_row_reordering_does_not_change_the_result():
    invs = [inv(1, d=date(2020, 1, 1)), inv(2, d=date(2021, 6, 1), pid="VGS", name="VGS"),
            inv(3, d=date(2022, 3, 1), pid="VAF", name="VAF")]
    cashes = [cash(10, d=date(2020, 1, 1)),
              cash(20, d=date(2021, 6, 1), pid="VGS", name="VGS"),
              cash(30, d=date(2022, 3, 1), pid="VAF", name="VAF")]

    forward = match_trades(invs, cashes)
    reverse = match_trades(list(reversed(invs)), list(reversed(cashes)))

    def sig(res):
        return sorted((c.status.value, c.security_id, str(c.investment_trade_date),
                       c.match_id) for c in res.candidates)
    assert sig(forward) == sig(reverse)


# --- privacy ----------------------------------------------------------

def test_match_diagnostics_carry_no_identifier():
    # A security name that (impossibly) still held an identifier: the matcher's
    # own diagnostics must not echo it. `match_id` is a one-way sha256 digest of
    # sanitised economic fields -- not free text -- so it is exempt from the
    # digit-run check (a hash can hold incidental digit runs), like every other
    # ID/hash column in src/validation/privacy.py.
    dirty_name = "Withdrawal to 99999999"
    r = match_trades([inv(1, name=dirty_name)], [cash(1, name=dirty_name)])
    for c in r.candidates:
        for reason in c.match_reasons:
            assert not contains_identifier(reason)
        for v in c.reconciliation_deltas.values():
            assert not contains_identifier(v)
        assert len(c.match_id) == 16 and all(ch in "0123456789abcdef" for ch in c.match_id)


# --- real data --------------------------------------------------------

def test_real_data_matches_are_clean_and_one_to_one():
    from pathlib import Path
    import pytest
    root = Path(__file__).resolve().parents[3] / "statements"
    inv_f = next(iter(sorted(root.glob("investment_transactions_*.csv"))), None)
    cash_f = next(iter(sorted(root.glob("cash_transactions_*.csv"))), None)
    if inv_f is None or cash_f is None:
        pytest.skip("real exports not present")

    ir = parse_investment_csv(inv_f)
    cr = parse_cash_csv(cash_f)
    result = match_trades(ir.investment_records, cr.cash_records)

    result.assert_all_trade_rows_accounted()
    result.assert_one_to_one()
    assert result.is_clean(), result.counts()
    assert len(result.matched) == len(ir.investment_records)
    for c in result.matched:
        # provenance from both files
        assert c.investment_file_sha256 != "-" and c.cash_file_sha256 is not None
        # no identifier in any free-text diagnostic (match_id is a hash -- exempt)
        for reason in c.match_reasons:
            assert not contains_identifier(reason)
        for v in c.reconciliation_deltas.values():
            assert not contains_identifier(v)
