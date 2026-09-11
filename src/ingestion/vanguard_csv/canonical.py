"""Structured CSV -> canonical transaction *candidates* (Step 9B, Stage 3).

A `CandidateSet` is a privacy-safe, deterministic, idempotent rendering of the
two Vanguard exports in the application's own canonical vocabulary. It is NOT
promoted over the PDF-derived ledger, does not touch the `transactions` table,
and does not change any accounting rule. Stage 4 reconciles it against the
PDF ledger; only then (Stage 4D, after the GO/NO-GO gate) does authority move.

One matched trade -> ONE `TradeCandidate` (never a BUY plus a separate cash
transaction). Non-trade cash rows -> one `CashCandidate` each. The engine
adapter in `engine_projection.py` expands trades into the (BUY, TRANSFER, FEE)
shape the *existing* engine consumes -- that is a read model for verification,
not a second canonical representation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from src.ingestion.vanguard_csv.records import (
    BrokerageSourceStatus, CashClass, CashSourceRecord, InvestmentSourceRecord,
    TradeSide,
)
from src.ingestion.vanguard_csv.securities_map import SecurityResolver
from src.ingestion.vanguard_csv.trade_match import MatchResult, MatchStatus
from src.models import SecurityType, TxnType
from src.normalisation.transactions import income_type_for


class ClassificationStatus(str, Enum):
    CLASSIFIED = "CLASSIFIED"
    NEEDS_RECONCILIATION = "NEEDS_RECONCILIATION"   # deferred to Stage 4
    UNRESOLVED_SECURITY = "UNRESOLVED_SECURITY"


@dataclass(frozen=True)
class SourceRef:
    """Privacy-safe pointer to one sanitised Vanguard row."""
    kind: str                 # INVESTMENT_TXN_CSV | CASH_TXN_CSV
    file_sha256: str
    row_number: int
    raw_type: str
    raw_amount: str            # signed source figure as text (Total, or Value)
    raw_quantity: str | None = None
    raw_brokerage: str | None = None   # literally "null" when the source cell was blank


@dataclass(frozen=True)
class TradeCandidate:
    canonical_id: str
    source_method: str                 # STRUCTURED_CSV
    type: TxnType                       # BUY | SELL
    security_id: str | None
    security_type: str | None
    trade_date: date
    cash_effective_date: date
    canonical_units: Decimal           # unsigned -- engine convention
    raw_quantity: Decimal              # signed exactly as exported
    price: Decimal
    gross_amount: Decimal              # unsigned gross consideration (investment Value)
    cash_effect: Decimal               # signed cash movement (cash CSV Buy/Sell Total, == +/-gross)
    raw_brokerage: Decimal | None
    canonical_brokerage: Decimal
    brokerage_source_status: str
    # Net consideration for cost basis / proceeds, following the established
    # engine rule (Stage 4 evidence from the PDF ledger): BUY = gross + brokerage,
    # SELL = -(gross - brokerage). None only if brokerage is genuinely unknown.
    net_amount: Decimal
    classification_status: ClassificationStatus
    match_id: str
    investment_source: SourceRef
    cash_source: SourceRef
    # canonical id of the separate brokerage FEE event, when brokerage > 0
    brokerage_fee_id: str | None = None
    notes: tuple[str, ...] = ()

    @property
    def economic_fingerprint(self) -> str:
        return _fp("CSVTRADE", self.type.value, self.security_id, self.trade_date,
                   self.canonical_units, self.price, self.gross_amount)


@dataclass(frozen=True)
class CashCandidate:
    canonical_id: str
    source_method: str
    type: TxnType                       # DEPOSIT | WITHDRAWAL | DIVIDEND | DISTRIBUTION | INTEREST | FEE
    security_id: str | None
    security_type: str | None
    effective_date: date
    signed_amount: Decimal             # exactly as exported: credit > 0, debit < 0
    description: str                   # sanitised
    source_transaction_type: str       # verbatim Vanguard label
    classification_method: str         # SECURITY_TYPE_NORMALIZATION | DIRECT_TYPE_MAP | ...
    classification_status: ClassificationStatus
    source_semantic: str | None        # e.g. DEPOSIT_REVERSAL_CANDIDATE, POSITIVE_FEE_CANDIDATE
    cash_source: SourceRef
    notes: tuple[str, ...] = ()

    @property
    def economic_fingerprint(self) -> str:
        return _fp("CSVCASH", self.source_transaction_type, self.effective_date,
                   self.signed_amount, self.security_id, _slug(self.description))


@dataclass
class CandidateSet:
    investment_file_sha256: str
    cash_file_sha256: str
    trades: list[TradeCandidate] = field(default_factory=list)
    cash: list[CashCandidate] = field(default_factory=list)
    unmatched_investment_rows: list[int] = field(default_factory=list)
    unmatched_cash_rows: list[int] = field(default_factory=list)
    ambiguous_rows: list[int] = field(default_factory=list)

    @property
    def all_ids(self) -> list[str]:
        return [t.canonical_id for t in self.trades] + [c.canonical_id for c in self.cash]

    def type_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.trades:
            out[t.type.value] = out.get(t.type.value, 0) + 1
        for c in self.cash:
            key = c.source_semantic or c.type.value
            out[key] = out.get(key, 0) + 1
        return out

    def unresolved(self) -> list[str]:
        return (
            [t.canonical_id for t in self.trades
             if t.classification_status is not ClassificationStatus.CLASSIFIED]
            + [c.canonical_id for c in self.cash
               if c.classification_status is not ClassificationStatus.CLASSIFIED]
        )


# -- identity helpers -------------------------------------------------------

def _fp(*parts: object) -> str:
    payload = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def _slug(text: str) -> str:
    """A short stable discriminator from a sanitised description -- letters and
    `#` only, so two structurally different descriptions stay distinct without
    carrying any figure."""
    keep = "".join(ch for ch in (text or "").lower() if ch.isalpha() or ch == "#")
    return keep[:32]


def _canonical_id(fingerprint: str, ordinal: int) -> str:
    return _fp(fingerprint, "ord", ordinal)


# -- construction ---------------------------------------------------------

_TRADE_TYPE = {TradeSide.BUY: TxnType.BUY, TradeSide.SELL: TxnType.SELL}


def _inv_ref(rec: InvestmentSourceRecord) -> SourceRef:
    return SourceRef(
        kind="INVESTMENT_TXN_CSV", file_sha256=rec.location.sanitised_file_sha256,
        row_number=rec.location.row_number, raw_type=rec.raw_type,
        raw_amount=str(rec.gross_value), raw_quantity=str(rec.raw_quantity),
        raw_brokerage="null" if rec.raw_brokerage is None else str(rec.raw_brokerage),
    )


def _cash_ref(rec: CashSourceRecord) -> SourceRef:
    return SourceRef(
        kind="CASH_TXN_CSV", file_sha256=rec.location.sanitised_file_sha256,
        row_number=rec.location.row_number, raw_type=rec.raw_type,
        raw_amount=str(rec.signed_total),
        raw_quantity=None if rec.units is None else str(rec.units),
    )


def build_candidates(
    match: MatchResult,
    investment_records: list[InvestmentSourceRecord],
    cash_records: list[CashSourceRecord],
    resolver: SecurityResolver,
) -> CandidateSet:
    inv_by_row = {r.location.row_number: r for r in investment_records}
    cash_by_row = {r.location.row_number: r for r in cash_records}

    inv_hash = investment_records[0].location.sanitised_file_sha256 if investment_records else "-"
    cash_hash = cash_records[0].location.sanitised_file_sha256 if cash_records else "-"
    cs = CandidateSet(investment_file_sha256=inv_hash, cash_file_sha256=cash_hash)

    ordinals: dict[str, int] = {}

    def next_ordinal(fp: str) -> int:
        n = ordinals.get(fp, 0)
        ordinals[fp] = n + 1
        return n

    long_names = {r.product_id: r.security_name for r in investment_records if r.product_id}
    brokerage_rows = [r for r in cash_records if r.cash_class is CashClass.TRADE_BROKERAGE_CASH]
    consumed_brokerage_rows: set[int] = set()

    # -- trades: one MatchedTradeCandidate -> one TradeCandidate --------
    for m in match.matched:
        inv = inv_by_row[m.investment_row]
        cash = cash_by_row[m.cash_row]
        resolved = resolver.resolve(product_id=inv.product_id, name=inv.security_name)
        fp = _fp("CSVTRADE", _TRADE_TYPE[inv.side].value, inv.product_id, inv.trade_date,
                 inv.canonical_units, inv.unit_price, inv.gross_value)
        ttype = _TRADE_TYPE[inv.side]
        brk = inv.canonical_brokerage
        # Established engine rule (PDF ledger, confirmed Stage 4): BUY net
        # consideration = gross + brokerage; SELL = -(gross - brokerage).
        net_amount = (inv.gross_value + brk) if ttype is TxnType.BUY else -(inv.gross_value - brk)

        trade_id = _canonical_id(fp, next_ordinal(fp))
        brokerage_fee_id: str | None = None
        if brk > 0:
            brk_row = _match_brokerage_row(
                inv, brokerage_rows, consumed_brokerage_rows, long_names.get(inv.product_id, ""))
            fee = _brokerage_fee(trade_id, inv, brk, brk_row, next_ordinal)
            cs.cash.append(fee)
            brokerage_fee_id = fee.canonical_id
            if brk_row is not None:
                consumed_brokerage_rows.add(brk_row.location.row_number)

        cs.trades.append(TradeCandidate(
            canonical_id=trade_id,
            source_method="STRUCTURED_CSV",
            type=ttype,
            security_id=inv.product_id,
            security_type=(resolved.security_type.value if resolved else None),
            trade_date=inv.trade_date,
            cash_effective_date=cash.date,
            canonical_units=inv.canonical_units,
            raw_quantity=inv.raw_quantity,
            price=inv.unit_price,
            gross_amount=inv.gross_value,
            cash_effect=cash.signed_total,
            raw_brokerage=inv.raw_brokerage,
            canonical_brokerage=brk,
            brokerage_source_status=inv.brokerage_source_status.value,
            net_amount=net_amount,
            classification_status=ClassificationStatus.CLASSIFIED,
            match_id=m.match_id,
            investment_source=_inv_ref(inv),
            cash_source=_cash_ref(cash),
            brokerage_fee_id=brokerage_fee_id,
        ))

    for c in match.by_status(MatchStatus.UNMATCHED_INVESTMENT):
        cs.unmatched_investment_rows.append(c.investment_row)
    for c in match.by_status(MatchStatus.UNMATCHED_CASH):
        cs.unmatched_cash_rows.append(c.cash_row)
    for c in match.by_status(MatchStatus.AMBIGUOUS):
        cs.ambiguous_rows.append(c.investment_row)

    # -- non-trade cash rows (brokerage rows already consumed above) -------
    for rec in cash_records:
        if (rec.cash_class is CashClass.TRADE_BROKERAGE_CASH
                and rec.location.row_number in consumed_brokerage_rows):
            continue
        cand = _cash_candidate(rec, resolver, next_ordinal)
        if cand is not None:
            cs.cash.append(cand)

    return cs


def _match_brokerage_row(inv: InvestmentSourceRecord, rows: list[CashSourceRecord],
                         consumed: set[int], long_name: str) -> CashSourceRecord | None:
    """The cash-CSV `... Transaction fee for <security> <Side>` row for this
    trade: security long-name + side word in the description, amount equal to
    the trade's brokerage, cash date on/after the trade date within a window."""
    side_word = "buy" if inv.side is TradeSide.BUY else "sell"
    name_key = long_name.strip().lower()
    best: CashSourceRecord | None = None
    for r in rows:
        if r.location.row_number in consumed:
            continue
        low = r.product_name.lower()
        if side_word not in low:
            continue
        if name_key and name_key not in low:
            continue
        if abs(r.signed_total) != inv.canonical_brokerage:
            continue
        if not (0 <= (r.date - inv.trade_date).days <= 7):
            continue
        if best is None or r.date < best.date:
            best = r
    return best


def _brokerage_fee(trade_id: str, inv: InvestmentSourceRecord, brk: Decimal,
                   row: CashSourceRecord | None, next_ordinal) -> CashCandidate:
    when = row.date if row is not None else inv.trade_date
    fp = _fp("CSVFEE", "BROKERAGE", trade_id, when, brk)
    src = _cash_ref(row) if row is not None else SourceRef(
        kind="INVESTMENT_TXN_CSV", file_sha256=inv.location.sanitised_file_sha256,
        row_number=inv.location.row_number, raw_type="Brokerage (investment CSV column)",
        raw_amount=str(brk),
    )
    return CashCandidate(
        canonical_id=_canonical_id(fp, next_ordinal(fp)),
        source_method="STRUCTURED_CSV",
        type=TxnType.FEE,
        security_id=inv.product_id,
        security_type=None,
        effective_date=when,
        signed_amount=-brk,
        description="Trade brokerage",
        source_transaction_type="Fees and Charges" if row is not None else "Brokerage",
        classification_method="TRADE_BROKERAGE",
        classification_status=ClassificationStatus.CLASSIFIED,
        source_semantic="TRADE_BROKERAGE",
        cash_source=src,
        notes=(("brokerage cash row matched to trade",) if row is not None
               else ("no cash brokerage row matched -- dated on trade date",)),
    )


def _cash_candidate(rec: CashSourceRecord, resolver: SecurityResolver,
                    next_ordinal) -> CashCandidate | None:
    cls = rec.cash_class
    if cls in (CashClass.TRADE_BUY_CASH, CashClass.TRADE_SELL_CASH):
        return None   # handled as the cash leg of a TradeCandidate

    security_id: str | None = None
    security_type: str | None = None
    status = ClassificationStatus.CLASSIFIED
    method = "DIRECT_TYPE_MAP"
    semantic: str | None = None
    notes: list[str] = []

    if cls is CashClass.DEPOSIT:
        ctype = TxnType.DEPOSIT
        if rec.signed_total < 0:
            # Stage 4A: a dishonoured/reversed funding transfer. Kept as a
            # signed-negative DEPOSIT (the existing engine model -- a
            # contribution adjustment, exactly as the PDF ledger's "Failed
            # Direct Debit" rows), so it nets its paired positive deposit and
            # never permanently inflates contributed capital. Not a WITHDRAWAL.
            semantic = "DEPOSIT_REVERSAL"
            notes.append("negative Deposit -- dishonoured funding transfer, signed contribution adjustment")
    elif cls is CashClass.WITHDRAWAL:
        ctype = TxnType.WITHDRAWAL
    elif cls is CashClass.INTEREST:
        ctype = TxnType.INTEREST
    elif cls is CashClass.ADMIN_FEE:
        ctype = TxnType.FEE
        semantic = "ADMIN_FEE"
        if rec.signed_total > 0:  # not expected for OngoingAdminChargeByValue
            status = ClassificationStatus.NEEDS_RECONCILIATION
            semantic = "POSITIVE_ADMIN_FEE"
            notes.append("positive OngoingAdminChargeByValue -- unexpected, flagged")
    elif cls is CashClass.FEE_REVERSAL:
        # Stage 4B: an explicit "Reversal: OngoingAdminChargeByValue" -- a
        # fee refund. Kept as a signed-positive FEE (a fee adjustment), so it
        # nets its paired charge. Sign is NOT forced negative.
        ctype = TxnType.FEE
        semantic = "FEE_REVERSAL"
        method = "FEE_REVERSAL"
        notes.append("explicit fee reversal -- signed-positive FEE adjustment, nets its paired charge")
    elif cls is CashClass.TRADE_BROKERAGE_CASH:
        # Should have been consumed as a trade's brokerage FEE. Reaching here
        # means it did not match any trade -- keep it as a standalone FEE and
        # flag for reconciliation rather than dropping it.
        ctype = TxnType.FEE
        status = ClassificationStatus.NEEDS_RECONCILIATION
        semantic = "UNMATCHED_TRADE_BROKERAGE"
        method = "TRADE_BROKERAGE"
        notes.append("brokerage cash row not matched to any trade")
    elif cls is CashClass.DISTRIBUTION_INCOME:
        method = "SECURITY_TYPE_NORMALIZATION"
        resolved = resolver.resolve(product_id=rec.product_id, name=rec.product_name)
        if resolved is None:
            ctype = TxnType.DISTRIBUTION       # neutral placeholder; flagged unresolved
            status = ClassificationStatus.UNRESOLVED_SECURITY
            notes.append("distribution security could not be resolved -- not guessed")
        else:
            security_id = resolved.security_id
            security_type = resolved.security_type.value
            ctype = income_type_for(resolved.security_type)  # SHARE -> DIVIDEND, ETF/fund -> DISTRIBUTION
    else:  # pragma: no cover -- every CashClass is handled above
        raise AssertionError(f"unhandled cash class {cls}")

    fp = _fp("CSVCASH", rec.raw_type, rec.date, rec.signed_total, security_id,
             _slug(rec.product_name))
    return CashCandidate(
        canonical_id=_canonical_id(fp, next_ordinal(fp)),
        source_method="STRUCTURED_CSV",
        type=ctype,
        security_id=security_id,
        security_type=security_type,
        effective_date=rec.date,
        signed_amount=rec.signed_total,
        description=rec.product_name,
        source_transaction_type=rec.raw_type,
        classification_method=method,
        classification_status=status,
        source_semantic=semantic,
        cash_source=_cash_ref(rec),
        notes=tuple(notes),
    )


__all__ = [
    "CandidateSet", "TradeCandidate", "CashCandidate", "ClassificationStatus",
    "SourceRef", "build_candidates",
]
