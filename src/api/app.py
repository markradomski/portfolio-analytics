"""HTTP API over the Phase 4 analytics service.

This is the boundary Phase 5 is required to consume through -- nothing in
src/engine/ or src/history/ is importable from the frontend, and nothing here
performs a financial calculation. Every handler is a thin translation:
parse query params, call one AnalyticsService/HistoryService method, and
serialise the result. If a screen needs a figure this layer doesn't expose,
the fix is a new endpoint here (backed by an existing or new Phase 4
function), never a calculation added on the frontend side.

Every route declares a `response_model` from src/api/models/ (API contract
hardening) so OpenAPI describes the real response shape and TypeScript can
be generated from it, instead of the generic JSON body this layer returned
before. Handlers still return the already-JSON-safe dict/list `to_json()`
produces -- FastAPI validates that shape against the declared model on the
way out; nothing here recalculates anything Phase 2-4 already computed.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.analytics.config import DEFAULT_ANALYTICS_CONFIG
from src.analytics.service import AnalyticsService
from src.api import models as m
from src.api.serialize import to_json
from src.database.repository import Repository
from src.history.config import Granularity

# PORTFOLIO_DB_PATH lets a deployment or demo point at a different database
# (e.g. the synthetic demo dataset in demo-data/) without touching code --
# defaults to the same path every CLI command already writes to.
DB_PATH = Path(os.environ.get(
    "PORTFOLIO_DB_PATH",
    str(Path(__file__).resolve().parents[2] / "data/processed/portfolio.db"),
))

app = FastAPI(
    title="Portfolio Analytics API",
    description="Read-only API over the Phase 4 analytics layer. Every"
    " figure traces to Phase 2 (accounting) or Phase 3 (historical series);"
    " this layer adds no financial calculation of its own.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # Vite picks the first free port from 5173 upward, so a fixed origin
    # list breaks the moment something else is already listening on 5173 --
    # match any localhost port in development rather than hard-coding one.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _service() -> AnalyticsService:
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Portfolio database not built yet. Run "
                   "'python -m src.cli import' and 'rebuild-history' first.")
    repo = Repository(DB_PATH)
    return AnalyticsService(repo, DEFAULT_ANALYTICS_CONFIG)


def Ok(content):
    """Converts Decimals/dates/dataclasses/enums to JSON-safe primitives
    (str/int/bool/None/dict/list) via to_json(), then returns that plain
    value so FastAPI runs it through the route's declared `response_model`
    for real: validating shape/nullability and re-serialising it, rather
    than a raw Response subclass FastAPI would pass through unvalidated.
    This is what makes response_model an enforced contract (sec 4, 10, 13),
    not documentation only -- returning a Response subclass here was tried
    and confirmed to skip response_model validation entirely."""
    return to_json(content)


def _granularity(value: str) -> Granularity:
    try:
        return Granularity(value)
    except ValueError:
        raise HTTPException(422, f"invalid granularity {value!r}")


# -- overview / capabilities / coverage --------------------------------------

@app.get("/api/portfolio/overview", response_model=m.PortfolioOverview)
def overview(as_at: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getPortfolioOverview(as_at))
    finally:
        service.repo.close()


@app.get("/api/portfolio/capabilities", response_model=m.AnalyticsCapabilities)
def capabilities():
    service = _service()
    try:
        return Ok(service.getAnalyticsCapabilities())
    finally:
        service.repo.close()


@app.get("/api/portfolio/coverage", response_model=m.DataCoverage)
def coverage():
    service = _service()
    try:
        return Ok(service.getDataCoverage())
    finally:
        service.repo.close()


# -- performance --------------------------------------------------------------

@app.get("/api/portfolio/performance", response_model=m.PerformanceOverview)
def performance(start: date, end: date):
    service = _service()
    try:
        return Ok(service.getPerformance(start, end))
    finally:
        service.repo.close()


@app.get("/api/portfolio/performance/year/{year}", response_model=m.PerformanceOverview)
def performance_for_year(year: int):
    service = _service()
    try:
        result = service.getPerformanceForYear(year)
        if result is None:
            raise HTTPException(404, f"no performance data for {year}")
        return Ok(result)
    finally:
        service.repo.close()


@app.get("/api/portfolio/performance/periods", response_model=list[m.PerformancePeriod])
def performance_periods():
    service = _service()
    try:
        return Ok(service.getReturns())
    finally:
        service.repo.close()


@app.get("/api/portfolio/performance/methodology", response_model=m.PerformanceMethodology)
def performance_methodology():
    service = _service()
    try:
        from src.analytics.performance import twrr_methodology_metadata
        return Ok({
            "return_methodology": service.getReturnMethodology(),
            "twrr": twrr_methodology_metadata(service.history),
        })
    finally:
        service.repo.close()


# -- historical series (primary chart) -----------------------------------------

@app.get("/api/portfolio/history", response_model=list[m.PortfolioDailyPoint])
def history(start: Optional[date] = None, end: Optional[date] = None,
           granularity: str = "daily"):
    service = _service()
    try:
        return Ok(service.history.portfolio_history(
            start, end, _granularity(granularity)))
    finally:
        service.repo.close()


# -- portfolio growth (Step 9 -- the primary chart's canonical dataset) --------

@app.get("/api/portfolio/growth", response_model=list[m.PortfolioGrowthPoint])
def portfolio_growth(start: Optional[date] = None, end: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getPortfolioGrowth(start, end))
    finally:
        service.repo.close()


@app.get("/api/portfolio/growth/summary", response_model=m.PortfolioGrowthSummary)
def portfolio_growth_summary(as_at: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getPortfolioGrowthSummary(as_at))
    finally:
        service.repo.close()


@app.get("/api/portfolio/growth/reconciliation",
        response_model=list[m.PortfolioValueReconciliationCheck])
def portfolio_growth_reconciliation():
    service = _service()
    try:
        return Ok(service.getPortfolioValueReconciliation())
    finally:
        service.repo.close()


# -- holdings & allocation ------------------------------------------------------

@app.get("/api/portfolio/holdings", response_model=m.PortfolioState | list[m.HoldingRow])
def holdings(on: Optional[date] = None):
    service = _service()
    try:
        target = on or _latest(service)
        if target is None:
            return Ok([])
        return Ok(service.history.portfolio_state(target))
    finally:
        service.repo.close()


@app.get("/api/portfolio/holdings/{code}/history", response_model=list[m.HoldingRow])
def holding_history(code: str, start: Optional[date] = None, end: Optional[date] = None):
    service = _service()
    try:
        rows = service.history.holdings_history(start=start, end=end)
        return Ok([r for r in rows if r["code"] == code])
    finally:
        service.repo.close()


@app.get("/api/portfolio/allocation", response_model=m.AllocationResult)
def allocation(by: str = "asset_class", on: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getAllocation(by, on))
    finally:
        service.repo.close()


@app.get("/api/portfolio/allocation/history", response_model=list[m.AllocationHistoryPoint])
def allocation_history(by: str = "asset_class", granularity: str = "monthly"):
    service = _service()
    try:
        return Ok(service.getAllocationHistory(by, _granularity(granularity)))
    finally:
        service.repo.close()


@app.get("/api/portfolio/concentration", response_model=m.ConcentrationSnapshot)
def concentration(on: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getConcentration(on))
    finally:
        service.repo.close()


# -- income ---------------------------------------------------------------------

@app.get("/api/portfolio/income", response_model=list[m.IncomeRow])
def income(granularity: str = "yearly", by_security: bool = False):
    service = _service()
    try:
        return Ok(service.getIncome(_granularity(granularity), by_security))
    finally:
        service.repo.close()


@app.get("/api/portfolio/income/yield", response_model=m.IncomeYieldResponse)
def income_yield(as_at: Optional[date] = None):
    service = _service()
    try:
        return Ok({
            "trailing": service.getTrailingIncomeYield(as_at),
            "forward": service.getForwardIncomeYield(as_at),
        })
    finally:
        service.repo.close()


@app.get("/api/portfolio/income/growth", response_model=list[m.IncomeGrowthRow])
def income_growth():
    service = _service()
    try:
        return Ok(service.getIncomeGrowth())
    finally:
        service.repo.close()


# -- contributions ----------------------------------------------------------------

@app.get("/api/portfolio/contributions", response_model=m.ContributionSummary)
def contributions(as_at: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getContributions(as_at))
    finally:
        service.repo.close()


@app.get("/api/portfolio/contributions/history", response_model=list[m.ContributionHistoryRow])
def contributions_history(granularity: str = "yearly"):
    service = _service()
    try:
        return Ok(service.history.contribution_history(_granularity(granularity)))
    finally:
        service.repo.close()


# -- gains & attribution -----------------------------------------------------------

@app.get("/api/portfolio/gains/realised", response_model=m.RealisedGainSummary)
def realised_gains(start: Optional[date] = None, end: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getRealisedGains(start, end))
    finally:
        service.repo.close()


@app.get("/api/portfolio/gains/unrealised", response_model=list[m.UnrealisedGainSnapshot])
def unrealised_gains(on: Optional[date] = None):
    service = _service()
    try:
        target = on or _latest(service)
        if target is None:
            return Ok([])
        return Ok(service.getUnrealisedGains(target))
    finally:
        service.repo.close()


@app.get("/api/portfolio/attribution", response_model=m.AttributionTree)
def attribution(start: date, end: date):
    service = _service()
    try:
        return Ok(service.getAttribution(start, end))
    finally:
        service.repo.close()


@app.get("/api/portfolio/attribution/securities", response_model=list[m.SecurityAttributionRow])
def security_attribution(start: date, end: date):
    service = _service()
    try:
        return Ok(service.getSecurityPerformance(start, end))
    finally:
        service.repo.close()


@app.get("/api/portfolio/attribution/reconciliation",
        response_model=m.AttributionReconciliationPair)
def attribution_reconciliation(start: date, end: date):
    service = _service()
    try:
        return Ok({
            "growth": service.getGrowthReconciliation(start, end),
            "attribution": service.getAttributionReconciliation(start, end),
        })
    finally:
        service.repo.close()


# -- risk ---------------------------------------------------------------------------

@app.get("/api/portfolio/risk", response_model=m.RiskMetrics)
def risk():
    service = _service()
    try:
        return Ok(service.getRisk())
    finally:
        service.repo.close()


@app.get("/api/portfolio/risk/benchmark", response_model=m.BenchmarkComparison)
def risk_benchmark(period: str = "1Y", benchmark_id: Optional[str] = None):
    service = _service()
    try:
        if not benchmark_id:
            return Ok({
                "portfolio_methodology": "N/A",
                "methodology_mismatch": False,
                "status": "unavailable",
                "note": "No benchmark registered",
            })
        return Ok(service.getBenchmarkComparison(period, benchmark_id))
    finally:
        service.repo.close()


@app.get("/api/portfolio/drawdowns", response_model=m.DrawdownAnalytics)
def drawdowns():
    service = _service()
    try:
        return Ok(service.getDrawdowns())
    finally:
        service.repo.close()


@app.get("/api/portfolio/drawdowns/high-water-mark", response_model=m.HighWaterMarkStatus)
def high_water_mark(on: Optional[date] = None):
    service = _service()
    try:
        return Ok(service.getHighWaterMarkStatus(on))
    finally:
        service.repo.close()


@app.get("/api/portfolio/risk/rolling",
        response_model=list[m.RollingReturnPoint] | list[m.RollingVolatilityPoint]
        | list[m.RollingIncomeYieldPoint])
def rolling(metric: str = "return", window_days: int = 90, window_quarters: int = 8):
    service = _service()
    try:
        if metric == "volatility":
            return Ok(service.getRollingVolatility(window_quarters))
        if metric == "income_yield":
            return Ok(service.getRollingIncomeYield())
        return Ok(service.getRollingMetrics(window_days))
    finally:
        service.repo.close()


# -- calendar / milestones / history -------------------------------------------------

@app.get("/api/portfolio/calendar", response_model=list[m.CalendarPerformanceRow])
def calendar(granularity: str = "yearly"):
    service = _service()
    try:
        return Ok(service.getCalendarPerformance(_granularity(granularity)))
    finally:
        service.repo.close()


@app.get("/api/portfolio/best-worst", response_model=m.BestWorstPeriods)
def best_worst():
    service = _service()
    try:
        return Ok(service.getBestWorstPeriods())
    finally:
        service.repo.close()


@app.get("/api/portfolio/milestones", response_model=list[m.Milestone])
def milestones():
    service = _service()
    try:
        return Ok(service.getMilestones())
    finally:
        service.repo.close()


@app.get("/api/portfolio/activity", response_model=list[m.ActivityRow])
def activity(start: Optional[date] = None, end: Optional[date] = None, limit: int = 200):
    """A presentation of existing Phase 1/2 transaction records -- not a new
    transaction engine (sec 27). Sorted most recent first."""
    service = _service()
    try:
        clauses, params = [], []
        if start:
            clauses.append("t.trade_date >= ?"); params.append(start.isoformat())
        if end:
            clauses.append("t.trade_date <= ?"); params.append(end.isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = service.repo.rows(
            "SELECT t.transaction_id, t.trade_date, t.type, s.code, t.units,"
            " t.price, t.net_amount, t.description FROM transactions t"
            " LEFT JOIN securities s USING (security_id)"
            f"{where} ORDER BY t.trade_date DESC, t.transaction_id DESC LIMIT ?",
            tuple(params) + (limit,))
        return Ok([dict(r) for r in rows])
    finally:
        service.repo.close()


@app.get("/api/health", response_model=m.HealthStatus)
def health():
    return Ok({"status": "ok", "database": DB_PATH.exists()})


def _latest(service: AnalyticsService) -> date | None:
    dates = sorted(r["date"] for r in service.history.portfolio_history())
    return date.fromisoformat(dates[-1]) if dates else None
