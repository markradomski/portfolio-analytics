"""Typed records for the canonical portfolio dataset.

Money and unit quantities are Decimal throughout: binary floats cannot
represent decimal currency exactly, and these values are summed and reconciled
against reported totals to the cent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class TxnType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    DISTRIBUTION = "DISTRIBUTION"
    INTEREST = "INTEREST"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FEE = "FEE"
    TAX = "TAX"
    TRANSFER = "TRANSFER"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    OTHER = "OTHER"


class SecurityType(str, Enum):
    ETF = "ETF"
    SHARE = "SHARE"
    MANAGED_FUND = "MANAGED_FUND"
    CASH = "CASH"


class DocumentKind(str, Enum):
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    TAX_REPORT = "TAX_REPORT"
    PERFORMANCE = "PERFORMANCE"
    OTHER = "OTHER"


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class Provenance:
    """Where a record came from, for investigating discrepancies later."""
    document_id: str
    page: int | None
    extraction_method: str = "pdfplumber-text"


@dataclass
class Document:
    document_id: str
    filename: str
    kind: DocumentKind
    period_start: date | None
    period_end: date | None
    page_count: int
    content_sha256: str
    extraction_method: str
    imported_at: datetime


@dataclass
class Account:
    """A synthetic account. The real account number is deliberately never read,
    so accounts are identified by a constant internal ID."""
    account_id: str
    label: str
    base_currency: str = "AUD"


@dataclass
class Security:
    security_id: str
    code: str
    name: str
    type: SecurityType
    currency: str = "AUD"


@dataclass
class Transaction:
    transaction_id: str
    account_id: str
    trade_date: date
    settlement_date: date | None
    type: TxnType
    security_id: str | None
    units: Decimal | None
    price: Decimal | None
    gross_amount: Decimal | None
    fees: Decimal | None
    net_amount: Decimal | None
    currency: str
    description: str
    ordinal: int
    provenance: Provenance


@dataclass
class Holding:
    holding_id: str
    account_id: str
    reporting_date: date
    security_id: str
    units: Decimal
    price: Decimal | None
    market_value: Decimal
    currency: str
    provenance: Provenance


@dataclass
class IncomeEvent:
    income_id: str
    account_id: str
    payment_date: date
    security_id: str | None
    amount: Decimal
    rate_per_unit: Decimal | None
    franking_credit: Decimal | None
    tax_withheld: Decimal | None
    ex_date: date | None
    currency: str
    provenance: Provenance


@dataclass
class PortfolioValuation:
    valuation_id: str
    account_id: str
    reporting_date: date
    portfolio_value: Decimal
    cash_balance: Decimal | None
    investment_value: Decimal | None
    # Income declared but not yet paid. Counted in the reported portfolio
    # value while appearing in neither the holdings table nor the cash ledger.
    accrued_income: Decimal | None
    currency: str
    provenance: Provenance


@dataclass
class StatementPeriod:
    """The period summary from page 1. Not a valuation: it describes flows over
    a window, and Phase 2 uses it to reconcile computed figures against what
    Vanguard reported."""
    period_id: str
    account_id: str
    kind: DocumentKind
    period_start: date | None
    period_end: date
    opening_value: Decimal | None
    closing_value: Decimal | None
    deposits: Decimal | None
    withdrawals: Decimal | None
    transfers_in: Decimal | None
    transfers_out: Decimal | None
    change_in_value: Decimal | None
    income: Decimal | None
    withholding_tax: Decimal | None
    fees: Decimal | None
    reported_return: Decimal | None
    opening_cash: Decimal | None
    provenance: Provenance


@dataclass
class TaxSummary:
    """Portfolio-level tax figures for one financial year."""
    tax_summary_id: str
    financial_year: int
    period_start: date | None
    period_end: date | None
    gross_income: Decimal | None = None
    net_income_received: Decimal | None = None
    dividend_franking_credits: Decimal | None = None
    trust_franking_credits: Decimal | None = None
    foreign_income_tax_offsets: Decimal | None = None
    total_tax_offsets: Decimal | None = None
    withholding_tax: Decimal | None = None
    total_fees: Decimal | None = None
    gross_capital_gains: Decimal | None = None
    net_capital_gain: Decimal | None = None
    discounted_capital_gains: Decimal | None = None
    cgt_concession: Decimal | None = None
    capital_losses_carried_forward: Decimal | None = None


@dataclass
class SecurityTaxDetail:
    """Annual distribution tax detail for one security. Trust distributions are
    reported as yearly totals with no payment dates, so they are never split
    across individual income events."""
    security_tax_id: str
    financial_year: int
    code: str
    security_id: str
    franked_amount: Decimal | None
    unfranked_amount: Decimal | None
    franking_credit: Decimal | None
    interest_income: Decimal | None
    other_deductions: Decimal | None
    page: int | None = None


@dataclass
class DividendTaxDetail:
    """One dividend payment, as reported for tax. Carries the ex date and
    franking credits that the quarterly statements omit."""
    financial_year: int
    code: str
    ex_date: date | None
    payment_date: date | None
    unfranked_amount: Decimal | None
    franked_amount: Decimal | None
    franking_credit: Decimal | None
    total_income: Decimal | None
    page: int | None = None


@dataclass
class Issue:
    severity: Severity
    code: str
    message: str
    document_id: str | None = None
    filename: str | None = None
    page: int | None = None


@dataclass
class ParsedDocument:
    """Everything extracted from a single PDF, before deduplication."""
    document: Document
    securities: list[Security] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    holdings: list[Holding] = field(default_factory=list)
    income: list[IncomeEvent] = field(default_factory=list)
    valuations: list[PortfolioValuation] = field(default_factory=list)
    periods: list[StatementPeriod] = field(default_factory=list)
    tax_summary: TaxSummary | None = None
    security_tax: list[SecurityTaxDetail] = field(default_factory=list)
    dividend_tax: list[DividendTaxDetail] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
