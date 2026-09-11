"""Turn page-attributed statement lines into canonical records.

Statements are laid out as prose tables with wrapped cells, and section order
is not stable between years, so sections are located by heading text and rows
are anchored on their numeric run rather than on column positions.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import re

from src.ids import content_hash, make_id
from src.ingestion import tax_report_parser
from src.ingestion.pdf_parser import (EXTRACTION_METHOD, PageLine,
                                      redact_inline, load)
from src.models import (Document, DocumentKind, Holding, IncomeEvent, Issue,
                        ParsedDocument, PortfolioValuation, Provenance,
                        Security, SecurityType, Severity, StatementPeriod,
                        Transaction, TxnType)
from src.normalisation.securities import normalise_code, security_type_for
from src.normalisation.transactions import (classify_cash, classify_trade,
                                            income_type_for, is_balance_marker)
from src.normalisation.values import (DATE_LONG, DATE_SHORT, NUMBER,
                                      parse_date, parse_decimal)

ACCOUNT_ID = make_id("ACCOUNT", "primary")

# --- row patterns -----------------------------------------------------------

# Holdings rows: long product names wrap across neighbouring lines, so the row
# is recognised by its trailing quantity/price/date/value run.
HOLDING_ROW = re.compile(
    rf"^([A-Z]{{2,5}})\s+(.*?)\s*({NUMBER})\s+({NUMBER})\s+({DATE_SHORT})\s+({NUMBER})\s*$"
)

# Trade rows: the settlement column reads "Not yet settled" for trades placed
# near period end, and the bracketed ticker may sit on an adjacent line.
TRADE_ANCHOR = re.compile(
    rf"^({DATE_LONG})\s+({DATE_LONG}|Not yet settled)\s+(.*?)"
    rf"({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+([A-Z]{{3}})\s+({NUMBER})\s*$"
)
CODE_IN_LINE = re.compile(r"\(([A-Z]{2,5})\)")

# Cash ledger rows. Debit and credit are separate columns in the PDF but
# indistinguishable once flattened to text, so direction is recovered from the
# movement in the running balance. The amount is always the number immediately
# before the balance -- anything earlier belongs to the description, such as the
# per-unit rate in "DIV: VAS.XASX.AU @ AUD 0.8479".
CASH_ROW_AMOUNT = re.compile(rf"^({DATE_LONG})\s+(.*?)\s*({NUMBER})\s+({NUMBER})\s*$")
CASH_ROW_BALANCE = re.compile(rf"^({DATE_LONG})\s+(.*?)\s*({NUMBER})\s*$")
_IS_ROW = re.compile(rf"^({DATE_LONG})\s")
_TABLE_HEADER = re.compile(r"Effective date|Transaction description|Debits", re.I)


# Descriptions that always fit on one line. A row carrying one of these needs
# nothing from its neighbours -- and must not take anything, or it will absorb
# the trailing fragment of the wrapped row above it.
_SELF_CONTAINED = re.compile(
    r"^(DIV\s*:|Buy transaction of|Sell transaction of|Account Fee"
    r"|Cash Account Interest|Opening balance|Closing balance"
    r"|Failed Direct Debit)", re.I)


def _is_continuation(text: str) -> bool:
    """A wrapped fragment of the adjacent row, rather than a row or a header."""
    return not _IS_ROW.match(text) and not _TABLE_HEADER.search(text)

DIV_LINE = re.compile(r"^\s*DIV\s*:\s*([A-Z0-9.]+)\s*(?:@\s*([A-Z]{3})\s*([\d.]+))?", re.I)

SUMMARY_FIELDS = [
    ("opening_value", rf"Portfolio opening value as at .+?\s({NUMBER})\s*$"),
    ("deposits", rf"Deposits into Vanguard Cash Account\s+({NUMBER})"),
    ("withdrawals", rf"Withdrawals from Vanguard Cash Account\s+({NUMBER})"),
    ("transfers_in", rf"Assets transferred in\s+({NUMBER})"),
    ("transfers_out", rf"Assets transferred out\s+({NUMBER})"),
    ("change_in_value", rf"Change in investment value\s+({NUMBER})"),
    ("income", rf"Income from your investments\s+({NUMBER})"),
    ("withholding_tax", rf"Withholding tax\s+({NUMBER})"),
    ("fees", rf"Direct fees and costs\s+({NUMBER})"),
    ("closing_value", rf"Portfolio closing value as at .+?\s({NUMBER})\s*$"),
    ("reported_return", rf"Return after withholding tax and fees\s+({NUMBER})"),
]

ASSET_CLASS_HEADINGS = [
    ("Exchange traded funds (ETFs)", "etf"),
    ("Australian shares", "australian_share"),
    ("Managed funds", "managed_fund"),
    ("Vanguard Cash Account", "cash"),
]

DOCUMENT_KINDS = [
    ("Annual Tax Report", DocumentKind.TAX_REPORT),
    ("Account Performance Report", DocumentKind.PERFORMANCE),
    ("Annual Statement", DocumentKind.ANNUAL),
    ("Quarterly Statement", DocumentKind.QUARTERLY),
]

STATEMENT_KINDS = (DocumentKind.QUARTERLY, DocumentKind.ANNUAL)


# --- helpers ----------------------------------------------------------------

def _section(lines: list[PageLine], start: str, *stops: str) -> list[PageLine]:
    """Lines from the first heading match up to (not including) any stop."""
    out: list[PageLine] = []
    started = False
    for line in lines:
        lowered = line.text.lower()
        if not started:
            if start.lower() in lowered:
                started = True
            continue
        if any(stop.lower() in lowered for stop in stops):
            break
        out.append(line)
    return out


def _classify(text: str) -> DocumentKind:
    for needle, kind in DOCUMENT_KINDS:
        if needle in text:
            return kind
    return DocumentKind.OTHER


def _period(text: str) -> tuple[date | None, date | None]:
    match = re.search(rf"for the period ({DATE_LONG}) to ({DATE_LONG})", text)
    if match:
        return parse_date(match.group(1)), parse_date(match.group(2))
    match = re.search(r"Period ending (\d{1,2} \w+ \d{4})", text)
    if match:
        return None, parse_date(match.group(1))
    return None, None


def _reporting_date(text: str) -> date | None:
    match = re.search(r"portfolio valuation as at (\d{1,2} \w+ \d{4})", text, re.I)
    return parse_date(match.group(1)) if match else None


# --- section parsers --------------------------------------------------------

def _parse_summary(lines: list[PageLine]) -> tuple[dict, int | None]:
    text = "\n".join(l.text for l in lines)
    values, page = {}, None
    for key, pattern in SUMMARY_FIELDS:
        match = re.search(pattern, text, re.M)
        if match:
            values[key] = parse_decimal(match.group(1))
            if page is None:
                page = next((l.page for l in lines if match.group(0) in l.text), None)
    return values, page


def _parse_holdings(lines: list[PageLine], issues: list[Issue], doc_id: str):
    """Yields (code, name, asset_class, units, price, price_date, value, page)."""
    section = _section(lines, "Your portfolio valuation as at",
                       "Vanguard Cash Account transaction details")
    asset_class = None
    for line in section:
        for heading, cls in ASSET_CLASS_HEADINGS:
            if line.text.startswith(heading) and not line.text.startswith("Total"):
                asset_class = cls
        if line.text.startswith("Total") or asset_class in (None, "cash"):
            continue
        match = HOLDING_ROW.match(line.text)
        if not match:
            continue
        code, name, units, price, price_date, value = match.groups()
        parsed_units, parsed_value = parse_decimal(units), parse_decimal(value)
        if parsed_units is None or parsed_value is None:
            issues.append(Issue(Severity.WARNING, "HOLDING_UNPARSED",
                                f"Holding row for {code} had unreadable numbers",
                                document_id=doc_id, page=line.page))
            continue
        yield (code, name.strip(), asset_class, parsed_units,
               parse_decimal(price), parse_date(price_date), parsed_value, line.page)


def _parse_trades(lines: list[PageLine]):
    """Yields (trade_date, settle_date, code, product, units, price, fee,
    currency, value, page)."""
    texts = [l.text for l in lines]
    section_start = next(
        (i for i, t in enumerate(texts)
         if "investment transaction details" in t.lower()), None)
    if section_start is None:
        return
    for i in range(section_start + 1, len(texts)):
        if texts[i].startswith("Notes:"):
            break
        match = TRADE_ANCHOR.match(texts[i])
        if not match:
            continue
        traded, settled, middle, units, price, fee, currency, value = match.groups()
        # A row carrying its own bracketed code is complete; only a wrapped
        # product name needs its neighbours. Borrowing unconditionally pulls in
        # the adjacent trade row or the table header.
        if CODE_IN_LINE.search(middle):
            before = after = ""
        else:
            before = texts[i - 1] if i > section_start + 1 else ""
            after = texts[i + 1] if i + 1 < len(texts) else ""
        code_match = next((m for m in
                           (CODE_IN_LINE.search(x) for x in (middle, after, before)) if m), None)
        code = code_match.group(1) if code_match else None
        product = " ".join(
            CODE_IN_LINE.sub("", " ".join((before, middle, after))).split())
        yield (parse_date(traded), parse_date(settled), code, product,
               parse_decimal(units), parse_decimal(price), parse_decimal(fee),
               currency, parse_decimal(value), lines[i].page)


def _parse_cash(lines: list[PageLine]):
    """Yields (date, description, signed_amount, balance, page).

    Long descriptions wrap around the numeric row -- the text starts on the line
    above and continues on the line below -- so a row whose description comes
    back empty borrows from its neighbours.
    """
    section = _section(lines, "Vanguard Cash Account transaction details",
                       "Your investment transaction details", "Notes:")
    previous: Decimal | None = None

    for i, line in enumerate(section):
        match = CASH_ROW_AMOUNT.match(line.text)
        if match:
            when, description, raw_amount, raw_balance = match.groups()
            amount = parse_decimal(raw_amount)
        else:
            match = CASH_ROW_BALANCE.match(line.text)
            if not match:
                continue
            when, description, raw_balance = match.groups()
            amount = None

        balance = parse_decimal(raw_balance)
        if balance is None:
            continue

        # A long description wraps around its numeric row: it begins on the
        # line above and continues on the line below, sometimes leaving only a
        # fragment on the row itself. Neighbouring lines that are not rows in
        # their own right belong to this one.
        description = description.strip()
        if not _SELF_CONTAINED.match(description):
            before = (section[i - 1].text if i > 0
                      and _is_continuation(section[i - 1].text) else "")
            after = (section[i + 1].text if i + 1 < len(section)
                     and _is_continuation(section[i + 1].text) else "")
            description = " ".join(
                part for part in (before, description, after) if part).strip()

        signed = None
        if amount is not None and previous is not None:
            signed = amount if balance > previous else -amount

        yield (parse_date(when), redact_inline(description), signed, balance, line.page)
        previous = balance


# --- entry point ------------------------------------------------------------

def parse_document(path: Path) -> ParsedDocument:
    raw = path.read_bytes()
    lines, page_count = load(path)
    text = "\n".join(l.text for l in lines)

    kind = _classify(text)
    period_start, period_end = _period(text)
    # The cash ledger states its own opening date and balance. Both are read
    # from the document rather than inferred.
    opening = re.search(
        rf"^({DATE_LONG})\s+Opening balance\s+({NUMBER})\s*$", text, re.M)
    if period_start is None and opening:
        period_start = parse_date(opening.group(1))
    doc_id = make_id("DOC", content_hash(raw))
    document = Document(
        document_id=doc_id, filename=path.name, kind=kind,
        period_start=period_start, period_end=period_end, page_count=page_count,
        content_sha256=content_hash(raw), extraction_method=EXTRACTION_METHOD,
        imported_at=datetime.now(),
    )
    parsed = ParsedDocument(document=document)

    if kind is DocumentKind.TAX_REPORT:
        summary, security_tax, dividend_tax = tax_report_parser.parse(
            lines, doc_id, parsed.issues)
        parsed.tax_summary = summary
        parsed.security_tax = security_tax
        parsed.dividend_tax = dividend_tax
        return parsed

    if kind not in STATEMENT_KINDS:
        parsed.issues.append(Issue(
            Severity.INFO, "DOCUMENT_SKIPPED",
            f"{path.name}: {kind.value} carries no portfolio records; skipped",
            document_id=doc_id, filename=path.name))
        return parsed

    securities: dict[str, Security] = {}

    def register(code: str | None, name: str, asset_class: str | None) -> str | None:
        code = normalise_code(code)
        if not code:
            return None
        if code not in securities:
            securities[code] = Security(
                security_id=make_id("SEC", code), code=code, name=name,
                type=security_type_for(asset_class, name))
        elif asset_class and securities[code].type is SecurityType.SHARE:
            securities[code].type = security_type_for(asset_class, name)
        return securities[code].security_id

    def prov(page: int | None) -> Provenance:
        return Provenance(document_id=doc_id, page=page,
                          extraction_method=EXTRACTION_METHOD)

    # -- holdings
    reporting_date = _reporting_date(text) or period_end
    for (code, name, cls, units, price, price_date, value, page) in _parse_holdings(
            lines, parsed.issues, doc_id):
        security_id = register(code, name, cls)
        if security_id is None or reporting_date is None:
            continue
        parsed.holdings.append(Holding(
            holding_id=make_id("HLD", reporting_date, code), account_id=ACCOUNT_ID,
            reporting_date=reporting_date, security_id=security_id, units=units,
            price=price, market_value=value, currency="AUD", provenance=prov(page)))

    # -- trades
    pending: list[Transaction] = []
    for (traded, settled, code, product, units, price, fee, currency, value,
         page) in _parse_trades(lines):
        if traded is None or units is None:
            parsed.issues.append(Issue(
                Severity.WARNING, "TRADE_UNPARSED",
                f"Trade row missing a date or quantity ({product[:40]})",
                document_id=doc_id, page=page))
            continue
        security_id = register(code, product, None)
        if security_id is None:
            parsed.issues.append(Issue(
                Severity.WARNING, "TRADE_NO_SECURITY",
                f"Trade row has no recoverable ticker ({product[:40]})",
                document_id=doc_id, page=page))
        gross = (units * price) if price is not None else None
        pending.append(Transaction(
            transaction_id="", account_id=ACCOUNT_ID, trade_date=traded,
            settlement_date=settled, type=classify_trade(1 if units > 0 else -1, product),
            security_id=security_id, units=units, price=price, gross_amount=gross,
            fees=fee, net_amount=value, currency=currency or "AUD",
            description=product, ordinal=0, provenance=prov(page)))

    # -- cash ledger
    for (when, description, signed, balance, page) in _parse_cash(lines):
        if when is None or is_balance_marker(description):
            continue
        if signed is None:
            parsed.issues.append(Issue(
                Severity.WARNING, "CASH_DIRECTION_UNKNOWN",
                f"Could not infer debit/credit for '{description[:40]}'",
                document_id=doc_id, page=page))
            continue
        txn_type = classify_cash(description)
        security_id = None
        div = DIV_LINE.match(description)
        if div:
            security_id = register(div.group(1), div.group(1), None)
            code = normalise_code(div.group(1))
            sec_type = securities[code].type if code in securities else None
            txn_type = income_type_for(sec_type)
            rate = parse_decimal(div.group(3)) if div.group(3) else None
            parsed.income.append(IncomeEvent(
                income_id=make_id("INC", when, code, signed), account_id=ACCOUNT_ID,
                payment_date=when, security_id=security_id, amount=signed,
                rate_per_unit=rate, franking_credit=None, tax_withheld=None,
                ex_date=None, currency="AUD", provenance=prov(page)))
        if txn_type is TxnType.OTHER:
            parsed.issues.append(Issue(
                Severity.WARNING, "CASH_UNCLASSIFIED",
                f"Cash row fell through to OTHER: '{description[:60]}'",
                document_id=doc_id, page=page))
        pending.append(Transaction(
            transaction_id="", account_id=ACCOUNT_ID, trade_date=when,
            settlement_date=None, type=txn_type, security_id=security_id,
            units=None, price=None, gross_amount=None, fees=None,
            net_amount=signed, currency="AUD", description=description,
            ordinal=0, provenance=prov(page)))

    # Two genuinely identical rows in one document are distinct events; an
    # ordinal keeps them apart while staying stable across re-imports and
    # across the quarterly/annual overlap.
    seen: Counter[tuple] = Counter()
    for txn in pending:
        key = (txn.trade_date, txn.type.value, txn.security_id,
               txn.units, txn.net_amount)
        txn.ordinal = seen[key]
        seen[key] += 1
        txn.transaction_id = make_id("TXN", *key, txn.ordinal)
    parsed.transactions = pending

    # -- valuation and period summary
    summary, summary_page = _parse_summary(lines)
    total = re.search(rf"Total cash and investment value\s+({NUMBER})", text)
    cash_total = re.search(rf"Total Vanguard Cash Account\s+({NUMBER})", text)
    accrued = re.search(
        rf"Income on investments due not yet received\s+({NUMBER})", text)
    if reporting_date and total:
        portfolio_value = parse_decimal(total.group(1))
        cash_balance = parse_decimal(cash_total.group(1)) if cash_total else None
        parsed.valuations.append(PortfolioValuation(
            valuation_id=make_id("VAL", reporting_date), account_id=ACCOUNT_ID,
            reporting_date=reporting_date, portfolio_value=portfolio_value,
            cash_balance=cash_balance,
            accrued_income=parse_decimal(accrued.group(1)) if accrued else None,
            investment_value=(portfolio_value - cash_balance)
            if portfolio_value is not None and cash_balance is not None else None,
            currency="AUD", provenance=prov(summary_page)))

    if period_end:
        parsed.periods.append(StatementPeriod(
            period_id=make_id("PER", kind.value, period_start, period_end),
            account_id=ACCOUNT_ID, kind=kind, period_start=period_start,
            period_end=period_end, reported_return=summary.get("reported_return"),
            opening_cash=parse_decimal(opening.group(2)) if opening else None,
            provenance=prov(summary_page),
            **{k: summary.get(k) for k in
               ("opening_value", "closing_value", "deposits", "withdrawals",
                "transfers_in", "transfers_out", "change_in_value", "income",
                "withholding_tax", "fees")}))

    parsed.securities = list(securities.values())
    return parsed
