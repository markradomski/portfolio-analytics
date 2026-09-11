"""Data coverage metadata (hardening sec 8).

A standard object describing how much genuine data underlies the analytics --
so a UI can say "24 valuation observations, quarterly data" instead of
implying daily precision it doesn't have (the spec's own example).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.history.service import HistoryService


@dataclass(frozen=True)
class DataCoverage:
    valuation_start: date | None
    valuation_end: date | None
    valuation_observation_count: int
    transaction_start: date | None
    transaction_end: date | None
    price_observation_count: int
    missing_valuation_count: int
    actual_observation_count: int
    carried_forward_observation_count: int
    estimated_observation_count: int
    unavailable_observation_count: int

    def to_dict(self) -> dict:
        return {
            "valuation_start": self.valuation_start.isoformat() if self.valuation_start else None,
            "valuation_end": self.valuation_end.isoformat() if self.valuation_end else None,
            "valuation_observation_count": self.valuation_observation_count,
            "transaction_start": self.transaction_start.isoformat() if self.transaction_start else None,
            "transaction_end": self.transaction_end.isoformat() if self.transaction_end else None,
            "price_observation_count": self.price_observation_count,
            "missing_valuation_count": self.missing_valuation_count,
            "actual_observation_count": self.actual_observation_count,
            "carried_forward_observation_count": self.carried_forward_observation_count,
            "estimated_observation_count": self.estimated_observation_count,
            "unavailable_observation_count": self.unavailable_observation_count,
        }


def get_data_coverage(service: HistoryService) -> DataCoverage:
    rows = service.portfolio_history()
    quality = service.data_quality()

    dates = sorted(date.fromisoformat(r["date"]) for r in rows)
    quarterly_dates = sorted(date.fromisoformat(r["date"]) for r in rows
                             if r.get("index_as_at") == r["date"])

    txn_dates = [r["trade_date"] for r in service.repo.rows(
        "SELECT trade_date FROM transactions ORDER BY trade_date")]

    by_status = quality["by_status"]
    return DataCoverage(
        valuation_start=quarterly_dates[0] if quarterly_dates else None,
        valuation_end=quarterly_dates[-1] if quarterly_dates else None,
        valuation_observation_count=len(quarterly_dates),
        transaction_start=date.fromisoformat(txn_dates[0]) if txn_dates else None,
        transaction_end=date.fromisoformat(txn_dates[-1]) if txn_dates else None,
        price_observation_count=quality.get("priced_dates", 0),
        missing_valuation_count=by_status.get("unavailable", 0),
        actual_observation_count=by_status.get("actual", 0),
        carried_forward_observation_count=by_status.get("estimated", 0),
        estimated_observation_count=by_status.get("calculated", 0),
        unavailable_observation_count=by_status.get("unavailable", 0),
    )
