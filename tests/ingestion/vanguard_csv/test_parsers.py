"""Step 9B, Stage 1 -- privacy-safe CSV parsers.

Acceptance gate coverage: every source row accounted for, no silent drops, no
PII in parser output, blank-brokerage rule, signed-quantity behaviour,
distribution-by-name behaviour.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.ingestion.vanguard_csv.cash import parse_cash_csv
from src.ingestion.vanguard_csv.investment import SchemaError, parse_investment_csv
from src.ingestion.vanguard_csv.records import (
    BrokerageSourceStatus, CashClass, SourceKind, TradeSide,
)
from src.ingestion.vanguard_csv.sanitise import contains_identifier, redact
from tests.fixtures import vanguard_csv as fx


# --- sanitisation ---------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("One-off Cash Withdrawal to 99999999 on 05-May-2026",
     "One-off Cash Withdrawal to ######## on 05-May-2026"),
    ("Off-System BSB Direct Entry Deposit - 12345678",
     "Off-System BSB Direct Entry Deposit - ########"),
    ("VAS trade of 14 units", "VAS trade of 14 units"),          # 2-digit run kept
    ("Paid on 5-Jul-21", "Paid on 5-Jul-21"),                     # short date kept
    ("ref 001234 and 12-Jan-2024", "ref ###### and 12-Jan-2024"), # digits redacted, date kept
])
def test_redact(raw, expected):
    assert redact(raw) == expected


def test_contains_identifier_detects_unredacted_digits():
    assert contains_identifier("account 12345678")
    assert not contains_identifier("account ########")
    assert not contains_identifier("settled 12-Jan-2024")


@pytest.mark.parametrize("raw,expected", [
    ("Off-System BSB Direct Entry Deposit - demobank", "Off-System BSB Direct Entry Deposit"),
    ("Off-System BSB Direct Entry Deposit - XJQ", "Off-System BSB Direct Entry Deposit"),
    ("Off-System BSB Direct Entry Deposit - From 12345678", "Off-System BSB Direct Entry Deposit"),
    ("Deposit for investment purchases", "Deposit for investment purchases"),   # no clause, unchanged
    ("Failed Direct Debit", "Failed Direct Debit"),
])
def test_strip_deposit_source(raw, expected):
    from src.ingestion.vanguard_csv.sanitise import strip_deposit_source
    assert strip_deposit_source(raw) == expected


# --- investment CSV ------------------------------------------------------

def test_investment_parses_all_rows_and_accounts_for_them():
    r = parse_investment_csv(fx.INVESTMENT_CSV)
    assert r.rows_in == 4
    assert len(r.investment_records) == 4
    assert not r.quarantined
    r.assert_all_rows_accounted()


def test_investment_account_number_column_is_dropped():
    r = parse_investment_csv(fx.INVESTMENT_CSV)
    for rec in r.investment_records:
        assert "Account number" not in rec.sanitised_cells
        assert not any(k.lower().startswith("account") for k in rec.sanitised_cells)


def test_investment_no_pii_survives_in_any_field():
    r = parse_investment_csv(fx.INVESTMENT_CSV)
    for rec in r.investment_records:
        for v in rec.sanitised_cells.values():
            assert not contains_identifier(v)
        assert not contains_identifier(rec.security_name)


def test_investment_signed_quantity_normalised_to_side_and_unsigned_units():
    r = parse_investment_csv(fx.INVESTMENT_CSV)
    buy = next(x for x in r.investment_records if x.product_id == "VAS")
    sell = next(x for x in r.investment_records if x.product_id == "RIO")
    assert buy.side is TradeSide.BUY and buy.raw_quantity == Decimal("14")
    assert buy.canonical_units == Decimal("14")
    assert sell.side is TradeSide.SELL and sell.raw_quantity == Decimal("-9")
    assert sell.canonical_units == Decimal("9")   # unsigned


def test_investment_blank_brokerage_becomes_canonical_zero_with_status():
    r = parse_investment_csv(fx.INVESTMENT_CSV)
    blank = next(x for x in r.investment_records if x.product_id == "VAS")
    assert blank.raw_brokerage is None                       # raw preserved, not rewritten to "0"
    assert blank.canonical_brokerage == Decimal("0.00")
    assert blank.brokerage_source_status is BrokerageSourceStatus.SOURCE_BLANK_INTERPRETED_AS_ZERO


def test_investment_explicit_brokerage_kept_verbatim():
    r = parse_investment_csv(fx.INVESTMENT_CSV)
    brk = next(x for x in r.investment_records if x.product_id == "BHP")
    assert brk.raw_brokerage == Decimal("9")
    assert brk.canonical_brokerage == Decimal("9")
    assert brk.brokerage_source_status is BrokerageSourceStatus.SOURCE_VALUE


def test_investment_blank_brokerage_review_mode_flags_instead_of_zeroing():
    r = parse_investment_csv(fx.INVESTMENT_CSV, review_blank_brokerage=True)
    blank = next(x for x in r.investment_records if x.product_id == "VAS")
    assert blank.raw_brokerage is None
    assert blank.brokerage_source_status is BrokerageSourceStatus.SOURCE_BLANK_NEEDS_REVIEW
    assert any("flagged for review" in w for w in r.warnings)


def test_investment_bad_arithmetic_warns_but_keeps_the_row():
    r = parse_investment_csv(fx.INVESTMENT_CSV_BAD_ARITHMETIC)
    assert len(r.investment_records) == 1
    assert any("Unit Price" in w for w in r.warnings)


def test_investment_malformed_rows_quarantined_never_dropped():
    r = parse_investment_csv(fx.INVESTMENT_CSV_MALFORMED)
    assert r.rows_in == 5
    assert len(r.investment_records) == 1                    # only the good row
    assert {q.reason_code for q in r.quarantined} == {
        "UNKNOWN_TRADE_TYPE", "BAD_TRADE_DATE", "ZERO_QUANTITY", "SIGN_MISMATCH"}
    r.assert_all_rows_accounted()


def test_investment_missing_column_is_a_hard_schema_error():
    with pytest.raises(SchemaError):
        parse_investment_csv("Investment,Product ID,Trade Date\nVAS,VAS,18-Sep-2020\n")


# --- cash CSV ----------------------------------------------------------------

def test_cash_parses_all_rows_and_accounts_for_them():
    r = parse_cash_csv(fx.CASH_CSV)
    assert r.rows_in == len(fx.CASH_ROWS)
    assert len(r.cash_records) == len(fx.CASH_ROWS)
    assert not r.quarantined
    r.assert_all_rows_accounted()


def test_fees_and_charges_rows_split_by_description():
    r = parse_cash_csv(fx.CASH_CSV)
    fees = {rec.product_name: rec.cash_class
            for rec in r.cash_records if rec.raw_type == "Fees and Charges"}
    assert fees["OngoingAdminChargeByValue"] is CashClass.ADMIN_FEE
    assert fees["Reversal: OngoingAdminChargeByValue"] is CashClass.FEE_REVERSAL
    assert fees["Australian Equity Transaction fee for Rio Tinto Limited Sell"] \
        is CashClass.TRADE_BROKERAGE_CASH


def test_cash_descriptions_are_redacted_before_records_exist():
    r = parse_cash_csv(fx.CASH_CSV)
    deposits = [x for x in r.cash_records if x.cash_class is CashClass.DEPOSIT]
    wd = next(x for x in r.cash_records if x.cash_class is CashClass.WITHDRAWAL)
    # Deposit rows: the whole trailing source clause (digits OR a bank name/
    # initials) is dropped, not merely digit-redacted -- see
    # test_deposit_bank_name_and_initials_are_stripped_not_just_redacted.
    for dep in deposits:
        assert "12345678" not in dep.product_name
        assert " - " not in dep.product_name
    assert "99999999" not in wd.product_name and "########" in wd.product_name
    # the date inside the withdrawal description is preserved
    assert "05-May-2026" in wd.product_name
    for rec in r.cash_records:
        for v in rec.sanitised_cells.values():
            assert not contains_identifier(v)


def test_deposit_bank_name_and_initials_are_stripped_not_just_redacted():
    # "demobank" and "XJQ" are alphabetic -- redact()'s digit-only rule would
    # leave them exposed. Deposit rows get the whole trailing clause dropped.
    r = parse_cash_csv(fx.CASH_CSV)
    deposits = {x.product_name for x in r.cash_records if x.cash_class is CashClass.DEPOSIT}
    for name in deposits:
        assert "demobank" not in name.lower()
        assert "xjq" not in name.lower()
    assert "Off-System BSB Direct Entry Deposit" in deposits   # the safe prefix survives


def test_cash_type_vocabulary_maps_to_normalised_classes():
    r = parse_cash_csv(fx.CASH_CSV)
    got = {rec.raw_type: rec.cash_class for rec in r.cash_records
           if rec.raw_type != "Fees and Charges"}
    assert got["Deposit"] is CashClass.DEPOSIT
    assert got["Withdrawal"] is CashClass.WITHDRAWAL
    assert got["Interest"] is CashClass.INTEREST
    assert got["Distribution"] is CashClass.DISTRIBUTION_INCOME
    assert got["Buy"] is CashClass.TRADE_BUY_CASH
    assert got["Sell"] is CashClass.TRADE_SELL_CASH


def test_cash_distribution_with_blank_product_id_keeps_the_security_name():
    r = parse_cash_csv(fx.CASH_CSV)
    dist = [x for x in r.cash_records if x.cash_class is CashClass.DISTRIBUTION_INCOME]
    by_name = next(x for x in dist if x.product_id is None)
    assert by_name.product_name == "Vanguard Australian Shares Index ETF"
    assert by_name.signed_total == Decimal("120.50")


def test_cash_signed_total_kept_verbatim():
    r = parse_cash_csv(fx.CASH_CSV)
    dep = next(x for x in r.cash_records if x.cash_class is CashClass.DEPOSIT)
    fee = next(x for x in r.cash_records
              if x.cash_class is CashClass.ADMIN_FEE and x.product_name == "OngoingAdminChargeByValue"
              and x.signed_total == Decimal("-0.28"))
    assert dep.signed_total == Decimal("10000")
    assert fee.signed_total == Decimal("-0.28")


def test_cash_sign_anomaly_warns_but_keeps_the_row():
    r = parse_cash_csv(fx.CASH_CSV_SIGN_ANOMALY)
    assert len(r.cash_records) == 1
    assert any("expected debit" in w for w in r.warnings)


def test_cash_malformed_rows_quarantined_never_dropped():
    r = parse_cash_csv(fx.CASH_CSV_MALFORMED)
    assert r.rows_in == 4
    assert len(r.cash_records) == 1
    assert {q.reason_code for q in r.quarantined} == {
        "UNKNOWN_CASH_TYPE", "BAD_DATE", "BAD_TOTAL"}
    r.assert_all_rows_accounted()


# --- file identity is content-based, not filename-based ------------------

def test_file_hash_is_stable_and_ignores_the_account_column():
    a = parse_investment_csv(fx.INVESTMENT_CSV)
    # same economic content, different account number in the dropped column
    swapped = fx.INVESTMENT_CSV.replace("99999999,", "11111111,")
    b = parse_investment_csv(swapped)
    assert a.sanitised_file_sha256 == b.sanitised_file_sha256
