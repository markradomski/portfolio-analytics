from datetime import date
from decimal import Decimal

from src.ingestion.statement_parser import parse_document
from src.models import DocumentKind, Severity, TxnType


def _by_type(parsed, txn_type):
    return [t for t in parsed.transactions if t.type is txn_type]


def test_classifies_and_dates_the_document(statement_pdf):
    parsed = parse_document(statement_pdf)
    assert parsed.document.kind is DocumentKind.QUARTERLY
    assert parsed.document.period_start == date(2024, 7, 1)
    assert parsed.document.period_end == date(2024, 9, 30)


def test_reads_holdings_whose_product_name_wraps(statement_pdf):
    parsed = parse_document(statement_pdf)
    assert len(parsed.holdings) == 1
    holding = parsed.holdings[0]
    assert holding.units == Decimal("15.00")
    assert holding.price == Decimal("100.000")
    assert holding.market_value == Decimal("1500.00")
    assert holding.reporting_date == date(2024, 9, 30)


def test_reads_trades_including_unsettled_ones(statement_pdf):
    parsed = parse_document(statement_pdf)
    buys = _by_type(parsed, TxnType.BUY)
    assert len(buys) == 2
    assert sum(b.units for b in buys) == Decimal("15.00")
    unsettled = [b for b in buys if b.settlement_date is None]
    assert len(unsettled) == 1
    assert unsettled[0].trade_date == date(2024, 9, 28)


def test_distribution_amount_is_not_the_per_unit_rate(statement_pdf):
    """The rate precedes the amount on a DIV row; taking the wrong one
    understates income by orders of magnitude."""
    parsed = parse_document(statement_pdf)
    assert len(parsed.income) == 1
    event = parsed.income[0]
    assert event.amount == Decimal("20.00")
    assert event.rate_per_unit == Decimal("2.0000")


def test_reads_cash_rows_whose_description_wraps(statement_pdf):
    parsed = parse_document(statement_pdf)
    deposits = _by_type(parsed, TxnType.DEPOSIT)
    withdrawals = _by_type(parsed, TxnType.WITHDRAWAL)
    assert [d.net_amount for d in deposits] == [Decimal("500.00")]
    assert [w.net_amount for w in withdrawals] == [Decimal("-200.00")]


def test_direction_is_inferred_from_the_running_balance(statement_pdf):
    parsed = parse_document(statement_pdf)
    fees = _by_type(parsed, TxnType.FEE)
    assert all(f.net_amount < 0 for f in fees)
    assert sum(f.net_amount for f in fees) == Decimal("-30.00")


def test_captures_valuation_including_accrued_income(statement_pdf):
    parsed = parse_document(statement_pdf)
    valuation = parsed.valuations[0]
    assert valuation.portfolio_value == Decimal("1910.00")
    assert valuation.cash_balance == Decimal("390.00")
    assert valuation.accrued_income == Decimal("20.00")


def test_period_summary_balances(statement_pdf):
    parsed = parse_document(statement_pdf)
    period = parsed.periods[0]
    computed = (period.opening_value + period.deposits + period.withdrawals
                + period.change_in_value + period.income - period.fees)
    assert computed == period.closing_value


def test_clean_statement_raises_no_issues(statement_pdf):
    parsed = parse_document(statement_pdf)
    assert [i for i in parsed.issues if i.severity is not Severity.INFO] == []


def test_malformed_rows_are_flagged_not_invented(tmp_path):
    from tests.fixtures import synthetic
    from tests.fixtures.pdf_builder import build_pdf

    path = build_pdf(tmp_path / "broken.pdf", synthetic.MALFORMED)
    parsed = parse_document(path)          # must not raise
    assert parsed.holdings == []
    assert parsed.transactions == []
