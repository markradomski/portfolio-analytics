"""Sanitised source records for the two Vanguard structured exports.

Step 9B, Stage 1: these are *not* canonical financial transactions. They are a
faithful, privacy-safe, typed rendering of each CSV row, with just enough
normalisation (type vocabulary, sign handling, the blank-brokerage rule) that
Stage 2 can match trades across the two files and Stage 3 can build canonical
events. Nothing here touches the accounting engine.

Every input row is accounted for: it becomes either a record or a
`QuarantinedRow`. Nothing is silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class SourceKind(str, Enum):
    INVESTMENT_TXN_CSV = "INVESTMENT_TXN_CSV"
    CASH_TXN_CSV = "CASH_TXN_CSV"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class CashClass(str, Enum):
    """Normalised cash-CSV row class. `TRADE_BUY_CASH` / `TRADE_SELL_CASH` are
    the cash *legs* of trades -- Stage 2 joins them to the investment-CSV row;
    they never become standalone canonical trades.

    Stage 4 evidence corrected the fee handling: the cash CSV's `Fees and
    Charges` rows are NOT all one kind. `Australian ETF/Equity Transaction
    fee for X` rows are trade **brokerage** (one per brokered trade, the
    cash side of the investment CSV's `Brokerage` column);
    `OngoingAdminChargeByValue` rows are the quarterly admin fee;
    `Reversal: ...` rows are explicit fee reversals.
    """
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    DISTRIBUTION_INCOME = "DISTRIBUTION_INCOME"   # canonical DIVIDEND vs DISTRIBUTION decided in Stage 3
    INTEREST = "INTEREST"
    ADMIN_FEE = "ADMIN_FEE"                       # OngoingAdminChargeByValue
    TRADE_BROKERAGE_CASH = "TRADE_BROKERAGE_CASH"  # "... Transaction fee for X" -- brokerage cash leg
    FEE_REVERSAL = "FEE_REVERSAL"                 # "Reversal: ..." -- explicit fee reversal/refund
    TRADE_BUY_CASH = "TRADE_BUY_CASH"
    TRADE_SELL_CASH = "TRADE_SELL_CASH"


class BrokerageSourceStatus(str, Enum):
    SOURCE_VALUE = "SOURCE_VALUE"
    SOURCE_BLANK_INTERPRETED_AS_ZERO = "SOURCE_BLANK_INTERPRETED_AS_ZERO"
    SOURCE_BLANK_NEEDS_REVIEW = "SOURCE_BLANK_NEEDS_REVIEW"


@dataclass(frozen=True)
class SourceLocation:
    """Where a record came from, with no account-identifying content. The file
    is named by its sanitised-content hash, never its filename."""
    kind: SourceKind
    sanitised_file_sha256: str
    row_number: int          # 1-based data row (header is row 0)


@dataclass(frozen=True)
class InvestmentSourceRecord:
    security_name: str
    product_id: str | None
    product_type: str | None
    trade_date: date
    raw_type: str                      # verbatim Vanguard label, e.g. "Buy Trade"
    side: TradeSide
    raw_quantity: Decimal              # signed exactly as exported (BUY > 0, SELL < 0)
    canonical_units: Decimal           # abs(raw_quantity) -- the ledger stores unsigned units + type
    unit_price: Decimal
    gross_value: Decimal               # unsigned (units * price), the trade consideration
    raw_brokerage: Decimal | None      # None when the export left the cell blank -- preserved as-is
    canonical_brokerage: Decimal       # the blank-brokerage rule may set this to 0.00
    brokerage_source_status: BrokerageSourceStatus
    location: SourceLocation
    sanitised_cells: dict[str, str]    # the row as read, minus Account number, redacted


@dataclass(frozen=True)
class CashSourceRecord:
    date: date
    raw_type: str                      # verbatim Vanguard label, e.g. "Fees and Charges"
    cash_class: CashClass
    product_name: str                  # sanitised description / security long name
    product_id: str | None
    units: Decimal | None
    signed_total: Decimal              # exactly as exported: credit > 0, debit < 0
    location: SourceLocation
    sanitised_cells: dict[str, str]


@dataclass(frozen=True)
class QuarantinedRow:
    """A row that failed validation. Retained, never dropped -- Stage 1's
    acceptance gate requires every input row be accounted for."""
    kind: SourceKind
    row_number: int
    reason_code: str
    reason: str
    sanitised_cells: dict[str, str]


@dataclass
class ParseResult:
    kind: SourceKind
    sanitised_file_sha256: str
    rows_in: int = 0
    investment_records: list[InvestmentSourceRecord] = field(default_factory=list)
    cash_records: list[CashSourceRecord] = field(default_factory=list)
    quarantined: list[QuarantinedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def records_out(self) -> int:
        return len(self.investment_records) + len(self.cash_records)

    def assert_all_rows_accounted(self) -> None:
        """Stage 1 acceptance gate: rows_in == records_out + quarantined."""
        got = self.records_out + len(self.quarantined)
        if got != self.rows_in:
            raise AssertionError(
                f"{self.kind.value}: {self.rows_in} rows in, "
                f"{self.records_out} records + {len(self.quarantined)} quarantined = {got}")
