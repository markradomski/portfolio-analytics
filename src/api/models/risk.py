"""Risk metrics, drawdowns and high-water mark (sec 8: Risk family)."""

from __future__ import annotations

from src.api.models.common import ApiModel, DecimalString, ISODate, Metric


class RiskMetrics(ApiModel):
    volatility: Metric
    sharpe_ratio: Metric
    sortino_ratio: Metric


class DrawdownEpisode(ApiModel):
    episode_id: str
    peak_date: ISODate
    peak_value: DecimalString
    trough_date: ISODate
    trough_value: DecimalString
    drawdown_value: DecimalString
    drawdown_pct: DecimalString
    recovery_date: ISODate | None = None
    recovery_days: int | None = None
    valuation_status: str


class HighWaterMarkStatus(ApiModel):
    date: ISODate
    current_value: DecimalString | None = None
    high_water_mark: DecimalString
    distance_from_high: DecimalString | None = None
    distance_from_high_pct: DecimalString | None = None
    days_since_high: int | None = None


class BenchmarkComparison(ApiModel):
    """Portfolio-vs-benchmark (sec 11/23). Every field is None/absent when
    no benchmark is registered -- the frontend must never construct a
    fake comparison from a missing one."""
    portfolio_return: DecimalString | None = None
    benchmark_return: DecimalString | None = None
    relative_return: DecimalString | None = None
    portfolio_methodology: str
    benchmark_methodology: str | None = None
    methodology_mismatch: bool
    status: str
    note: str | None = None
    benchmark_id: str | None = None
    benchmark_name: str | None = None
    benchmark_return_method: str | None = None
    benchmark_data_source: str | None = None
    benchmark_frequency: str | None = None
    benchmark_coverage: int | None = None


class DrawdownAnalytics(ApiModel):
    """getDrawdowns() -- summary statistics over Phase 3's drawdown_history()
    episodes (sec 27/29). All fields are null when there is no drawdown
    history at all, never a fabricated zero."""
    maximum_drawdown_pct: DecimalString | None = None
    maximum_drawdown_peak: ISODate | None = None
    maximum_drawdown_trough: ISODate | None = None
    average_drawdown_pct: DecimalString | None = None
    episode_count: int
    longest_underwater_days: int | None = None
    longest_underwater_peak: ISODate | None = None
    fastest_recovery_days: int | None = None
