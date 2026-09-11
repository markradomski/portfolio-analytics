import pytest

from src.models import SecurityType, TxnType
from src.normalisation.transactions import (classify_cash, classify_trade,
                                            income_type_for, is_balance_marker)


@pytest.mark.parametrize("description,expected", [
    ("Account Fee", TxnType.FEE),
    ("Australian Equity Transaction fee for BHP Billiton Limited Sell", TxnType.FEE),
    ("Reversal: OngoingAdminChargeByValue", TxnType.FEE),
    ("DIV: VAS.XASX.AU @ AUD 0.8479", TxnType.DISTRIBUTION),
    ("Cash Account Interest", TxnType.INTEREST),
    ("Off-System BSB Direct Entry Deposit - [redacted]", TxnType.DEPOSIT),
    ("Failed Direct Debit", TxnType.DEPOSIT),
    ("One-off Cash Withdrawal to [redacted] on 29-Apr-2024", TxnType.WITHDRAWAL),
    ("Buy transaction of VAS", TxnType.TRANSFER),
    ("Withholding tax", TxnType.TAX),
])
def test_classifies_cash_descriptions(description, expected):
    assert classify_cash(description) is expected


def test_fee_rules_win_over_trade_rules():
    """'Transaction fee for X Sell' contains both patterns; it is a fee."""
    assert classify_cash("Transaction fee for Rio Tinto Limited Sell") is TxnType.FEE


def test_unknown_descriptions_are_flagged_not_guessed():
    assert classify_cash("Something entirely new") is TxnType.OTHER


def test_balance_markers_are_not_transactions():
    assert is_balance_marker("Opening balance")
    assert is_balance_marker("Closing balance")
    assert not is_balance_marker("Account Fee")


def test_trade_side_comes_from_quantity_sign():
    assert classify_trade(-1, "Sold X") is TxnType.SELL
    assert classify_trade(1, "Bought X") is TxnType.BUY
    assert classify_trade(0, "Sold X") is TxnType.SELL


def test_funds_distribute_and_companies_pay_dividends():
    assert income_type_for(SecurityType.ETF) is TxnType.DISTRIBUTION
    assert income_type_for(SecurityType.MANAGED_FUND) is TxnType.DISTRIBUTION
    assert income_type_for(SecurityType.SHARE) is TxnType.DIVIDEND
