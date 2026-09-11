"""Promote reconciled Vanguard CSV candidates into the active accounting
projection (Step 9B, Stage 5 -- MVP release).

This is the ONE place a Stage 4 `ReconciliationReport` becomes a decision
about what the existing engine actually reads. It does not add a second
accounting engine: it writes ordinary `Transaction` rows into the same
`transactions` table `Ledger.from_repository()` already reads, using the
existing schema and model unchanged. Every other table (documents, holdings,
income_events, portfolio_valuations, statement_periods, tax data,
record_sources) is left exactly as the PDF pipeline wrote it -- full source
evidence remains available for audit; only the *active* transaction rows
for the classes Stage 4 resolved are replaced.

Promotion refuses to run at all if the reconciliation is not
`promotion_ready` -- there is no partial/best-effort promotion of an
unresolved reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal

from src.database.repository import Repository
from src.ids import make_id
from src.ingestion.vanguard_csv.canonical import CandidateSet, CashCandidate, TradeCandidate
from src.ingestion.vanguard_csv.reconcile import Authority, ReconciliationReport, ReconStatus
from src.models import Document, DocumentKind, Provenance, Transaction, TxnType

ACCOUNT_ID = make_id("ACCOUNT", "primary")   # same constant the PDF pipeline uses
PROMOTED_DOCUMENT_ID = "CSV-PROMOTED"
PROMOTED_EXTRACTION_METHOD = "STRUCTURED_CSV_PROMOTED"

# Reconciliation statuses whose CSV side is safe to promote and whose PDF
# side (when present) is genuinely superseded, not merely "close enough".
_SUPERSEDES_PDF = frozenset({
    ReconStatus.MATCH, ReconStatus.MATCH_WITH_MINOR_DIFFERENCE, ReconStatus.TIMING_DIFFERENCE,
})


@dataclass
class PromotionPlan:
    ready: bool
    blocking: tuple[str, ...]
    superseded_pdf_ids: set[str] = field(default_factory=set)
    kept_pdf_ids: set[str] = field(default_factory=set)     # fallback -- stays active, informational
    new_transactions: list[Transaction] = field(default_factory=list)

    @property
    def active_type_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.new_transactions:
            out[t.type] = out.get(t.type, 0) + 1
        return out


def build_promotion_plan(cs: CandidateSet, report: ReconciliationReport) -> PromotionPlan:
    """Decide, from the Stage 4 report alone, which PDF rows are superseded
    and build the promoted Transaction rows. Refuses (ready=False) if the
    reconciliation itself is not promotion_ready, or if any individual
    result both claims CSV_PREFERRED authority and remains unresolved."""
    if report.policy is None or not report.policy.promotion_ready:
        blocking = report.policy.blocking if report.policy else ("no reconciliation policy",)
        return PromotionPlan(ready=False, blocking=blocking)

    unresolved = [r for r in report.results if not r.resolved]
    if unresolved:
        return PromotionPlan(ready=False, blocking=(
            f"{len(unresolved)} reconciliation result(s) remain unresolved",))

    superseded: set[str] = set()
    kept: set[str] = set()
    for r in report.results:
        if r.status in _SUPERSEDES_PDF or r.status is ReconStatus.SUPERSEDED_SOURCE_REPRESENTATION:
            superseded.update(r.pdf_ids)
        elif r.authority is Authority.PDF_ONLY_SUPPORTED:
            kept.update(r.pdf_ids)
        # REVERSAL_PAIR / FEE_REBATE results describe CSV-side pairing only
        # (no pdf_ids) and never affect which PDF rows are superseded/kept.

    # Each trade candidate becomes exactly the two rows the *existing*
    # engine already requires for a trade (see src/engine/ledger.py): one
    # BUY/SELL (holdings + cost basis) and its paired TRANSFER (the cash
    # side -- CASH_TYPES deliberately excludes BUY/SELL, so a trade with no
    # transfer event never moves cash and the ledger would misstate the
    # balance). This is not "an additional TRANSFER": it is the one CSV-
    # sourced replacement for the PDF TRANSFER superseded above -- net
    # active TRANSFER count for these 76 trades stays at 76, not 152.
    new_transactions = []
    for t in cs.trades:
        new_transactions.append(_trade_transaction(t))
        new_transactions.append(_transfer_transaction(t))
    new_transactions += [_cash_transaction(c) for c in cs.cash]

    return PromotionPlan(ready=True, blocking=(), superseded_pdf_ids=superseded,
                         kept_pdf_ids=kept, new_transactions=new_transactions)


def _promoted_provenance() -> Provenance:
    return Provenance(document_id=PROMOTED_DOCUMENT_ID, page=None,
                      extraction_method=PROMOTED_EXTRACTION_METHOD)


def _trade_transaction(t: TradeCandidate) -> Transaction:
    # Match the PDF pipeline's own sign convention exactly (Stage 4 finding):
    # units and gross_amount are signed with the trade direction (BUY +,
    # SELL -); net_amount = gross +/- brokerage (established engine rule).
    signed_units = t.raw_quantity
    signed_gross = t.gross_amount if t.type is TxnType.BUY else -t.gross_amount
    return Transaction(
        transaction_id=f"CSV-{t.canonical_id}", account_id=ACCOUNT_ID,
        trade_date=t.trade_date, settlement_date=t.cash_effective_date,
        type=t.type, security_id=t.security_id, units=signed_units, price=t.price,
        gross_amount=signed_gross, fees=t.canonical_brokerage, net_amount=t.net_amount,
        currency="AUD", description=f"{t.type.value} {t.security_id} (STRUCTURED_CSV)",
        ordinal=0, provenance=_promoted_provenance(),
    )


def _transfer_transaction(t: TradeCandidate) -> Transaction:
    return Transaction(
        transaction_id=f"CSV-{t.canonical_id}-xfer", account_id=ACCOUNT_ID,
        trade_date=t.cash_effective_date, settlement_date=None,
        type=TxnType.TRANSFER, security_id=None, units=None, price=None,
        gross_amount=None, fees=None, net_amount=t.cash_effect,
        currency="AUD", description=f"cash leg of {t.type.value} {t.security_id} (STRUCTURED_CSV)",
        ordinal=0, provenance=_promoted_provenance(),
    )


def _cash_transaction(c: CashCandidate) -> Transaction:
    return Transaction(
        transaction_id=f"CSV-{c.canonical_id}", account_id=ACCOUNT_ID,
        trade_date=c.effective_date, settlement_date=None,
        type=c.type, security_id=c.security_id, units=None, price=None,
        gross_amount=None, fees=None, net_amount=c.signed_amount,
        currency="AUD", description=c.description, ordinal=0,
        provenance=_promoted_provenance(),
    )


def _code_to_db_security_id(repo: Repository) -> dict[str, str]:
    """Throughout Stage 1-4, a candidate's `security_id` is the ticker code
    (VAS, BHP, ...) -- consistent everywhere those candidates are matched,
    reconciled and reported. The persisted `securities` table instead keys
    each security on its own opaque id (`make_id(...)`, distinct from
    `code`). This is the one place that distinction matters: writing a new
    `transactions` row needs the table's real id to satisfy its foreign key,
    so promoted rows are translated code -> security_id right before the
    write, never earlier in the pipeline."""
    return {r["code"]: r["security_id"] for r in repo.rows("SELECT security_id, code FROM securities")}


def seed_transactions_from_candidates(cs: CandidateSet) -> list[Transaction]:
    """Convert an entire (fully-resolved) CandidateSet straight into
    canonical Transaction rows, with no PDF ledger to reconcile against or
    supersede -- for seeding a brand-new database (the synthetic demo
    dataset; see tools/generate_demo_data.py) rather than promoting reconciled
    data over an existing one. Reuses the exact same per-candidate
    conversion `apply_promotion` uses, so a demo-seeded database and a
    promoted real one are built by identical logic.

    Unlike `apply_promotion`, this does not translate a ticker code to the
    persisted `securities.security_id` -- the caller is expected to have
    seeded its own `securities` table keyed by the same codes (as
    tools/generate_demo_data.py does), since there is no existing table to
    look the real id up in.
    """
    transactions: list[Transaction] = []
    for t in cs.trades:
        transactions.append(_trade_transaction(t))
        transactions.append(_transfer_transaction(t))
    transactions += [_cash_transaction(c) for c in cs.cash]
    return transactions


def apply_promotion(repo: Repository, plan: PromotionPlan) -> None:
    """Write the plan into the repository: retire the superseded PDF rows,
    insert the promoted rows, commit. Never touches any table but
    `transactions`, and never called at all unless `plan.ready`."""
    if not plan.ready:
        raise ValueError(f"refusing to apply a non-ready promotion plan: {plan.blocking}")

    repo.upsert_document(Document(
        document_id=PROMOTED_DOCUMENT_ID, filename="vanguard-csv-promotion",
        kind=DocumentKind.OTHER, period_start=None, period_end=None, page_count=0,
        content_sha256=make_id("CSV_PROMOTION_DOC", datetime.now().date().isoformat()),
        extraction_method=PROMOTED_EXTRACTION_METHOD, imported_at=datetime.now(),
    ))

    code_to_id = _code_to_db_security_id(repo)
    resolved_transactions = []
    for t in plan.new_transactions:
        if t.security_id is None:
            resolved_transactions.append(t)
            continue
        db_id = code_to_id.get(t.security_id)
        if db_id is None:
            raise ValueError(f"promoted transaction references unknown security {t.security_id!r}")
        resolved_transactions.append(replace(t, security_id=db_id))

    repo.delete_transactions(plan.superseded_pdf_ids)
    repo.upsert_transactions(resolved_transactions)
    repo.commit()
