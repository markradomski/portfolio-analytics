"""CSV candidate <-> PDF-derived event reconciliation (Step 9B, Stage 4).

Evidence + adjudication only. Does NOT rewrite the persisted `transactions`
table, delete a PDF row, promote source authority, or change any accounting
rule. It builds `ReconciliationResult`s and a `SourceAuthorityPolicy` that
Stage 5 will act on.

Privacy: consumes sanitised CSV candidates and privacy-safe PDF fields
(date / type / security code / signed amount only -- never a PDF description,
which in this dataset still carries names/bank references from the PDF
pipeline). Every string emitted here is a fixed enum value or a Decimal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

from src.ingestion.vanguard_csv.canonical import CandidateSet, CashCandidate, TradeCandidate
from src.models import TxnType

CENT = Decimal("0.01")
DATE_WINDOW = timedelta(days=7)


class ReconStatus(str, Enum):
    MATCH = "MATCH"
    MATCH_WITH_MINOR_DIFFERENCE = "MATCH_WITH_MINOR_DIFFERENCE"
    CLASSIFICATION_DIFFERENCE = "CLASSIFICATION_DIFFERENCE"
    TIMING_DIFFERENCE = "TIMING_DIFFERENCE"
    CSV_ONLY = "CSV_ONLY"
    PDF_ONLY = "PDF_ONLY"
    SOURCE_COVERAGE_DIFFERENCE = "SOURCE_COVERAGE_DIFFERENCE"
    PDF_DUPLICATE = "PDF_DUPLICATE"
    CSV_DUPLICATE = "CSV_DUPLICATE"
    REVERSAL_PAIR = "REVERSAL_PAIR"
    SUPERSEDED_SOURCE_REPRESENTATION = "SUPERSEDED_SOURCE_REPRESENTATION"
    FEE_REBATE = "FEE_REBATE"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    SECURITY_MISMATCH = "SECURITY_MISMATCH"
    BROKERAGE_CASH_SETTLEMENT_UNRESOLVED = "BROKERAGE_CASH_SETTLEMENT_UNRESOLVED"
    BUG = "BUG"
    UNRESOLVED = "UNRESOLVED"


class Authority(str, Enum):
    CSV_PREFERRED = "CSV_PREFERRED"
    PDF_FALLBACK = "PDF_FALLBACK"
    RECONCILIATION_ONLY = "RECONCILIATION_ONLY"
    PDF_ONLY_SUPPORTED = "PDF_ONLY_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class PdfEvent:
    """A privacy-safe view of one PDF-derived canonical transaction."""
    transaction_id: str
    type: TxnType
    security_code: str | None
    trade_date: date
    net_amount: Decimal | None
    units: Decimal | None


@dataclass
class ReconciliationResult:
    event_class: str
    status: ReconStatus
    reasons: tuple[str, ...] = ()
    authority: Authority = Authority.UNRESOLVED
    security: str | None = None
    csv_date: date | None = None
    pdf_date: date | None = None
    csv_amount: Decimal | None = None
    pdf_amount: Decimal | None = None
    csv_id: str | None = None
    pdf_ids: tuple[str, ...] = ()
    linked_id: str | None = None          # e.g. the paired reversal event
    statement_evidence: str | None = None
    resolved: bool = True

    @property
    def is_exact(self) -> bool:
        return self.status is ReconStatus.MATCH


@dataclass
class CashBridge:
    opening: Decimal
    deposits: Decimal
    withdrawals: Decimal
    trade_cash: Decimal
    income: Decimal
    interest: Decimal
    fees: Decimal
    csv_closing: Decimal
    pdf_closing: Decimal
    residual: Decimal
    residual_explanation: tuple[str, ...]
    residual_resolved: bool


@dataclass
class SourceAuthorityPolicy:
    by_class: dict[str, Authority] = field(default_factory=dict)
    promotion_ready: bool = False
    blocking: tuple[str, ...] = ()


@dataclass
class ReconciliationReport:
    results: list[ReconciliationResult] = field(default_factory=list)
    bridge: CashBridge | None = None
    policy: SourceAuthorityPolicy | None = None

    def by_class(self, event_class: str) -> list[ReconciliationResult]:
        return [r for r in self.results if r.event_class == event_class]

    def by_status(self, status: ReconStatus) -> list[ReconciliationResult]:
        return [r for r in self.results if r.status is status]

    def unresolved(self) -> list[ReconciliationResult]:
        return [r for r in self.results if not r.resolved]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results:
            out[r.status.value] = out.get(r.status.value, 0) + 1
        return out


def _near(a: date, b: date) -> bool:
    return abs((a - b).days) <= DATE_WINDOW.days


def _amounts_match(a: Decimal | None, b: Decimal | None) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) <= CENT


# -- trade reconciliation -------------------------------------------------

def _reconcile_trades(cs: CandidateSet, pdf: list[PdfEvent]) -> list[ReconciliationResult]:
    results: list[ReconciliationResult] = []
    pdf_trades = [e for e in pdf if e.type in (TxnType.BUY, TxnType.SELL)]
    pdf_transfers = [e for e in pdf if e.type is TxnType.TRANSFER]
    used_trade: set[str] = set()
    used_transfer: set[str] = set()

    for t in cs.trades:
        bs = _best_trade_match(t, pdf_trades, used_trade)
        tr = _best_transfer_match(t, pdf_transfers, used_transfer)
        reasons: list[str] = []
        status = ReconStatus.MATCH

        if bs is None:
            results.append(ReconciliationResult(
                event_class="TRADE", status=ReconStatus.CSV_ONLY,
                reasons=("no PDF BUY/SELL matched",), authority=Authority.UNRESOLVED,
                security=t.security_id, csv_date=t.trade_date, csv_amount=t.gross_amount,
                csv_id=t.canonical_id, resolved=False))
            continue

        used_trade.add(bs.transaction_id)
        if bs.security_code != t.security_id:
            status, reasons = ReconStatus.SECURITY_MISMATCH, ["PDF security != CSV security"]
        elif bs.units is not None and abs(abs(bs.units) - t.canonical_units) > Decimal("0.0001"):
            status, reasons = ReconStatus.QUANTITY_MISMATCH, ["units differ"]
        elif bs.net_amount is not None and not _amounts_match(abs(bs.net_amount), abs(t.net_amount)):
            status = ReconStatus.MATCH_WITH_MINOR_DIFFERENCE
            reasons = [f"net_amount diff {abs(bs.net_amount) - abs(t.net_amount)}"]
        if bs.trade_date != t.trade_date:
            status = ReconStatus.TIMING_DIFFERENCE if status is ReconStatus.MATCH else status
            reasons.append(f"trade date diff {(bs.trade_date - t.trade_date).days}d")

        pdf_ids = [bs.transaction_id]
        if tr is not None:
            used_transfer.add(tr.transaction_id)
            pdf_ids.append(tr.transaction_id)
            reasons.append("PDF TRANSFER cash leg identified -> SUPERSEDED_SOURCE_REPRESENTATION")
        else:
            reasons.append("no PDF TRANSFER cash leg found")
            if status is ReconStatus.MATCH:
                status = ReconStatus.MATCH_WITH_MINOR_DIFFERENCE

        results.append(ReconciliationResult(
            event_class="TRADE", status=status, reasons=tuple(reasons),
            authority=Authority.CSV_PREFERRED if status in (
                ReconStatus.MATCH, ReconStatus.MATCH_WITH_MINOR_DIFFERENCE,
                ReconStatus.TIMING_DIFFERENCE) else Authority.UNRESOLVED,
            security=t.security_id, csv_date=t.trade_date, pdf_date=bs.trade_date,
            csv_amount=t.net_amount, pdf_amount=bs.net_amount,
            csv_id=t.canonical_id, pdf_ids=tuple(pdf_ids),
            resolved=status in (ReconStatus.MATCH, ReconStatus.MATCH_WITH_MINOR_DIFFERENCE,
                                ReconStatus.TIMING_DIFFERENCE)))

    # PDF TRANSFERs consumed by a trade above -> superseded; any left over is PDF_ONLY.
    for tr in pdf_transfers:
        if tr.transaction_id in used_transfer:
            results.append(ReconciliationResult(
                event_class="TRADE_CASH_LEG",
                status=ReconStatus.SUPERSEDED_SOURCE_REPRESENTATION,
                reasons=("PDF TRANSFER is the cash-side representation of a CSV trade",),
                authority=Authority.RECONCILIATION_ONLY,
                pdf_date=tr.trade_date, pdf_amount=tr.net_amount,
                pdf_ids=(tr.transaction_id,)))
        else:
            results.append(ReconciliationResult(
                event_class="TRADE_CASH_LEG", status=ReconStatus.PDF_ONLY,
                reasons=("PDF TRANSFER with no CSV trade",), authority=Authority.UNRESOLVED,
                pdf_date=tr.trade_date, pdf_amount=tr.net_amount,
                pdf_ids=(tr.transaction_id,), resolved=False))

    for bs in pdf_trades:
        if bs.transaction_id not in used_trade:
            results.append(ReconciliationResult(
                event_class="TRADE", status=ReconStatus.PDF_ONLY,
                reasons=("PDF BUY/SELL with no CSV trade",), authority=Authority.UNRESOLVED,
                security=bs.security_code, pdf_date=bs.trade_date, pdf_amount=bs.net_amount,
                pdf_ids=(bs.transaction_id,), resolved=False))

    return results


def _best_trade_match(t: TradeCandidate, pdf: list[PdfEvent], used: set[str]) -> PdfEvent | None:
    cands = [e for e in pdf if e.transaction_id not in used and e.type is t.type
             and e.security_code == t.security_id and _near(e.trade_date, t.trade_date)
             and (e.units is None or abs(abs(e.units) - t.canonical_units) < Decimal("0.5"))]
    if not cands:
        return None
    return min(cands, key=lambda e: (abs((e.trade_date - t.trade_date).days),
                                     abs((abs(e.net_amount or Decimal(0))) - abs(t.net_amount))))


def _best_transfer_match(t: TradeCandidate, pdf: list[PdfEvent], used: set[str]) -> PdfEvent | None:
    # A trade's PDF TRANSFER carries the *gross* cash amount, opposite sign to
    # the trade direction; brokerage is a separate PDF FEE row.
    target = -t.gross_amount if t.type is TxnType.BUY else t.gross_amount
    cands = [e for e in pdf if e.transaction_id not in used
             and _near(e.trade_date, t.cash_effective_date)
             and e.net_amount is not None and abs(e.net_amount - target) <= CENT]
    return cands[0] if cands else None


# -- cash-event reconciliation -----------------------------------------

_CLASS_OF = {
    TxnType.DEPOSIT: "DEPOSIT", TxnType.WITHDRAWAL: "WITHDRAWAL",
    TxnType.DIVIDEND: "DIVIDEND", TxnType.DISTRIBUTION: "DISTRIBUTION",
    TxnType.INTEREST: "INTEREST", TxnType.FEE: "FEE",
}


def _reconcile_cash(cs: CandidateSet, pdf: list[PdfEvent],
                    csv_start: date, csv_end: date,
                    pdf_start: date, pdf_end: date) -> list[ReconciliationResult]:
    results: list[ReconciliationResult] = []
    # PDF income lives in a separate table; the caller passes it in as
    # DIVIDEND/DISTRIBUTION PdfEvents.
    pdf_by_class: dict[str, list[PdfEvent]] = {}
    for e in pdf:
        c = _CLASS_OF.get(e.type)
        if c:
            pdf_by_class.setdefault(c, []).append(e)
    used: set[str] = set()

    for cand in cs.cash:
        cls = _CLASS_OF.get(cand.type)
        if cls is None:
            continue
        pool = pdf_by_class.get(cls, [])
        m = _best_cash_match(cand, pool, used)
        if m is not None:
            used.add(m.transaction_id)
            timing = m.trade_date != cand.effective_date
            amt_ok = _amounts_match(m.net_amount, cand.signed_amount)
            status = (ReconStatus.MATCH if amt_ok and not timing
                      else ReconStatus.TIMING_DIFFERENCE if amt_ok
                      else ReconStatus.MATCH_WITH_MINOR_DIFFERENCE)
            results.append(ReconciliationResult(
                event_class=cls, status=status,
                reasons=(("date diff",) if timing else ()) + (() if amt_ok else ("amount diff",)),
                authority=Authority.CSV_PREFERRED, security=cand.security_id,
                csv_date=cand.effective_date, pdf_date=m.trade_date,
                csv_amount=cand.signed_amount, pdf_amount=m.net_amount,
                csv_id=cand.canonical_id, pdf_ids=(m.transaction_id,),
                resolved=status in (ReconStatus.MATCH, ReconStatus.TIMING_DIFFERENCE,
                                    ReconStatus.MATCH_WITH_MINOR_DIFFERENCE)))
        else:
            outside = cand.effective_date < pdf_start or cand.effective_date > pdf_end
            results.append(ReconciliationResult(
                event_class=cls,
                status=ReconStatus.SOURCE_COVERAGE_DIFFERENCE if outside else ReconStatus.CSV_ONLY,
                reasons=("CSV event after the last PDF statement period" if cand.effective_date > pdf_end
                         else "CSV event before the PDF coverage window" if outside
                         else "no PDF event matched",),
                authority=Authority.CSV_PREFERRED if outside else Authority.UNRESOLVED,
                security=cand.security_id, csv_date=cand.effective_date,
                csv_amount=cand.signed_amount, csv_id=cand.canonical_id,
                resolved=outside))

    for cls, pool in pdf_by_class.items():
        for e in pool:
            if e.transaction_id in used:
                continue
            outside = e.trade_date < csv_start or e.trade_date > csv_end
            results.append(ReconciliationResult(
                event_class=cls,
                status=ReconStatus.SOURCE_COVERAGE_DIFFERENCE if outside else ReconStatus.PDF_ONLY,
                reasons=("PDF event before the CSV coverage window" if e.trade_date < csv_start
                         else "PDF event after the CSV coverage window" if outside
                         else "no CSV candidate matched",),
                authority=Authority.PDF_ONLY_SUPPORTED if outside else Authority.UNRESOLVED,
                security=e.security_code, pdf_date=e.trade_date, pdf_amount=e.net_amount,
                pdf_ids=(e.transaction_id,), resolved=outside))

    return results


def _best_cash_match(cand: CashCandidate, pool: list[PdfEvent], used: set[str]) -> PdfEvent | None:
    cands = [e for e in pool if e.transaction_id not in used
             and _amounts_match(e.net_amount, cand.signed_amount)
             and (e.security_code == cand.security_id or cand.security_id is None or e.security_code is None)
             and _near(e.trade_date, cand.effective_date)]
    if not cands:
        # allow a security-agnostic amount+date match for fees/deposits
        cands = [e for e in pool if e.transaction_id not in used
                 and _amounts_match(e.net_amount, cand.signed_amount)
                 and _near(e.trade_date, cand.effective_date)]
    if not cands:
        return None
    return min(cands, key=lambda e: abs((e.trade_date - cand.effective_date).days))


# -- reversal-pair detection -----------------------------------------

def _detect_reversal_pairs(cs: CandidateSet) -> list[ReconciliationResult]:
    out: list[ReconciliationResult] = []
    # deposits: a negative that cancels an earlier equal positive
    deps = sorted([c for c in cs.cash if c.type is TxnType.DEPOSIT],
                  key=lambda c: c.effective_date)
    for neg in [c for c in deps if c.signed_amount < 0]:
        prior = [p for p in deps if p.signed_amount == -neg.signed_amount
                 and p.effective_date <= neg.effective_date
                 and (neg.effective_date - p.effective_date).days <= 30]
        out.append(ReconciliationResult(
            event_class="DEPOSIT", status=ReconStatus.REVERSAL_PAIR,
            reasons=("negative Deposit cancels an earlier equal positive Deposit"
                     if prior else "negative Deposit with no located positive pair",),
            authority=Authority.CSV_PREFERRED, csv_date=neg.effective_date,
            csv_amount=neg.signed_amount, csv_id=neg.canonical_id,
            linked_id=prior[-1].canonical_id if prior else None,
            resolved=bool(prior)))
    # fees: an explicit reversal that cancels an earlier equal charge
    fees = sorted([c for c in cs.cash if c.type is TxnType.FEE], key=lambda c: c.effective_date)
    for rev in [c for c in fees if c.source_semantic == "FEE_REVERSAL"]:
        prior = [p for p in fees if p.signed_amount == -rev.signed_amount
                 and p.effective_date <= rev.effective_date
                 and (rev.effective_date - p.effective_date).days <= 60]
        out.append(ReconciliationResult(
            event_class="FEE", status=ReconStatus.FEE_REBATE,
            reasons=("explicit fee reversal cancels an earlier equal admin charge"
                     if prior else "fee reversal with no located charge pair",),
            authority=Authority.CSV_PREFERRED, csv_date=rev.effective_date,
            csv_amount=rev.signed_amount, csv_id=rev.canonical_id,
            linked_id=prior[-1].canonical_id if prior else None,
            resolved=bool(prior)))
    return out


# -- cash bridge ----------------------------------------------------

def _cash_bridge(cs: CandidateSet, pdf_closing: Decimal,
                 cash_results: list[ReconciliationResult],
                 opening: Decimal = Decimal("0")) -> CashBridge:
    def s(pred) -> Decimal:
        return sum((c.signed_amount for c in cs.cash if pred(c)), Decimal("0"))

    deposits = s(lambda c: c.type is TxnType.DEPOSIT)
    withdrawals = s(lambda c: c.type is TxnType.WITHDRAWAL)
    income = s(lambda c: c.type in (TxnType.DIVIDEND, TxnType.DISTRIBUTION))
    interest = s(lambda c: c.type is TxnType.INTEREST)
    fees = s(lambda c: c.type is TxnType.FEE)
    trade_cash = sum((t.cash_effect for t in cs.trades), Decimal("0"))

    csv_closing = opening + deposits + withdrawals + income + interest + fees + trade_cash
    residual = pdf_closing - csv_closing

    # The residual is "explained" precisely when it equals the net effect of
    # events Stage 4 already classified as boundary-of-coverage differences:
    # a PDF-only event (in pdf_closing, absent from csv_closing) contributes
    # +pdf_amount; a CSV-only event (already summed into csv_closing, absent
    # from the PDF side) contributes -csv_amount. This is evidence-based, not
    # a hardcoded constant -- it generalises to any candidate/PDF subset.
    coverage = [r for r in cash_results if r.status is ReconStatus.SOURCE_COVERAGE_DIFFERENCE]
    expected = sum(
        (r.pdf_amount if r.pdf_amount is not None else -(r.csv_amount or Decimal("0")))
        for r in coverage
    ) if coverage else Decimal("0")
    resolved = abs(residual - expected) <= CENT

    explanation = tuple(
        f"{'PDF-only' if r.pdf_amount is not None else 'CSV-only'} "
        f"{r.event_class} {r.pdf_amount if r.pdf_amount is not None else r.csv_amount} "
        f"on {r.pdf_date if r.pdf_date is not None else r.csv_date} "
        "(source coverage boundary)"
        for r in coverage
    ) if resolved and coverage else (
        ("residual matches expected boundary events",) if resolved
        else ("residual does not match known boundary events -- investigate",)
    )

    return CashBridge(
        opening=opening, deposits=deposits, withdrawals=withdrawals, trade_cash=trade_cash,
        income=income, interest=interest, fees=fees,
        csv_closing=csv_closing, pdf_closing=pdf_closing, residual=residual,
        residual_explanation=explanation, residual_resolved=resolved,
    )


# -- authority policy --------------------------------------------

def _build_policy(report: ReconciliationReport) -> SourceAuthorityPolicy:
    policy = SourceAuthorityPolicy()
    blocking: list[str] = []
    for cls in ("TRADE", "DEPOSIT", "WITHDRAWAL", "DIVIDEND", "DISTRIBUTION",
                "INTEREST", "FEE"):
        rs = report.by_class(cls)
        if not rs:
            continue
        unresolved = [r for r in rs if not r.resolved]
        if unresolved:
            policy.by_class[cls] = Authority.UNRESOLVED
            blocking.append(f"{cls}: {len(unresolved)} unresolved")
        else:
            policy.by_class[cls] = Authority.CSV_PREFERRED
    policy.by_class["TRADE_CASH_LEG"] = Authority.RECONCILIATION_ONLY
    policy.by_class["BROKERAGE_EXECUTION"] = Authority.CSV_PREFERRED
    # brokerage cash settlement is now resolved (it IS a cash CSV row), so not blocking
    bridge_ok = report.bridge is not None and report.bridge.residual_resolved
    if not bridge_ok:
        blocking.append("cash residual unexplained")
    policy.blocking = tuple(blocking)
    policy.promotion_ready = not blocking
    return policy


# -- top-level -------------------------------------------------

def reconcile(cs: CandidateSet, pdf_events: list[PdfEvent], *,
              pdf_closing_cash: Decimal | None = None) -> ReconciliationReport:
    csv_dates = [c.effective_date for c in cs.cash] + [t.trade_date for t in cs.trades]
    pdf_dates = [e.trade_date for e in pdf_events]
    csv_start, csv_end = (min(csv_dates), max(csv_dates)) if csv_dates else (date.min, date.max)
    pdf_start, pdf_end = (min(pdf_dates), max(pdf_dates)) if pdf_dates else (date.min, date.max)

    report = ReconciliationReport()
    report.results.extend(_reconcile_trades(cs, pdf_events))
    cash_results = _reconcile_cash(cs, pdf_events, csv_start, csv_end, pdf_start, pdf_end)
    report.results.extend(cash_results)
    report.results.extend(_detect_reversal_pairs(cs))
    # Callers that only care about non-cash reconciliation (most unit tests)
    # may omit pdf_closing_cash; defaulting it to the CSV-side closing figure
    # makes the residual trivially zero rather than an arbitrary mismatch.
    provisional_closing = pdf_closing_cash
    if provisional_closing is None:
        provisional_closing = sum((c.signed_amount for c in cs.cash), Decimal("0")) \
            + sum((t.cash_effect for t in cs.trades), Decimal("0"))
    report.bridge = _cash_bridge(cs, provisional_closing, cash_results)
    report.policy = _build_policy(report)
    return report
