"""The analytics capability registry (hardening sec 7).

Phase 5 must not independently decide whether a chart or metric is valid --
that would let presentation code drift out of sync with what the data
actually supports, or worse, invent a judgement call Phase 4 never made.
`getAnalyticsCapabilities()` is the single place that decision is made, once,
from the same checks each metric function already performs internally.

Every entry says what the metric is, whether it's usable today, and why not
when it isn't -- machine-readable, so a UI can decide to hide, grey out, or
show a specific message without parsing prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.analytics.config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from src.history.config import Granularity
from src.history.service import HistoryService

ZERO = Decimal("0")


@dataclass(frozen=True)
class Capability:
    available: bool
    reason: str | None = None

    def to_dict(self) -> dict:
        return {"available": self.available, "reason": self.reason}


def _available() -> Capability:
    return Capability(True, None)


def _unavailable(reason: str) -> Capability:
    return Capability(False, reason)


def get_analytics_capabilities(service: HistoryService, benchmarks=None,
                               config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG
                               ) -> dict[str, dict]:
    """Every capability the spec lists (sec 7), each checked against this
    dataset's actual state rather than assumed."""
    rows = service.portfolio_history()
    quality = service.data_quality()
    reported_dates = service.reported_dates() if hasattr(service, "reported_dates") else None
    valuation_count = len([r for r in rows if r["valuation_status"] == "actual"])
    has_history = bool(rows)
    has_holdings = any(h for h in service.holdings_history())
    has_transactions = bool(service.repo.rows("SELECT 1 FROM transactions LIMIT 1"))
    has_income = bool(service.repo.rows("SELECT 1 FROM income_events LIMIT 1"))
    has_sales = bool(service.repo.rows("SELECT 1 FROM transactions WHERE type='SELL' LIMIT 1"))

    quarterly_dates = {r["date"] for r in rows if r.get("index_as_at") == r["date"]}
    quarterly_count = len(quarterly_dates)
    daily_gap = _finest_gap(rows)

    def gated(name: str, condition: bool, reason: str) -> tuple[str, dict]:
        return name, (_available() if condition else _unavailable(reason)).to_dict()

    caps: dict[str, dict] = dict([
        gated("portfolio_value", has_history, "No portfolio history available"),
        gated("historical_value", has_history, "No portfolio history available"),
        gated("holdings", has_holdings, "No holdings recorded"),
        gated("contributions", has_transactions, "No transactions imported"),
        gated("withdrawals", has_transactions, "No transactions imported"),
        gated("income", has_income, "No income events recorded"),
        gated("capital_gains", has_history, "No portfolio history available"),
        gated("realised_gains", has_sales, "No sell transactions recorded"),
        gated("unrealised_gains", has_holdings, "No holdings recorded"),
        gated("twrr", valuation_count >= 2,
             f"Only {valuation_count} real valuation(s) -- at least 2 are needed to chain a return"),
        gated("xirr", has_transactions and valuation_count >= 1,
             "Insufficient valuation or transaction data"),
        gated("daily_returns", daily_gap is not None and daily_gap <= 3,
             "Insufficient daily valuation observations"
             if daily_gap is None or daily_gap > 3 else None),
        gated("weekly_returns", daily_gap is not None and daily_gap <= 10,
             "Insufficient weekly valuation observations"
             if daily_gap is None or daily_gap > 10 else None),
        gated("monthly_returns", daily_gap is not None and daily_gap <= 35,
             "Insufficient monthly valuation observations"
             if daily_gap is None or daily_gap > 35 else None),
        gated("quarterly_returns", quarterly_count >= 2,
             "Insufficient quarterly valuation observations"),
        gated("volatility", quarterly_count >= config.minimum_observations_for_risk_metrics,
             f"Only {quarterly_count} quarterly observations, fewer than the"
             f" configured minimum of {config.minimum_observations_for_risk_metrics}"),
        gated("sharpe_ratio", config.risk_free_rate_annual is not None,
             "No risk-free rate configured"),
        gated("sortino_ratio", config.risk_free_rate_annual is not None,
             "No risk-free rate configured"),
        gated("beta", bool(benchmarks and benchmarks.all()),
             "No benchmark registered"),
        gated("correlation", bool(benchmarks and benchmarks.all()),
             "No benchmark registered"),
        gated("benchmark_comparison", bool(benchmarks and benchmarks.all()),
             "No benchmark registered"),
        gated("allocation", has_holdings, "No holdings recorded"),
        gated("sector_allocation", False, "Security classification metadata unavailable"),
        gated("geographic_allocation", False, "Security classification metadata unavailable"),
        gated("currency_allocation", False, "Security classification metadata unavailable"),
        gated("income_yield", has_income, "No income events recorded"),
        gated("income_growth", has_income, "No income events recorded"),
        gated("drawdown", quarterly_count >= 2,
             "Insufficient valuation observations to detect a drawdown"),
        gated("rolling_metrics", quarterly_count >= 8,
             "Fewer than 8 quarterly observations -- too few for a rolling window"),
    ])
    return caps


def _finest_gap(rows: list[dict]) -> int | None:
    """The smallest number of days between two consecutive real valuations."""
    from datetime import date as _date
    valued = sorted(_date.fromisoformat(r["date"]) for r in rows
                    if r.get("index_as_at") == r["date"])
    if len(valued) < 2:
        return None
    return min((b - a).days for a, b in zip(valued, valued[1:]))
