"""Risk analytics: volatility, Sharpe, Sortino, beta, correlation, drawdown
and high-water-mark analytics (sec 24-28).

The frequency question is the one that matters here. This portfolio is priced
on ~24 real dates across six years -- computing "daily volatility" from a
series that is 92% carried-forward values would report a number with false
precision: near-zero on every flat day, then an artificial spike whenever a
real price lands. Every calculation here operates on the quarterly TWRR series
Phase 3 already validated (period_summaries), because that is the finest
frequency this data can honestly support -- see docs/analytics.md
"Why quarterly risk metrics".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analytics.config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig, ReturnFrequency
from src.analytics.result import Confidence, DataQuality, Metric, confidence_for, unavailable
from src.engine.benchmark import Benchmark
from src.history.config import Granularity
from src.history.service import HistoryService

ZERO = Decimal("0")


def _quarterly_returns(service: HistoryService) -> list[tuple[date, Decimal]]:
    rows = service.period_summaries(Granularity.QUARTERLY)
    return [(date.fromisoformat(r["period_end"]), Decimal(r["twrr"]))
            for r in rows if r["twrr"] is not None]


def _stdev(values: list[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    mean = sum(values, ZERO) / Decimal(len(values))
    variance = sum(((v - mean) ** 2 for v in values), ZERO) / Decimal(len(values) - 1)
    # Decimal has no sqrt; float round-trip is fine for a summary statistic.
    return Decimal(str(float(variance) ** 0.5))


# Below this many observations, even a calculated figure is marked LIMITED
# rather than CALCULATED -- technically computable, but from a sample too
# small to trust as a stable estimate. Distinct from
# minimum_observations_for_risk_metrics, which is the harder floor below
# which nothing is reported at all.
_LIMITED_SAMPLE_THRESHOLD = 12


def volatility(service: HistoryService, config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG
              ) -> Metric:
    if config.risk_return_frequency is not ReturnFrequency.QUARTERLY:
        return unavailable(
            "volatility", "stdev(period returns) x sqrt(periods_per_year)",
            f"{config.risk_return_frequency.value} returns are not available for"
            " this data source -- prices exist on ~24 dates across six years,"
            " which only supports genuine quarterly observations",
            frequency=config.risk_return_frequency.value)

    returns = [r for _, r in _quarterly_returns(service)]
    n = len(returns)
    if n < config.minimum_observations_for_risk_metrics:
        return unavailable(
            "volatility", "stdev(quarterly TWRR) x sqrt(4)",
            f"only {n} quarterly observations available, fewer than"
            f" the configured minimum of {config.minimum_observations_for_risk_metrics}",
            frequency="quarterly", observations=n)

    period_stdev = _stdev(returns)
    factor = Decimal(str(4 ** 0.5))
    annualised = period_stdev * factor
    quality = (DataQuality.LIMITED if n < _LIMITED_SAMPLE_THRESHOLD
              else DataQuality.CALCULATED)
    confidence = confidence_for(n, config.minimum_observations_for_risk_metrics)
    note = (f"{n} quarterly observations"
           + (" -- a sample this small should be read as indicative, not precise"
              if quality is DataQuality.LIMITED else ""))
    return Metric(
        name="volatility", value=annualised,
        methodology="stdev(quarterly TWRR) x sqrt(4), annualised",
        data_quality=quality, frequency="quarterly",
        annualisation="x sqrt(4)", annualisation_factor=factor,
        observations=n, confidence=confidence, note=note)


def sharpe_ratio(service: HistoryService, config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG
                 ) -> Metric:
    """(annualised portfolio return - risk-free rate) / annualised volatility.
    UNAVAILABLE, not zero, when no risk-free rate is configured (sec 26's
    explicit instruction) -- an assumed 0% rate is a real, material choice."""
    if config.risk_free_rate_annual is None:
        return unavailable(
            "sharpe_ratio", "(annualised_return - risk_free_rate) / annualised_volatility",
            "no risk_free_rate_annual configured -- assuming 0% would be a"
            " real, undocumented choice, not a harmless default")

    vol = volatility(service, config)
    if vol.data_quality is DataQuality.UNAVAILABLE:
        return unavailable(
            "sharpe_ratio", "(annualised_return - risk_free_rate) / annualised_volatility",
            f"volatility unavailable: {vol.note}")

    quarterly = [r for _, r in _quarterly_returns(service)]
    compound = Decimal(1)
    for r in quarterly:
        compound *= (Decimal(1) + r)
    years = Decimal(len(quarterly)) / Decimal(4)
    annualised_return = (Decimal(str(float(compound) ** (1 / float(years))))
                         - Decimal(1)) if years > ZERO and compound > ZERO else None
    if annualised_return is None:
        return unavailable("sharpe_ratio", "(annualised_return - risk_free_rate) / annualised_volatility",
                           "could not annualise the portfolio return")

    excess = annualised_return - config.risk_free_rate_annual
    n = len(quarterly)
    return Metric(
        name="sharpe_ratio", value=excess / vol.value,
        methodology="(annualised_return - risk_free_rate) / annualised_volatility",
        data_quality=vol.data_quality, frequency="quarterly",
        annualisation="x sqrt(4)", annualisation_factor=Decimal(str(4 ** 0.5)),
        risk_free_rate=config.risk_free_rate_annual, observations=n,
        confidence=vol.confidence,
        note=f"built on the same {n}-observation volatility figure above"
        + (" -- LIMITED sample" if vol.data_quality is DataQuality.LIMITED else ""))


def sortino_ratio(service: HistoryService, config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG
                  ) -> Metric:
    """Same as Sharpe, but the denominator is downside deviation -- stdev of
    only the negative quarterly returns -- so volatility from good quarters
    doesn't penalise the ratio."""
    if config.risk_free_rate_annual is None:
        return unavailable(
            "sortino_ratio", "(annualised_return - risk_free_rate) / downside_deviation",
            "no risk_free_rate_annual configured")

    returns = [r for _, r in _quarterly_returns(service)]
    downside = [r for r in returns if r < ZERO]
    if len(downside) < 2:
        return unavailable(
            "sortino_ratio", "(annualised_return - risk_free_rate) / downside_deviation",
            f"only {len(downside)} negative quarters observed -- too few to"
            " compute a downside deviation", observations=len(downside))

    downside_stdev = _stdev(downside) * Decimal(str(4 ** 0.5))
    compound = Decimal(1)
    for r in returns:
        compound *= (Decimal(1) + r)
    years = Decimal(len(returns)) / Decimal(4)
    annualised_return = (Decimal(str(float(compound) ** (1 / float(years))))
                         - Decimal(1)) if years > ZERO and compound > ZERO else None
    if annualised_return is None or downside_stdev == ZERO:
        return unavailable("sortino_ratio", "(annualised_return - risk_free_rate) / downside_deviation",
                           "could not compute an annualised return or downside deviation")

    excess = annualised_return - config.risk_free_rate_annual
    n = len(downside)
    quality = DataQuality.LIMITED if n < _LIMITED_SAMPLE_THRESHOLD else DataQuality.CALCULATED
    return Metric(
        name="sortino_ratio", value=excess / downside_stdev,
        methodology="(annualised_return - risk_free_rate) / downside_deviation",
        data_quality=quality, frequency="quarterly",
        annualisation="x sqrt(4)", annualisation_factor=Decimal(str(4 ** 0.5)),
        risk_free_rate=config.risk_free_rate_annual, observations=n,
        confidence=confidence_for(n, config.minimum_observations_for_risk_metrics),
        note=f"{n} negative quarters used for downside deviation"
        + (" -- LIMITED sample" if quality is DataQuality.LIMITED else ""))


def beta(service: HistoryService, benchmark: Benchmark | None,
        config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> Metric:
    """cov(portfolio, benchmark) / var(benchmark), on quarterly returns.
    UNAVAILABLE with no benchmark registered -- see src/analytics/benchmark.py."""
    if benchmark is None:
        return unavailable("beta", "cov(portfolio, benchmark) / var(benchmark)",
                           "no benchmark registered")
    dated_returns = _quarterly_returns(service)
    dates = [d for d, _ in dated_returns]
    bench_returns = benchmark.return_series(dates)
    pairs = [(p, b) for (_, p), b in zip(dated_returns, bench_returns) if b is not None]
    if len(pairs) < config.minimum_observations_for_risk_metrics:
        return unavailable("beta", "cov(portfolio, benchmark) / var(benchmark)",
                           f"only {len(pairs)} paired observations, fewer than"
                           f" the configured minimum of {config.minimum_observations_for_risk_metrics}",
                           observations=len(pairs))
    p_vals, b_vals = [p for p, _ in pairs], [b for _, b in pairs]
    p_mean = sum(p_vals, ZERO) / Decimal(len(p_vals))
    b_mean = sum(b_vals, ZERO) / Decimal(len(b_vals))
    cov = sum(((p - p_mean) * (b - b_mean) for p, b in pairs), ZERO) / Decimal(len(pairs) - 1)
    var = sum(((b - b_mean) ** 2 for b in b_vals), ZERO) / Decimal(len(b_vals) - 1)
    if var == ZERO:
        return unavailable("beta", "cov(portfolio, benchmark) / var(benchmark)",
                           "benchmark variance is zero over this period")
    n = len(pairs)
    quality = DataQuality.LIMITED if n < _LIMITED_SAMPLE_THRESHOLD else DataQuality.CALCULATED
    return Metric(name="beta", value=cov / var,
                 methodology="cov(portfolio, benchmark) / var(benchmark)",
                 data_quality=quality, frequency="quarterly",
                 benchmark=benchmark.definition.identifier, observations=n,
                 confidence=confidence_for(n, config.minimum_observations_for_risk_metrics),
                 note=f"{n} paired quarterly observations"
                 + (" -- LIMITED sample" if quality is DataQuality.LIMITED else ""))


def correlation(service: HistoryService, benchmark: Benchmark | None,
                config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> Metric:
    if benchmark is None:
        return unavailable("correlation", "pearson correlation coefficient",
                           "no benchmark registered")
    dated_returns = _quarterly_returns(service)
    dates = [d for d, _ in dated_returns]
    bench_returns = benchmark.return_series(dates)
    pairs = [(p, b) for (_, p), b in zip(dated_returns, bench_returns) if b is not None]
    if len(pairs) < config.minimum_observations_for_risk_metrics:
        return unavailable("correlation", "pearson correlation coefficient",
                           f"only {len(pairs)} paired observations",
                           observations=len(pairs))
    p_vals, b_vals = [p for p, _ in pairs], [b for _, b in pairs]
    p_sd, b_sd = _stdev(p_vals), _stdev(b_vals)
    if not p_sd or not b_sd:
        return unavailable("correlation", "pearson correlation coefficient",
                           "zero variance in one of the series")
    p_mean = sum(p_vals, ZERO) / Decimal(len(p_vals))
    b_mean = sum(b_vals, ZERO) / Decimal(len(b_vals))
    cov = sum(((p - p_mean) * (b - b_mean) for p, b in pairs), ZERO) / Decimal(len(pairs) - 1)
    n = len(pairs)
    quality = DataQuality.LIMITED if n < _LIMITED_SAMPLE_THRESHOLD else DataQuality.CALCULATED
    return Metric(name="correlation", value=cov / (p_sd * b_sd),
                 methodology="pearson correlation coefficient on quarterly returns",
                 data_quality=quality, frequency="quarterly",
                 benchmark=benchmark.definition.identifier, observations=n,
                 confidence=confidence_for(n, config.minimum_observations_for_risk_metrics))


@dataclass(frozen=True)
class DrawdownAnalytics:
    maximum_drawdown_pct: Decimal | None
    maximum_drawdown_peak: date | None
    maximum_drawdown_trough: date | None
    average_drawdown_pct: Decimal | None
    episode_count: int
    longest_underwater_days: int | None
    longest_underwater_peak: date | None
    fastest_recovery_days: int | None


def drawdown_analytics(service: HistoryService) -> DrawdownAnalytics:
    """Extends Phase 3's drawdown_episodes (sec 27) with the summary
    statistics Sharesight-style reporting wants -- reads them, computes
    nothing about drawdown detection itself (that stays in Phase 3)."""
    episodes = service.drawdown_history()
    if not episodes:
        return DrawdownAnalytics(None, None, None, None, 0, None, None, None)

    worst = min(episodes, key=lambda e: Decimal(e["drawdown_pct"]))
    depths = [Decimal(e["drawdown_pct"]) for e in episodes]
    average = sum(depths, ZERO) / Decimal(len(depths))

    def underwater_days(e: dict) -> int | None:
        peak = date.fromisoformat(e["peak_date"])
        recovery = date.fromisoformat(e["recovery_date"]) if e["recovery_date"] else None
        return (recovery - peak).days if recovery else None

    with_duration = [(e, underwater_days(e)) for e in episodes]
    timed = [(e, d) for e, d in with_duration if d is not None]
    longest = max(timed, key=lambda x: x[1], default=(None, None))
    fastest = min(
        ((e, (date.fromisoformat(e["recovery_date"]) - date.fromisoformat(e["trough_date"])).days)
         for e in episodes if e["recovery_date"]),
        key=lambda x: x[1], default=(None, None))

    return DrawdownAnalytics(
        maximum_drawdown_pct=Decimal(worst["drawdown_pct"]),
        maximum_drawdown_peak=date.fromisoformat(worst["peak_date"]),
        maximum_drawdown_trough=date.fromisoformat(worst["trough_date"]),
        average_drawdown_pct=average, episode_count=len(episodes),
        longest_underwater_days=longest[1],
        longest_underwater_peak=date.fromisoformat(longest[0]["peak_date"]) if longest[0] else None,
        fastest_recovery_days=fastest[1])


@dataclass(frozen=True)
class HighWaterMarkStatus:
    date: date
    current_value: Decimal | None
    high_water_mark: Decimal
    distance_from_high: Decimal | None
    distance_from_high_pct: Decimal | None
    days_since_high: int | None


def high_water_mark_status(service: HistoryService, on: date | None = None
                           ) -> HighWaterMarkStatus:
    """Sec 28. Uses the investment (flow-neutral) high-water mark, not the
    value-based one -- consistent with Phase 3's own distinction, since the
    value-based figure conflates a withdrawal with a decline."""
    rows = service.portfolio_history()
    if not rows:
        return HighWaterMarkStatus(on or date.today(), None, ZERO, None, None, None)
    target = on or max(date.fromisoformat(r["date"]) for r in rows)
    row = next((r for r in rows if r["date"] == target.isoformat()), None)
    if row is None:
        return HighWaterMarkStatus(target, None, ZERO, None, None, None)

    high_water_index = Decimal(row["return_high_water"]) if row["return_high_water"] else None
    current_index = Decimal(row["return_index"]) if row["return_index"] else None
    distance_pct = (Decimal(row["return_drawdown_pct"])
                    if row["return_drawdown_pct"] is not None else None)

    high_date = None
    if high_water_index is not None:
        at_high = [r for r in rows if r["return_index"]
                  and Decimal(r["return_index"]) >= high_water_index
                  and date.fromisoformat(r["date"]) <= target]
        if at_high:
            high_date = min(date.fromisoformat(r["date"]) for r in at_high
                            if Decimal(r["return_index"]) >= high_water_index)

    current_value = Decimal(row["total_value"]) if row["total_value"] else None
    return HighWaterMarkStatus(
        date=target, current_value=current_value,
        high_water_mark=high_water_index or ZERO,
        distance_from_high=(current_index - high_water_index)
        if current_index is not None and high_water_index is not None else None,
        distance_from_high_pct=distance_pct,
        days_since_high=(target - high_date).days if high_date else None)
