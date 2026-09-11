"""Deterministic cross-file BUY/SELL matching (Step 9B, Stage 2).

The two Vanguard exports describe the same economic trades from two angles:

    investment transactions CSV  ->  execution / security facts
    cash transactions CSV        ->  the gross cash movement of that trade

This module pairs `InvestmentSourceRecord`s with the cash CSV's `Buy` / `Sell`
rows and produces an auditable `MatchResult`. It does NOT build canonical
transactions, does NOT touch the accounting engine, does NOT read the ledger,
and does NOT promote source authority -- that is Stage 3+ and only after the
Stage 4/5 reconciliation gates.

Determinism: inputs are sorted by a stable economic key first; candidate
selection is set-based, never order-based; ties are `AMBIGUOUS`, never
resolved by row order. Re-running on reordered input yields the identical
result.

Privacy: operates only on already-sanitised Stage 1 records. No field here is
re-read from a raw CSV cell; no diagnostic string carries an identifier.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from src.ingestion.vanguard_csv.records import (
    CashClass, CashSourceRecord, InvestmentSourceRecord, TradeSide,
)

# The application's currency rounding tolerance (cf. src/engine/settlement.py).
VALUE_TOLERANCE = Decimal("0.01")
# A cash entry dated within this many days of the trade is still the same
# trade's cash leg; the delta is recorded either way.
DATE_WINDOW_DAYS = 5


class MatchStatus(str, Enum):
    MATCH = "MATCH"
    MATCH_WITH_MINOR_DIFFERENCE = "MATCH_WITH_MINOR_DIFFERENCE"
    UNMATCHED_INVESTMENT = "UNMATCHED_INVESTMENT"
    UNMATCHED_CASH = "UNMATCHED_CASH"
    AMBIGUOUS = "AMBIGUOUS"
    VALUE_MISMATCH = "VALUE_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    SECURITY_MISMATCH = "SECURITY_MISMATCH"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"


class DateRelation(str, Enum):
    SAME_DAY = "SAME_DAY"
    NEXT_DAY = "NEXT_DAY"
    PLUS_TWO_DAYS = "PLUS_TWO_DAYS"
    OTHER_POSITIVE_DELTA = "OTHER_POSITIVE_DELTA"
    NEGATIVE_DELTA = "NEGATIVE_DELTA"


def _date_relation(delta_days: int) -> DateRelation:
    if delta_days == 0:
        return DateRelation.SAME_DAY
    if delta_days == 1:
        return DateRelation.NEXT_DAY
    if delta_days == 2:
        return DateRelation.PLUS_TWO_DAYS
    if delta_days < 0:
        return DateRelation.NEGATIVE_DELTA
    return DateRelation.OTHER_POSITIVE_DELTA


@dataclass(frozen=True)
class MatchedTradeCandidate:
    match_id: str
    status: MatchStatus
    side: TradeSide
    security_id: str | None
    investment_trade_date: object          # datetime.date
    cash_transaction_date: object | None   # datetime.date | None
    date_delta_days: int | None
    date_relation: DateRelation | None
    raw_quantity: Decimal
    canonical_units_candidate: Decimal
    investment_gross_value: Decimal
    cash_total: Decimal | None
    raw_brokerage: Decimal | None
    canonical_brokerage: Decimal
    brokerage_source_status: str
    match_reasons: tuple[str, ...]
    reconciliation_deltas: dict[str, str]
    # provenance -- sanitised source locations only
    investment_row: int
    cash_row: int | None
    investment_file_sha256: str
    cash_file_sha256: str | None


@dataclass
class MatchResult:
    candidates: list[MatchedTradeCandidate] = field(default_factory=list)
    _n_inv_trades: int = 0
    _n_cash_trades: int = 0

    def assert_all_trade_rows_accounted(self) -> None:
        """Gate 1-2: every investment BUY/SELL row and every cash BUY/SELL row
        appears in the result exactly once."""
        inv_rows = [c.investment_row for c in self.candidates if c.investment_row != -1]
        cash_rows = [c.cash_row for c in self.candidates if c.cash_row is not None]
        if sorted(inv_rows) != sorted(set(inv_rows)) or len(inv_rows) != self._n_inv_trades:
            raise AssertionError(
                f"investment trade rows: {len(inv_rows)} in result, {self._n_inv_trades} in source")
        # cash rows: consumed + unmatched must cover the source; ambiguous cash
        # rows have no cash_row on the AMBIGUOUS record, so only assert coverage
        # when the result is otherwise clean.
        if self.counts()[MatchStatus.AMBIGUOUS.value] == 0:
            if len(cash_rows) != len(set(cash_rows)) or len(cash_rows) != self._n_cash_trades:
                raise AssertionError(
                    f"cash trade rows: {len(cash_rows)} in result, {self._n_cash_trades} in source")

    @property
    def matched(self) -> list[MatchedTradeCandidate]:
        return [c for c in self.candidates
                if c.status in (MatchStatus.MATCH, MatchStatus.MATCH_WITH_MINOR_DIFFERENCE)]

    def by_status(self, status: MatchStatus) -> list[MatchedTradeCandidate]:
        return [c for c in self.candidates if c.status is status]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {s.value: 0 for s in MatchStatus}
        for c in self.candidates:
            out[c.status.value] += 1
        return out

    def assert_one_to_one(self) -> None:
        inv_rows = [c.investment_row for c in self.matched]
        cash_rows = [c.cash_row for c in self.matched]
        if len(inv_rows) != len(set(inv_rows)):
            raise AssertionError("an investment row participates in two matches")
        if len(cash_rows) != len(set(cash_rows)):
            raise AssertionError("a cash row participates in two matches")

    def is_clean(self) -> bool:
        """Stage 2 gate 1-6: every trade row accounted for, 1:1, nothing
        ambiguous or unexplained-mismatched."""
        c = self.counts()
        try:
            self.assert_one_to_one()
        except AssertionError:
            return False
        return (
            c[MatchStatus.AMBIGUOUS.value] == 0
            and c[MatchStatus.UNMATCHED_INVESTMENT.value] == 0
            and c[MatchStatus.UNMATCHED_CASH.value] == 0
            and c[MatchStatus.SECURITY_MISMATCH.value] == 0
            and c[MatchStatus.VALUE_MISMATCH.value] == 0
            and c[MatchStatus.QUANTITY_MISMATCH.value] == 0
        )


_CASH_SIDE = {
    TradeSide.BUY: CashClass.TRADE_BUY_CASH,
    TradeSide.SELL: CashClass.TRADE_SELL_CASH,
}


def _match_id(inv: InvestmentSourceRecord, cash: CashSourceRecord | None, ordinal: int) -> str:
    parts = [
        "TRADEMATCH", inv.side.value, str(inv.product_id), inv.trade_date.isoformat(),
        str(inv.canonical_units), str(inv.gross_value),
        cash.date.isoformat() if cash else "-",
        str(cash.signed_total) if cash else "-", str(ordinal),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _security_agrees(inv: InvestmentSourceRecord, cash: CashSourceRecord) -> bool | None:
    """True/False when both carry a Product ID; None when the cash side lacks
    one (then the caller falls back to the long-name confirmation)."""
    if inv.product_id and cash.product_id:
        return inv.product_id == cash.product_id
    return None


def _candidate_cash_rows(
    inv: InvestmentSourceRecord, cash_rows: list[CashSourceRecord],
) -> list[CashSourceRecord]:
    """Every cash row that could be this trade's leg: same side, security
    agrees (by id, or by long name when id absent), gross value within
    tolerance, date within the window."""
    want = _CASH_SIDE[inv.side]
    out = []
    for cash in cash_rows:
        if cash.cash_class is not want:
            continue
        agrees = _security_agrees(inv, cash)
        if agrees is False:
            continue
        if agrees is None and cash.product_name.strip().lower() != inv.security_name.strip().lower():
            continue
        if abs(abs(cash.signed_total) - inv.gross_value) > VALUE_TOLERANCE:
            continue
        if abs((cash.date - inv.trade_date).days) > DATE_WINDOW_DAYS:
            continue
        out.append(cash)
    return out


def match_trades(
    investment_records: list[InvestmentSourceRecord],
    cash_records: list[CashSourceRecord],
) -> MatchResult:
    result = MatchResult()

    inv_sorted = sorted(
        investment_records,
        key=lambda r: (r.side.value, str(r.product_id), r.trade_date.isoformat(),
                       str(r.canonical_units), str(r.gross_value), r.location.row_number),
    )
    cash_trades = sorted(
        (c for c in cash_records if c.cash_class in _CASH_SIDE.values()),
        key=lambda r: (r.cash_class.value, str(r.product_id), r.date.isoformat(),
                       str(r.signed_total), r.location.row_number),
    )

    # First pass: candidate sets. A cash row wanted by >1 investment row (or an
    # investment row with >1 candidate) is ambiguous for everyone involved.
    inv_candidates: dict[int, list[CashSourceRecord]] = {}
    cash_claimed_by: dict[int, list[InvestmentSourceRecord]] = {c.location.row_number: [] for c in cash_trades}
    for inv in inv_sorted:
        cands = _candidate_cash_rows(inv, cash_trades)
        inv_candidates[inv.location.row_number] = cands
        for c in cands:
            cash_claimed_by[c.location.row_number].append(inv)

    consumed_cash: set[int] = set()
    group_ordinal: dict[tuple, int] = {}

    for inv in inv_sorted:
        cands = inv_candidates[inv.location.row_number]
        contested = [c for c in cands if len(cash_claimed_by[c.location.row_number]) > 1]

        gk = (inv.side.value, inv.product_id, inv.trade_date.isoformat(),
              str(inv.canonical_units), str(inv.gross_value))
        ordinal = group_ordinal.get(gk, 0)
        group_ordinal[gk] = ordinal + 1

        if len(cands) == 0:
            result.candidates.append(_unmatched_investment(inv, ordinal))
            continue
        if len(cands) > 1 or contested:
            result.candidates.append(_ambiguous(inv, cands, ordinal))
            continue

        cash = cands[0]
        consumed_cash.add(cash.location.row_number)
        result.candidates.append(_pair(inv, cash, ordinal))

    # A trade cash row that no investment row could match at all is
    # UNMATCHED_CASH. One that *was* a candidate for an ambiguous investment
    # row is left to that AMBIGUOUS record (and the gate fails on ambiguity
    # regardless).
    candidate_cash = {c.location.row_number for cands in inv_candidates.values() for c in cands}
    for cash in cash_trades:
        if cash.location.row_number in consumed_cash:
            continue
        if cash.location.row_number in candidate_cash:
            continue
        result.candidates.append(_unmatched_cash(cash))

    result._n_inv_trades = len(inv_sorted)
    result._n_cash_trades = len(cash_trades)
    return result


def _deltas(inv: InvestmentSourceRecord, cash: CashSourceRecord) -> dict[str, str]:
    d = {
        "value_delta": str(abs(cash.signed_total) - inv.gross_value),
        "date_delta_days": str((cash.date - inv.trade_date).days),
    }
    if cash.units is not None:
        d["quantity_delta"] = str(abs(cash.units) - inv.canonical_units)
    return d


def _pair(inv: InvestmentSourceRecord, cash: CashSourceRecord, ordinal: int) -> MatchedTradeCandidate:
    reasons: list[str] = []
    status = MatchStatus.MATCH
    delta_days = (cash.date - inv.trade_date).days

    if inv.product_id and cash.product_id and inv.product_id == cash.product_id:
        reasons.append("product_id_exact")
    elif cash.product_name.strip().lower() == inv.security_name.strip().lower():
        reasons.append("security_name_confirmed")

    value_delta = abs(abs(cash.signed_total) - inv.gross_value)
    if value_delta == 0:
        reasons.append("gross_value_exact")
    else:
        reasons.append("gross_value_within_tolerance")
        status = MatchStatus.MATCH_WITH_MINOR_DIFFERENCE

    if delta_days == 0:
        reasons.append("same_day")
    else:
        reasons.append(f"cash_date_delta_{delta_days}d")
        status = MatchStatus.MATCH_WITH_MINOR_DIFFERENCE

    if cash.units is not None:
        if abs(cash.units) == inv.canonical_units:
            reasons.append("quantity_exact")
        else:
            reasons.append("quantity_mismatch")
            status = MatchStatus.QUANTITY_MISMATCH

    # Brokerage is deliberately absent from every amount comparison above.
    reasons.append("brokerage_excluded_from_match_amount")

    return MatchedTradeCandidate(
        match_id=_match_id(inv, cash, ordinal),
        status=status,
        side=inv.side,
        security_id=inv.product_id,
        investment_trade_date=inv.trade_date,
        cash_transaction_date=cash.date,
        date_delta_days=delta_days,
        date_relation=_date_relation(delta_days),
        raw_quantity=inv.raw_quantity,
        canonical_units_candidate=inv.canonical_units,
        investment_gross_value=inv.gross_value,
        cash_total=cash.signed_total,
        raw_brokerage=inv.raw_brokerage,
        canonical_brokerage=inv.canonical_brokerage,
        brokerage_source_status=inv.brokerage_source_status.value,
        match_reasons=tuple(reasons),
        reconciliation_deltas=_deltas(inv, cash),
        investment_row=inv.location.row_number,
        cash_row=cash.location.row_number,
        investment_file_sha256=inv.location.sanitised_file_sha256,
        cash_file_sha256=cash.location.sanitised_file_sha256,
    )


def _bare(inv: InvestmentSourceRecord, ordinal: int, status: MatchStatus,
          reasons: tuple[str, ...]) -> MatchedTradeCandidate:
    return MatchedTradeCandidate(
        match_id=_match_id(inv, None, ordinal), status=status, side=inv.side,
        security_id=inv.product_id, investment_trade_date=inv.trade_date,
        cash_transaction_date=None, date_delta_days=None, date_relation=None,
        raw_quantity=inv.raw_quantity, canonical_units_candidate=inv.canonical_units,
        investment_gross_value=inv.gross_value, cash_total=None,
        raw_brokerage=inv.raw_brokerage, canonical_brokerage=inv.canonical_brokerage,
        brokerage_source_status=inv.brokerage_source_status.value,
        match_reasons=reasons, reconciliation_deltas={},
        investment_row=inv.location.row_number, cash_row=None,
        investment_file_sha256=inv.location.sanitised_file_sha256, cash_file_sha256=None,
    )


def _unmatched_investment(inv: InvestmentSourceRecord, ordinal: int) -> MatchedTradeCandidate:
    return _bare(inv, ordinal, MatchStatus.UNMATCHED_INVESTMENT,
                 ("no_cash_row_matched_side_security_value_date",))


def _ambiguous(inv: InvestmentSourceRecord, cands: list[CashSourceRecord],
               ordinal: int) -> MatchedTradeCandidate:
    return _bare(inv, ordinal, MatchStatus.AMBIGUOUS,
                 (f"{len(cands)}_equally_plausible_cash_rows", "not_resolved_by_row_order"))


def _unmatched_cash(cash: CashSourceRecord) -> MatchedTradeCandidate:
    return MatchedTradeCandidate(
        match_id=hashlib.sha256(
            f"UNMATCHEDCASH|{cash.cash_class.value}|{cash.product_id}|"
            f"{cash.date.isoformat()}|{cash.signed_total}".encode()).hexdigest()[:16],
        status=MatchStatus.UNMATCHED_CASH,
        side=TradeSide.BUY if cash.cash_class is CashClass.TRADE_BUY_CASH else TradeSide.SELL,
        security_id=cash.product_id, investment_trade_date=cash.date,
        cash_transaction_date=cash.date, date_delta_days=0, date_relation=DateRelation.SAME_DAY,
        raw_quantity=cash.units or Decimal("0"),
        canonical_units_candidate=abs(cash.units) if cash.units is not None else Decimal("0"),
        investment_gross_value=abs(cash.signed_total), cash_total=cash.signed_total,
        raw_brokerage=None, canonical_brokerage=Decimal("0.00"), brokerage_source_status="N/A",
        match_reasons=("no_investment_row_matched",), reconciliation_deltas={},
        investment_row=-1, cash_row=cash.location.row_number,
        investment_file_sha256="-", cash_file_sha256=cash.location.sanitised_file_sha256,
    )
