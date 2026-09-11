"""Parser for the Vanguard *cash transactions CSV* (cash-account ledger).

Step 9B, Stage 1. Produces sanitised `CashSourceRecord`s -- no canonical
transactions yet. `Product Name` on cash rows can embed a destination account
or BSB (Deposit / Withdrawal descriptions); it is redacted before the record is
built.

Observed schema (current export):
    Date, Type, Product Type, Product Name, Product ID, Units, Total
    Type vocabulary: Distribution, Buy, Fees and Charges, Interest, Deposit,
                     Sell, Withdrawal
    Total: signed -- credit > 0, debit < 0
    Distribution rows: blank Product ID (security identified by Product Name)
    Fees and Charges: all "OngoingAdminChargeByValue" -- account admin fee, not
                      trade brokerage
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal
from pathlib import Path

from src.ingestion.vanguard_csv import sanitise
from src.ingestion.vanguard_csv.investment import SchemaError, _load_text, sanitise_hash
from src.ingestion.vanguard_csv.records import (
    CashClass, CashSourceRecord, ParseResult, QuarantinedRow, SourceKind,
    SourceLocation,
)
from src.normalisation.securities import normalise_code
from src.normalisation.values import parse_date, parse_decimal

REQUIRED_COLUMNS = frozenset({
    "Date", "Type", "Product Type", "Product Name", "Product ID", "Units", "Total",
})

# Raw Vanguard "Type" -> normalised class. Casing normalised to lower for lookup.
# "Fees and Charges" is resolved further by Product Name (see `_fee_class`).
_TYPE_MAP = {
    "deposit": CashClass.DEPOSIT,
    "withdrawal": CashClass.WITHDRAWAL,
    "distribution": CashClass.DISTRIBUTION_INCOME,
    "interest": CashClass.INTEREST,
    "buy": CashClass.TRADE_BUY_CASH,
    "sell": CashClass.TRADE_SELL_CASH,
}


def _fee_class(product_name: str) -> CashClass:
    """Split a `Fees and Charges` row by its description (Stage 4 evidence):
    an "... Transaction fee for X" is trade brokerage, a "Reversal: ..." is a
    fee reversal, everything else (OngoingAdminChargeByValue) is an admin fee.
    """
    low = (product_name or "").lower()
    if low.startswith("reversal:"):
        return CashClass.FEE_REVERSAL
    if "transaction fee for" in low:
        return CashClass.TRADE_BROKERAGE_CASH
    return CashClass.ADMIN_FEE


# Expected sign of `Total` for each class (None = either sign acceptable).
_EXPECTED_SIGN = {
    CashClass.DEPOSIT: 1,
    CashClass.WITHDRAWAL: -1,
    CashClass.DISTRIBUTION_INCOME: 1,
    CashClass.INTEREST: None,          # tiny negative interest adjustments occur
    CashClass.ADMIN_FEE: -1,
    CashClass.TRADE_BROKERAGE_CASH: -1,
    CashClass.FEE_REVERSAL: 1,         # a reversal credits the account
    CashClass.TRADE_BUY_CASH: -1,
    CashClass.TRADE_SELL_CASH: 1,
}


def _read(source: str | Path) -> tuple[list[dict[str, str]], str]:
    reader = csv.DictReader(io.StringIO(_load_text(source)))
    if reader.fieldnames is None:
        raise SchemaError("cash transactions CSV: empty / no header row")
    present = {f.strip() for f in reader.fieldnames}
    missing = REQUIRED_COLUMNS - present
    if missing:
        raise SchemaError(f"cash transactions CSV: missing columns {sorted(missing)}")
    rows = list(reader)
    safe = [{k: sanitise.redact(v) for k, v in row.items()
             if (k or "").strip().lower() not in sanitise.FORBIDDEN_COLUMNS}
            for row in rows]
    return rows, sanitise_hash(safe)


def parse_cash_csv(source: str | Path) -> ParseResult:
    rows, digest = _read(source)
    result = ParseResult(kind=SourceKind.CASH_TXN_CSV,
                         sanitised_file_sha256=digest, rows_in=len(rows))

    for i, raw in enumerate(rows, start=1):
        cells = {k: sanitise.redact(v) for k, v in raw.items()
                 if (k or "").strip().lower() not in sanitise.FORBIDDEN_COLUMNS}

        def quarantine(code: str, msg: str) -> None:
            result.quarantined.append(QuarantinedRow(
                SourceKind.CASH_TXN_CSV, i, code, msg, cells))

        label = (raw.get("Type") or "").strip()
        if label.lower() == "fees and charges":
            cash_class: CashClass | None = _fee_class(cells.get("Product Name", ""))
        else:
            cash_class = _TYPE_MAP.get(label.lower())
        if cash_class is None:
            quarantine("UNKNOWN_CASH_TYPE", f"unrecognised Type {label!r}")
            continue

        if cash_class is CashClass.DEPOSIT and "Product Name" in cells:
            cells = {**cells, "Product Name": sanitise.strip_deposit_source(cells["Product Name"])}

        when = parse_date(raw.get("Date"))
        if when is None:
            quarantine("BAD_DATE", f"unparseable Date {raw.get('Date')!r}")
            continue

        total = parse_decimal(raw.get("Total"))
        if total is None:
            quarantine("BAD_TOTAL", f"unparseable Total {raw.get('Total')!r}")
            continue

        expected_sign = _EXPECTED_SIGN[cash_class]
        if expected_sign is not None and total != 0:
            actual = 1 if total > 0 else -1
            if actual != expected_sign:
                # A sign that contradicts the type is a real anomaly (e.g. a
                # reversed deposit). Keep the row -- flag, don't drop.
                result.warnings.append(
                    f"row {i}: {label} has Total {total} "
                    f"(expected {'credit' if expected_sign > 0 else 'debit'})")

        units = parse_decimal(raw.get("Units"))  # blank on all non-trade rows
        # `cells["Product Name"]` was already stripped of its trailing
        # bank-name/initials clause above (Deposit rows only) -- the digit-only
        # redact() leaves alphabetic source identifiers untouched, so this is
        # a second, dedicated pass rather than a pattern-match on names.

        result.cash_records.append(CashSourceRecord(
            date=when,
            raw_type=label,
            cash_class=cash_class,
            product_name=cells.get("Product Name", ""),
            product_id=normalise_code(raw.get("Product ID")),
            units=units,
            signed_total=total,
            location=SourceLocation(SourceKind.CASH_TXN_CSV, digest, i),
            sanitised_cells=cells,
        ))

    result.assert_all_rows_accounted()
    return result
