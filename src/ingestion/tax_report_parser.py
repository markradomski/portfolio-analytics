"""Parse Vanguard Annual Tax Reports.

These carry the tax detail the quarterly statements omit: franking credits,
ex-dividend dates, withholding tax and capital gains.

Two different shapes of data live here, and the difference matters:

* **Dividends** (pages 7-ish) are listed per payment, with an ex date, a payment
  date and their own franking credits. These can be matched back to individual
  income events recorded from the statements.
* **Trust distributions** (pages 8 onward) are annual totals per security, with
  no payment dates at all. They cannot be attributed to individual payments, so
  they are stored per security per financial year and never split up.

A report covers a financial year and overlaps the statements that cover the same
period; it adds detail to them rather than restating them.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from src.ids import make_id
from src.ingestion.pdf_parser import PageLine
from src.models import (DividendTaxDetail, Issue, SecurityTaxDetail, Severity,
                        TaxSummary)
from src.normalisation.securities import normalise_code
from src.normalisation.values import DATE_LONG, NUMBER, parse_date, parse_decimal

MONEY = r"\$?-?[\d,]+\.\d{2}"

# Ex date, payment date, code, product name, then four amounts:
# unfranked, franked (excluding credits), franking credits, total.
DIVIDEND_ROW = re.compile(
    rf"^({DATE_LONG})\s+({DATE_LONG})\s+([A-Z]{{2,5}})\s+(.+?)\s+"
    rf"({MONEY})\s+({MONEY})\s+({MONEY})\s+({MONEY})\s*$")

# Code, product name, then five amounts: franked (including credits),
# unfranked, franking credits, interest income, other deductions.
DISTRIBUTION_ROW = re.compile(
    rf"^([A-Z]{{2,5}})\s+(.*?)\s*({MONEY})\s+({MONEY})\s+({MONEY})\s+"
    rf"({MONEY})\s+({MONEY})\s*$")

PERIOD = re.compile(r"(\d{1,2} \w+ \d{4})\s+to\s+(\d{1,2} \w+ \d{4})")

# Portfolio-level totals. Each appears once, followed by an ATO tax guide
# reference which is deliberately not captured.
SUMMARY_FIELDS = [
    ("gross_income", r"Total gross income\s+(" + NUMBER + r")"),
    ("net_income_received", r"Total net income received\s+(" + NUMBER + r")"),
    ("dividend_franking_credits",
     r"Australian dividend franking credits\s+(" + NUMBER + r")"),
    ("trust_franking_credits", r"Trust franking credits\s+(" + NUMBER + r")"),
    ("foreign_income_tax_offsets",
     r"Trust foreign income tax offsets\s+(" + NUMBER + r")"),
    ("total_tax_offsets", r"Total tax offsets\s+(" + NUMBER + r")"),
    ("withholding_tax", r"Total withholding tax\s+(" + NUMBER + r")"),
    ("total_fees", r"Total fees\s+(" + NUMBER + r")"),
    ("gross_capital_gains",
     r"Total current year capital gains\s+(" + NUMBER + r")"),
    ("net_capital_gain", r"Net capital gain\d?\s+(" + NUMBER + r")"),
    ("discounted_capital_gains", r"Discounted capital gains\s+(" + NUMBER + r")"),
    ("cgt_concession", r"CGT concession\s+(" + NUMBER + r")"),
    ("capital_losses_carried_forward",
     r"Net capital losses carried forward\s+(" + NUMBER + r")"),
]

DIVIDEND_SECTION = "Australian dividend income and tax information"
DISTRIBUTION_SECTION = "Australian trust distribution income and tax information"
DISTRIBUTION_END = "Total Australian trust distributions"


def _financial_year(period_end: date | None) -> int | None:
    """Australian financial years end on 30 June and are named for that year."""
    if period_end is None:
        return None
    return period_end.year if period_end.month <= 6 else period_end.year + 1


def _section(lines: list[PageLine], start: str, *stops: str) -> list[PageLine]:
    out, started = [], False
    for line in lines:
        if not started:
            if start.lower() in line.text.lower():
                started = True
            continue
        if any(stop.lower() in line.text.lower() for stop in stops):
            break
        out.append(line)
    return out


def parse_period(text: str) -> tuple[date | None, date | None]:
    match = PERIOD.search(text)
    if not match:
        return None, None
    return parse_date(match.group(1)), parse_date(match.group(2))


def parse_summary(text: str) -> dict[str, Decimal | None]:
    values: dict[str, Decimal | None] = {}
    for key, pattern in SUMMARY_FIELDS:
        match = re.search(pattern, text, re.M)
        if match:
            values[key] = parse_decimal(match.group(1))
    return values


def parse_dividends(lines: list[PageLine], year: int | None,
                    issues: list[Issue], doc_id: str) -> list[DividendTaxDetail]:
    """Per-payment dividend detail: the only place ex dates appear."""
    out = []
    for line in _section(lines, DIVIDEND_SECTION, "Total Australian dividend income"):
        match = DIVIDEND_ROW.match(line.text)
        if not match:
            continue
        ex, paid, raw_code, _name, unfranked, franked, credits, total = match.groups()
        code = normalise_code(raw_code)
        if code is None:
            issues.append(Issue(
                Severity.WARNING, "TAX_DIVIDEND_NO_CODE",
                f"Dividend row on {paid} has no usable ticker",
                document_id=doc_id, page=line.page))
            continue
        out.append(DividendTaxDetail(
            financial_year=year, code=code, ex_date=parse_date(ex),
            payment_date=parse_date(paid),
            unfranked_amount=parse_decimal(unfranked),
            franked_amount=parse_decimal(franked),
            franking_credit=parse_decimal(credits),
            total_income=parse_decimal(total), page=line.page))
    return out


def parse_distributions(lines: list[PageLine], year: int | None,
                        doc_id: str) -> list[SecurityTaxDetail]:
    """Annual per-security distribution totals. No payment dates exist here."""
    out = []
    for line in _section(lines, DISTRIBUTION_SECTION, DISTRIBUTION_END):
        match = DISTRIBUTION_ROW.match(line.text)
        if not match:
            continue
        raw_code, _name, franked, unfranked, credits, interest, deductions = match.groups()
        code = normalise_code(raw_code)
        if code is None:
            continue
        out.append(SecurityTaxDetail(
            security_tax_id=make_id("STX", year, code), financial_year=year,
            code=code, security_id=make_id("SEC", code),
            franked_amount=parse_decimal(franked),
            unfranked_amount=parse_decimal(unfranked),
            franking_credit=parse_decimal(credits),
            interest_income=parse_decimal(interest),
            other_deductions=parse_decimal(deductions), page=line.page))
    return out


def parse(lines: list[PageLine], doc_id: str,
          issues: list[Issue]) -> tuple[TaxSummary | None,
                                        list[SecurityTaxDetail],
                                        list[DividendTaxDetail]]:
    text = "\n".join(l.text for l in lines)
    period_start, period_end = parse_period(text)
    year = _financial_year(period_end)
    if year is None:
        issues.append(Issue(
            Severity.WARNING, "TAX_REPORT_NO_PERIOD",
            "Tax report has no recognisable reporting period", document_id=doc_id))
        return None, [], []

    values = parse_summary(text)
    summary = TaxSummary(
        tax_summary_id=make_id("TAX", year), financial_year=year,
        period_start=period_start, period_end=period_end,
        **{key: values.get(key) for key, _ in SUMMARY_FIELDS})

    return (summary,
            parse_distributions(lines, year, doc_id),
            parse_dividends(lines, year, issues, doc_id))
