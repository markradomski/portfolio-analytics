"""Step 9B -- guarded smoke test against the real Vanguard exports.

Skipped automatically when the exports are not present (they live under the
git-ignored `statements/` and are never copied into fixtures). Asserts only
sanitised aggregates and the privacy invariant -- never prints or asserts any
account-identifying value.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.vanguard_csv.cash import parse_cash_csv
from src.ingestion.vanguard_csv.investment import parse_investment_csv
from src.ingestion.vanguard_csv.sanitise import contains_identifier

_STATEMENTS = Path(__file__).resolve().parents[3] / "statements"


def _find(glob: str) -> Path | None:
    return next(iter(sorted(_STATEMENTS.glob(glob))), None)


@pytest.fixture
def investment_csv() -> Path:
    p = _find("investment_transactions_*.csv")
    if p is None:
        pytest.skip("real investment transactions CSV not present")
    return p


@pytest.fixture
def cash_csv() -> Path:
    p = _find("cash_transactions_*.csv")
    if p is None:
        pytest.skip("real cash transactions CSV not present")
    return p


def test_real_investment_csv_every_row_accounted_for(investment_csv):
    r = parse_investment_csv(investment_csv)
    r.assert_all_rows_accounted()
    assert r.rows_in > 0
    assert not r.quarantined, [q.reason_code for q in r.quarantined]


def test_real_cash_csv_every_row_accounted_for(cash_csv):
    r = parse_cash_csv(cash_csv)
    r.assert_all_rows_accounted()
    assert r.rows_in > 0
    assert not r.quarantined, [q.reason_code for q in r.quarantined]


def test_real_exports_leak_no_identifier(investment_csv, cash_csv):
    inv = parse_investment_csv(investment_csv)
    cash = parse_cash_csv(cash_csv)
    leaks = 0
    for rec in inv.investment_records:
        leaks += sum(contains_identifier(v) for v in rec.sanitised_cells.values())
        leaks += contains_identifier(rec.security_name)
    for rec in cash.cash_records:
        leaks += sum(contains_identifier(v) for v in rec.sanitised_cells.values())
        leaks += contains_identifier(rec.product_name)
    for q in (*inv.quarantined, *cash.quarantined):
        leaks += sum(contains_identifier(v) for v in q.sanitised_cells.values())
    assert leaks == 0


def test_real_deposit_descriptions_carry_no_bank_name_or_initials(cash_csv):
    # contains_identifier() only catches digit runs; a bank name or the
    # investor's own initials is alphabetic and was found in this real
    # export -- assert the dedicated Deposit-clause stripping catches it.
    from src.ingestion.vanguard_csv.records import CashClass
    cash = parse_cash_csv(cash_csv)
    for rec in cash.cash_records:
        if rec.cash_class is CashClass.DEPOSIT:
            assert " - " not in rec.product_name, rec.product_name
