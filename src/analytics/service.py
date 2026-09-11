"""The analytics service façade (sec 37).

One entry point for everything in this package, shaped around the questions
listed in the spec. Returns structured data (dataclasses, dicts of Decimal
strings) -- never a chart-ready or presentation-specific structure. The
frontend (Phase 5) must never calculate a return itself; this is where every
number comes from.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.analytics import (allocation as _allocation, attribution as _attribution,
                           benchmark as _benchmark, calendar as _calendar,
                           capabilities as _capabilities,
                           contributions as _contributions, costs as _costs,
                           coverage as _coverage, gains as _gains,
                           growth as _growth,
                           income as _income, performance as _performance,
                           risk as _risk, rolling as _rolling, trading as _trading)
from src.analytics.config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from src.database.repository import Repository
from src.engine.benchmark import Benchmark, BenchmarkRegistry
from src.engine.ledger import Ledger
from src.engine.prices import SnapshotPriceSource
from src.engine.state import StateEngine
from src.history.config import Granularity
from src.history.service import HistoryService


class AnalyticsService:
    def __init__(self, repo: Repository, config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
                 benchmarks: BenchmarkRegistry | None = None):
        self.repo = repo
        self.config = config
        self.history = HistoryService(repo)
        self.benchmarks = benchmarks or BenchmarkRegistry()
        self._ledger: Ledger | None = None
        self._state_engine: StateEngine | None = None

    # Internal composition only (hardening sec 14): nothing on the public
    # surface of this service returns a raw engine/history object. Phase 5
    # must consume analytics exclusively through the getX() methods below,
    # never by importing src.engine or src.history for its own calculations.
    @property
    def _ledger_(self) -> Ledger:
        if self._ledger is None:
            self._ledger = Ledger.from_repository(self.repo)
        return self._ledger

    @property
    def _state_engine_(self) -> StateEngine:
        if self._state_engine is None:
            from src.engine.cash import opening_cash_for
            self._state_engine = StateEngine(
                SnapshotPriceSource.from_repository(self.repo),
                opening_cash=opening_cash_for(self.repo))
        return self._state_engine

    # -- performance (sec 3-5) ------------------------------------------------

    def getPerformance(self, start: date, end: date) -> _performance.PerformanceOverview:
        return _performance.overview_for_range(self.history, start, end)

    def getPerformanceForYear(self, year: int) -> _performance.PerformanceOverview | None:
        return _performance.overview_for_year(self.history, year)

    def getReturns(self, as_at: date | None = None) -> list:
        return _performance.standard_periods(self.history, as_at)

    def getReturnMethodology(self) -> dict[str, str]:
        return _performance.return_methodology_notes()

    # -- attribution (sec 6, 7, 36, 41-42) ------------------------------------

    def getAttribution(self, start: date, end: date) -> dict:
        return _attribution.attribution_tree(self._state_engine_, self._ledger_, start, end)

    def getGrowthDecomposition(self, start: date, end: date):
        return _attribution.growth_decomposition(self._state_engine_, self._ledger_, start, end)

    def getSecurityPerformance(self, start: date, end: date) -> list:
        return _attribution.security_attribution(self._state_engine_, self._ledger_, start, end)

    def getAttributionReconciliation(self, start: date, end: date):
        return _attribution.reconcile_attribution(self._state_engine_, self._ledger_, start, end)

    def getGrowthReconciliation(self, start: date, end: date):
        return _attribution.reconcile_growth(self._state_engine_, self._ledger_, start, end)

    # -- contributions (sec 8-9) ----------------------------------------------

    def getContributionSummary(self, as_at: date | None = None):
        return _contributions.contribution_summary(self.history, as_at)

    def getContributionEfficiency(self, as_at: date | None = None):
        return _contributions.contribution_efficiency(self.history, as_at)

    # -- portfolio growth (Step 9) ---------------------------------------------

    def getPortfolioGrowth(self, start: date | None = None, end: date | None = None):
        return _growth.portfolio_growth(self.history, self.repo, start, end)

    def getPortfolioGrowthSummary(self, as_at: date | None = None):
        return _growth.portfolio_growth_summary(self.history, as_at)

    def getPortfolioValueReconciliation(self):
        """Calculated portfolio value/cash vs. Vanguard's own reported
        statement figures, per date (Step 9 sec 10) -- distinct from
        getGrowthReconciliation() above, which checks a period's own flow
        arithmetic is internally consistent rather than against a source
        document."""
        return _growth.growth_reconciliation(self.repo, self._ledger_)

    # -- income (sec 10-12) ---------------------------------------------------

    def getIncomeAnalytics(self, granularity: Granularity = Granularity.YEARLY,
                           by_security: bool = False) -> list[dict]:
        return _income.income_by(self.history, granularity, by_security)

    def getIncomeByAssetClass(self, granularity: Granularity = Granularity.YEARLY) -> list[dict]:
        return _income.income_by_asset_class(self.history, granularity)

    def getTrailingIncomeYield(self, as_at: date | None = None):
        return _income.trailing_income_yield(self.history, as_at, self.config)

    def getForwardIncomeYield(self, as_at: date | None = None):
        return _income.forward_income_yield(self.history, as_at, self.config)

    def getSecurityIncomeYield(self, code: str, as_at: date | None = None):
        return _income.security_income_yield(self.history, code, as_at, self.config)

    def getIncomeGrowth(self) -> list[dict]:
        return _income.income_growth(self.history)

    # -- allocation (sec 13-15) ------------------------------------------------

    def getAllocation(self, by: str = "security", on: date | None = None) -> dict:
        return _allocation.allocation(self.history, by, on)

    def getAllocationHistory(self, by: str = "asset_class",
                             granularity: Granularity = Granularity.MONTHLY) -> list[dict]:
        return _allocation.allocation_history(self.history, by, granularity)

    def getAllocationDrift(self, targets: dict[str, Decimal], by: str = "asset_class",
                           on: date | None = None) -> list:
        return _allocation.allocation_drift(self.history, targets, by, on)

    def getConcentration(self, on: date | None = None):
        return _allocation.concentration(self.history, on)

    def getConcentrationHistory(self, granularity: Granularity = Granularity.MONTHLY) -> list:
        return _allocation.concentration_history(self.history, granularity)

    # -- trading & turnover (sec 16-17) ----------------------------------------

    def getTurnover(self, start: date, end: date):
        return _trading.turnover(self.history, self.repo, start, end, self.config)

    def getTradingActivity(self, start: date | None = None, end: date | None = None):
        return _trading.trading_activity(self.repo, start, end)

    def getTradingActivityBy(self, granularity: str = "year") -> list[dict]:
        return _trading.trading_activity_by(self.repo, granularity)

    # -- gains (sec 18-20) ------------------------------------------------------

    def getRealisedGains(self, start: date | None = None, end: date | None = None):
        return _gains.realised_gains(self._ledger_, start, end)

    def getRealisedGainsBySecurity(self, start: date | None = None,
                                   end: date | None = None) -> list:
        return _gains.realised_gains_by_security(self.repo, self._ledger_, start, end)

    def getUnrealisedGains(self, on: date) -> list:
        classes = {r["code"]: r["asset_class"] for r in self.repo.rows(
            "SELECT DISTINCT h.asset_class, s.code FROM holding_daily h"
            " JOIN securities s USING (security_id)")}
        return _gains.unrealised_gains(self._state_engine_, self._ledger_, on, classes)

    def getGainAttribution(self, on: date):
        return _gains.gain_attribution(self._state_engine_, self._ledger_, on)

    # -- benchmarking (sec 21-23) -----------------------------------------------

    def registerBenchmark(self, benchmark: Benchmark) -> None:
        self.benchmarks.register(benchmark)

    def getBenchmarkComparison(self, period_label: str, benchmark_id: str,
                               as_at: date | None = None):
        periods = _performance.standard_periods(self.history, as_at)
        period = next((p for p in periods if p.label == period_label), None)
        if period is None:
            raise ValueError(f"unknown period label {period_label!r}")
        dates = sorted(date.fromisoformat(r["date"]) for r in
                       self.history.portfolio_history(period.start_date, period.end_date))
        return _benchmark.compare_to_benchmark(period, self.benchmarks, benchmark_id, dates)

    # -- risk (sec 24-28) ---------------------------------------------------------

    def getRiskMetrics(self) -> dict:
        return {
            "volatility": _risk.volatility(self.history, self.config),
            "sharpe_ratio": _risk.sharpe_ratio(self.history, self.config),
            "sortino_ratio": _risk.sortino_ratio(self.history, self.config),
        }

    def getBeta(self, benchmark_id: str | None = None):
        benchmark = self.benchmarks.get(benchmark_id) if benchmark_id else None
        return _risk.beta(self.history, benchmark, self.config)

    def getCorrelation(self, benchmark_id: str | None = None):
        benchmark = self.benchmarks.get(benchmark_id) if benchmark_id else None
        return _risk.correlation(self.history, benchmark, self.config)

    def getDrawdownAnalytics(self):
        return _risk.drawdown_analytics(self.history)

    def getHighWaterMarkStatus(self, on: date | None = None):
        return _risk.high_water_mark_status(self.history, on)

    # -- rolling (sec 29) -----------------------------------------------------

    def getRollingMetrics(self, window_days: int = 90) -> list:
        return _rolling.rolling_return(self.history, window_days)

    def getRollingVolatility(self, window_quarters: int = 8) -> list[dict]:
        return _rolling.rolling_volatility(self.history, window_quarters)

    def getRollingIncomeYield(self) -> list[dict]:
        return _rolling.rolling_income_yield(self.history)

    # -- calendar, best/worst, milestones (sec 30-32) --------------------------

    def getCalendarPerformance(self, granularity: Granularity = Granularity.YEARLY) -> list[dict]:
        return _calendar.calendar_performance(self.history, granularity)

    def getBestWorstPeriods(self) -> dict:
        return _calendar.best_worst_periods(self.history)

    def getMilestoneAnalytics(self) -> list[dict]:
        return _calendar.milestone_context(self.history)

    # -- efficiency, fees, tax (sec 33-35) -----------------------------------

    def getEfficiencyMetrics(self, start: date, end: date):
        return _costs.efficiency_metrics(self.history, start, end)

    def getFeeAnalytics(self, start: date, end: date):
        return _costs.fee_summary(self.history, start, end)

    def getFeesByYear(self) -> list[dict]:
        return _costs.fees_by_year(self.repo)

    def getFeesBySecurity(self) -> list[dict]:
        return _costs.fees_by_security(self.repo)

    def getTaxAnalytics(self) -> list:
        return _costs.tax_analytics(self.repo)

    # -- API boundary aliases (hardening sec 14) -------------------------------
    #
    # The exact getX() names sec 14 lists, as thin aliases over the richer
    # names above -- both are kept so existing callers (and their tests)
    # continue to work, and Phase 5 has the names the spec asks for.

    def getPortfolioOverview(self, as_at: date | None = None) -> dict:
        """A single-call snapshot: current state, lifetime contributions, and
        data coverage -- everything a portfolio "home page" typically needs
        without composing several calls."""
        contributions = self.getContributionSummary(as_at)
        dates = sorted(r["date"] for r in self.history.portfolio_history())
        latest = date.fromisoformat(dates[-1]) if dates else None
        return {
            "as_at": (as_at or latest).isoformat() if (as_at or latest) else None,
            "current_value": str(contributions.current_value) if contributions.current_value is not None else None,
            "total_contributed": str(contributions.total_contributed),
            "total_withdrawn": str(contributions.total_withdrawn),
            "net_contributed": str(contributions.net_contributed),
            "investment_growth": str(contributions.investment_growth) if contributions.investment_growth is not None else None,
            "income_received": str(contributions.income_received),
            "data_coverage": self.getDataCoverage().to_dict(),
        }

    def getContributions(self, as_at: date | None = None):
        return self.getContributionSummary(as_at)

    def getIncome(self, granularity: Granularity = Granularity.YEARLY,
                 by_security: bool = False) -> list[dict]:
        return self.getIncomeAnalytics(granularity, by_security)

    def getRisk(self) -> dict:
        return self.getRiskMetrics()

    def getDrawdowns(self):
        return self.getDrawdownAnalytics()

    def getMilestones(self) -> list[dict]:
        return self.getMilestoneAnalytics()

    # -- capabilities and coverage (hardening sec 7-8) -------------------------

    def getAnalyticsCapabilities(self) -> dict[str, dict]:
        return _capabilities.get_analytics_capabilities(
            self.history, self.benchmarks, self.config)

    def getDataCoverage(self):
        return _coverage.get_data_coverage(self.history)
