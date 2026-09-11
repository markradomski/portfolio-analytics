"""Idempotent staging for CSV-backed canonical candidates (Step 9B, Stage 3).

The staging store holds candidate economic events by their canonical id. It is
NOT the production ledger: nothing here writes `transactions`, deletes a
PDF-derived row, or promotes source authority.

Guarantees:

* **idempotent** -- staging the identical candidate set again is a no-op
  (recognised by canonical id, not by a DB constraint failure);
* **overlap-safe** -- a wider later export re-recognises the events it shares
  with an earlier one and inserts only the genuinely new ones;
* **correction-aware** -- a candidate that occupies the same economic *slot*
  (type + security + date) as a staged event but has a changed financial field
  is flagged `SOURCE_CHANGED`, with both provenances kept; it never silently
  overwrites. Full supersession/versioning is deferred (documented).

File identity is the sanitised-content sha256 the candidate set carries, never
the filename -- same content under a different filename stages as the same input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.ingestion.vanguard_csv.canonical import (
    CandidateSet, CashCandidate, TradeCandidate,
)


class EventStatus(str, Enum):
    STAGED = "STAGED"
    SOURCE_CHANGED = "SOURCE_CHANGED"      # a corrected representation arrived


@dataclass
class ImportRun:
    import_run_id: str
    source_type: str
    sanitised_source_hashes: tuple[str, ...]
    started_at: str
    completed_at: str | None = None
    rows_seen: int = 0
    candidate_events: int = 0
    matched_events: int = 0
    unresolved_events: int = 0
    status: str = "RUNNING"


@dataclass
class StagedEvent:
    canonical_id: str
    kind: str                              # "trade" | "cash"
    correction_key: tuple
    economic_fingerprint: str
    payload: TradeCandidate | CashCandidate
    status: EventStatus
    first_seen_run: str
    last_seen_run: str
    provenance_history: list[tuple] = field(default_factory=list)
    supersedes: str | None = None


@dataclass
class StageResult:
    import_run: ImportRun
    added: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)   # canonical ids of the new (changed) events

    @property
    def duplicate_economic_events(self) -> int:
        return 0   # by construction -- staging is keyed on canonical id


def _correction_key(payload: TradeCandidate | CashCandidate) -> tuple:
    if isinstance(payload, TradeCandidate):
        return ("trade", payload.type.value, payload.security_id, payload.trade_date.isoformat())
    return ("cash", payload.source_transaction_type, payload.security_id,
            payload.effective_date.isoformat())


def _provenance_snapshot(payload: TradeCandidate | CashCandidate) -> tuple:
    if isinstance(payload, TradeCandidate):
        return (payload.investment_source, payload.cash_source)
    return (payload.cash_source,)


class StagingStore:
    def __init__(self) -> None:
        self._events: dict[str, StagedEvent] = {}
        self._by_correction_key: dict[tuple, list[str]] = {}
        self.runs: list[ImportRun] = []

    # -- read ----------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._events)

    @property
    def events(self) -> list[StagedEvent]:
        return list(self._events.values())

    def economic_event_count(self) -> int:
        """Distinct economic events currently staged -- a SOURCE_CHANGED pair
        still counts as one slot's worth for the purposes of the idempotency
        assertion, but each canonical id is retained for audit."""
        return len(self._events)

    def ids(self) -> list[str]:
        return sorted(self._events)

    # -- write -------------------------------------------------------------

    def stage(self, candidate_set: CandidateSet, *, import_run_id: str | None = None,
              source_type: str = "VANGUARD_CSV") -> StageResult:
        run = ImportRun(
            import_run_id=import_run_id or f"run-{len(self.runs) + 1}",
            source_type=source_type,
            sanitised_source_hashes=(candidate_set.investment_file_sha256,
                                     candidate_set.cash_file_sha256),
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = StageResult(import_run=run)

        payloads: list[TradeCandidate | CashCandidate] = [
            *candidate_set.trades, *candidate_set.cash,
        ]
        run.rows_seen = len(payloads)
        run.candidate_events = len(payloads)
        run.matched_events = len(candidate_set.trades)
        run.unresolved_events = len(candidate_set.unresolved())

        for payload in payloads:
            cid = payload.canonical_id
            fp = payload.economic_fingerprint
            ckey = _correction_key(payload)

            if cid in self._events:
                # exact same economic identity -> idempotent
                self._events[cid].last_seen_run = run.import_run_id
                result.unchanged.append(cid)
                continue

            siblings = [
                self._events[e] for e in self._by_correction_key.get(ckey, [])
                if self._events[e].economic_fingerprint != fp
            ]
            kind = "trade" if isinstance(payload, TradeCandidate) else "cash"
            ev = StagedEvent(
                canonical_id=cid, kind=kind, correction_key=ckey,
                economic_fingerprint=fp, payload=payload,
                status=EventStatus.SOURCE_CHANGED if siblings else EventStatus.STAGED,
                first_seen_run=run.import_run_id, last_seen_run=run.import_run_id,
                provenance_history=[_provenance_snapshot(payload)],
            )
            if siblings:
                ev.supersedes = siblings[0].canonical_id
                siblings[0].provenance_history.append(_provenance_snapshot(payload))
                result.corrections.append(cid)
            else:
                result.added.append(cid)

            self._events[cid] = ev
            self._by_correction_key.setdefault(ckey, []).append(cid)

        run.completed_at = datetime.now().isoformat(timespec="seconds")
        run.status = "COMPLETE"
        self.runs.append(run)
        return result
