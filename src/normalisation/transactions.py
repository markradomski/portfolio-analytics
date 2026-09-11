"""Map statement prose onto the controlled transaction vocabulary.

Cash-account descriptions are free text, so classification is by ordered
pattern match: the first rule that matches wins, and anything unmatched becomes
OTHER and is flagged for review rather than guessed at.
"""

from __future__ import annotations

import re

from src.models import SecurityType, TxnType

# Ordered: earlier patterns win. Fee rules precede the trade-settlement rules
# because "Australian Equity Transaction fee for X Sell" contains both.
_CASH_RULES: list[tuple[re.Pattern[str], TxnType]] = [
    (re.compile(r"\b(opening|closing) balance\b", re.I), TxnType.OTHER),
    (re.compile(r"transaction fee|account fee|brokerage|admin\s*charge"
                r"|adminchargebyvalue", re.I), TxnType.FEE),
    (re.compile(r"withholding tax|tax withheld", re.I), TxnType.TAX),
    (re.compile(r"^\s*DIV\s*:", re.I), TxnType.DISTRIBUTION),
    (re.compile(r"\bdistribution\b", re.I), TxnType.DISTRIBUTION),
    (re.compile(r"\bdividend\b", re.I), TxnType.DIVIDEND),
    (re.compile(r"\binterest\b", re.I), TxnType.INTEREST),
    # A reversed deposit. Signed negative, so it cancels the original credit.
    (re.compile(r"failed direct debit|dishonour", re.I), TxnType.DEPOSIT),
    (re.compile(r"\bwithdrawal\b|\bpayment to\b", re.I), TxnType.WITHDRAWAL),
    (re.compile(r"\bdeposit\b|\bcontribution\b|\bfunds received\b", re.I), TxnType.DEPOSIT),
    # Cash leg of a settled trade. The BUY/SELL itself is captured from the
    # investment transaction table, so this side is a transfer between the cash
    # account and the holding, not a second trade.
    (re.compile(r"\b(sell|buy) transaction of\b", re.I), TxnType.TRANSFER),
    (re.compile(r"\btransfer\b", re.I), TxnType.TRANSFER),
    (re.compile(r"\bsplit\b|\bconsolidation\b|\bcorporate action\b", re.I),
     TxnType.CORPORATE_ACTION),
]

_BALANCE_LINE = re.compile(r"\b(opening|closing) balance\b", re.I)


def is_balance_marker(description: str) -> bool:
    """Opening/closing balance rows are ledger anchors, not transactions."""
    return bool(_BALANCE_LINE.search(description))


def classify_cash(description: str) -> TxnType:
    for pattern, txn_type in _CASH_RULES:
        if pattern.search(description):
            return txn_type
    return TxnType.OTHER


def classify_trade(units_sign: int, description: str = "") -> TxnType:
    """Investment transaction rows: the sign of the quantity is authoritative,
    with the prose as a fallback when quantity is absent."""
    if units_sign < 0:
        return TxnType.SELL
    if units_sign > 0:
        return TxnType.BUY
    lowered = description.lower()
    if "sold" in lowered or "sell" in lowered:
        return TxnType.SELL
    if "bought" in lowered or "buy" in lowered:
        return TxnType.BUY
    return TxnType.OTHER


def income_type_for(security_type: SecurityType | None) -> TxnType:
    """ETFs and managed funds distribute; companies pay dividends."""
    if security_type in (SecurityType.ETF, SecurityType.MANAGED_FUND):
        return TxnType.DISTRIBUTION
    return TxnType.DIVIDEND
