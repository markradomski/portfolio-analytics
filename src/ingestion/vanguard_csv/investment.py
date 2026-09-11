"""Parser for the Vanguard *investment transactions CSV* (Buy/Sell orders).

Step 9B, Stage 1. Produces sanitised `InvestmentSourceRecord`s -- no canonical
transactions yet. The `Account number` column is dropped before any row is
built; every other cell is redacted through `sanitise.redact`.

Observed schema (current export):
    Account number, Investment, Product ID, Product Type, Trade Date, Type,
    Unit Price, Quantity, Value, Brokerage
    Type vocabulary: "Buy Trade", "Sell trade"  (casing varies -- matched loosely)
    Quantity: signed, BUY > 0, SELL < 0
    Value: unsigned gross consideration (== units * price)
    Brokerage: "9" or blank
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal
from pathlib import Path

from src.ingestion.vanguard_csv import sanitise
from src.ingestion.vanguard_csv.records import (
    BrokerageSourceStatus, InvestmentSourceRecord, ParseResult, QuarantinedRow,
    SourceKind, SourceLocation, TradeSide,
)
from src.normalisation.securities import normalise_code
from src.normalisation.values import parse_date, parse_decimal

REQUIRED_COLUMNS = frozenset({
    "Investment", "Product ID", "Product Type", "Trade Date", "Type",
    "Unit Price", "Quantity", "Value", "Brokerage",
})

_BUY_LABELS = {"buy trade", "buy"}
_SELL_LABELS = {"sell trade", "sell"}


class SchemaError(ValueError):
    """Raised when the CSV is missing columns the importer must have -- a hard
    failure, per spec: 'Fail clearly if the schema differs materially.'"""


def _load_text(source: str | Path) -> str:
    """A `Path` is read from disk; a `str` is treated as CSV content directly
    (so tests need no temp files)."""
    if isinstance(source, Path):
        return source.read_text()
    return source


def _read(source: str | Path) -> tuple[list[dict[str, str]], str]:
    text = _load_text(source)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise SchemaError("investment transactions CSV: empty / no header row")
    present = {f.strip() for f in reader.fieldnames}
    missing = REQUIRED_COLUMNS - present
    if missing:
        raise SchemaError(f"investment transactions CSV: missing columns {sorted(missing)}")
    rows = list(reader)
    # Re-hash only the sanitised, account-free content so the file's identity
    # never depends on the account number in a cell or the filename.
    safe = drop_account_column(rows)
    digest = sanitise_hash(safe)
    return rows, digest


def drop_account_column(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {k: sanitise.redact(v) for k, v in row.items()
         if (k or "").strip().lower() not in sanitise.FORBIDDEN_COLUMNS}
        for row in rows
    ]


def sanitise_hash(safe_rows: list[dict[str, str]]) -> str:
    import hashlib
    payload = "\n".join(
        "|".join(f"{k}={v}" for k, v in sorted(row.items())) for row in safe_rows
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def parse_investment_csv(
    source: str | Path,
    *,
    review_blank_brokerage: bool = False,
) -> ParseResult:
    """Parse the investment transactions CSV into sanitised source records.

    `review_blank_brokerage=True` marks every blank-brokerage row
    `SOURCE_BLANK_NEEDS_REVIEW` and raises a warning instead of quietly applying
    the zero rule -- the hook for 'a future row has blank brokerage but other
    fields imply a non-zero charge' (spec, authoritative decision 1).
    """
    rows, digest = _read(source)
    result = ParseResult(kind=SourceKind.INVESTMENT_TXN_CSV,
                         sanitised_file_sha256=digest, rows_in=len(rows))

    for i, raw in enumerate(rows, start=1):
        cells = {k: sanitise.redact(v) for k, v in raw.items()
                 if (k or "").strip().lower() not in sanitise.FORBIDDEN_COLUMNS}

        def quarantine(code: str, msg: str) -> None:
            result.quarantined.append(QuarantinedRow(
                SourceKind.INVESTMENT_TXN_CSV, i, code, msg, cells))

        label = (raw.get("Type") or "").strip()
        low = label.lower()
        if low in _BUY_LABELS:
            side = TradeSide.BUY
        elif low in _SELL_LABELS:
            side = TradeSide.SELL
        else:
            quarantine("UNKNOWN_TRADE_TYPE", f"unrecognised Type {label!r}")
            continue

        traded = parse_date(raw.get("Trade Date"))
        if traded is None:
            quarantine("BAD_TRADE_DATE", f"unparseable Trade Date {raw.get('Trade Date')!r}")
            continue

        qty = parse_decimal(raw.get("Quantity"))
        price = parse_decimal(raw.get("Unit Price"))
        value = parse_decimal(raw.get("Value"))
        if qty is None or price is None or value is None:
            quarantine("BAD_NUMERIC",
                       f"unparseable Quantity/Unit Price/Value: "
                       f"{raw.get('Quantity')!r}/{raw.get('Unit Price')!r}/{raw.get('Value')!r}")
            continue
        if qty == 0:
            quarantine("ZERO_QUANTITY", "trade row has zero quantity")
            continue

        # Sign convention check: BUY must be positive, SELL negative.
        if side is TradeSide.BUY and qty < 0:
            quarantine("SIGN_MISMATCH", "Buy row has a negative Quantity")
            continue
        if side is TradeSide.SELL and qty > 0:
            quarantine("SIGN_MISMATCH", "Sell row has a positive Quantity")
            continue

        raw_brk_str = (raw.get("Brokerage") or "").strip()
        if raw_brk_str == "":
            raw_brk: Decimal | None = None
            if review_blank_brokerage:
                canonical_brk = Decimal("0.00")
                status = BrokerageSourceStatus.SOURCE_BLANK_NEEDS_REVIEW
                result.warnings.append(
                    f"row {i}: blank brokerage flagged for review (not auto-zeroed)")
            else:
                # Authoritative decision 1: Vanguard's historical brokerage-free
                # ETF semantics -- blank normalises to 0.00, but the raw None is
                # preserved and the status records that this was interpretation.
                canonical_brk = Decimal("0.00")
                status = BrokerageSourceStatus.SOURCE_BLANK_INTERPRETED_AS_ZERO
        else:
            raw_brk = parse_decimal(raw_brk_str)
            if raw_brk is None:
                quarantine("BAD_BROKERAGE", f"unparseable Brokerage {raw_brk_str!r}")
                continue
            canonical_brk = raw_brk
            status = BrokerageSourceStatus.SOURCE_VALUE

        # Arithmetic sanity (spec §7): |qty| * price ~= value, cent tolerance
        # per unit. Recorded as a warning, not a rejection -- the row is still
        # imported with its source figures intact.
        expected = (abs(qty) * price).quantize(Decimal("0.01"))
        if abs(expected - value) > (Decimal("0.01") * abs(qty) + Decimal("0.01")):
            result.warnings.append(
                f"row {i}: Value {value} != |Quantity|*Unit Price {expected} "
                f"(diff {value - expected})")

        result.investment_records.append(InvestmentSourceRecord(
            security_name=cells.get("Investment", ""),
            product_id=normalise_code(raw.get("Product ID")),
            product_type=(raw.get("Product Type") or "").strip() or None,
            trade_date=traded,
            raw_type=label,
            side=side,
            raw_quantity=qty,
            canonical_units=abs(qty),
            unit_price=price,
            gross_value=value,
            raw_brokerage=raw_brk,
            canonical_brokerage=canonical_brk,
            brokerage_source_status=status,
            location=SourceLocation(SourceKind.INVESTMENT_TXN_CSV, digest, i),
            sanitised_cells=cells,
        ))

    result.assert_all_rows_accounted()
    return result
