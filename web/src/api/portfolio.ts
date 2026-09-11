/**
 * The portfolio API adapter: overview, holdings, allocation, income,
 * contributions, gains, activity. Every function here maps 1:1 to one
 * endpoint in src/api/app.py -- no aggregation or calculation happens here,
 * only the HTTP call and its typed return.
 */

import { apiGet } from "./client";
import type {
  ActivityRow, AllocationHistoryPoint, AllocationResult, AnalyticsCapabilities,
  AttributionReconciliationPair, AttributionTree, BenchmarkComparison,
  BestWorstPeriods, CalendarPerformanceRow, ConcentrationSnapshot,
  ContributionHistoryRow, ContributionSummary, DataCoverage, DrawdownAnalytics,
  HighWaterMarkStatus, HoldingRow, IncomeGrowthRow, IncomeRow, IncomeYieldResponse,
  Milestone, PortfolioDailyPoint, PortfolioGrowthPoint, PortfolioGrowthSummary,
  PortfolioOverview, PortfolioState, PortfolioValueReconciliationCheck,
  RealisedGainSummary, RiskMetrics, RollingIncomeYieldPoint, RollingReturnPoint,
  RollingVolatilityPoint, SecurityAttributionRow, UnrealisedGainSnapshot,
} from "./types";

export type Granularity = "daily" | "weekly" | "monthly" | "quarterly" | "yearly";

export const portfolioApi = {
  overview: (asAt?: string) => apiGet<PortfolioOverview>("/api/portfolio/overview", { as_at: asAt }),
  capabilities: () => apiGet<AnalyticsCapabilities>("/api/portfolio/capabilities"),
  coverage: () => apiGet<DataCoverage>("/api/portfolio/coverage"),

  history: (start?: string, end?: string, granularity: Granularity = "daily") =>
    apiGet<PortfolioDailyPoint[]>("/api/portfolio/history", { start, end, granularity }),

  // Step 9: the canonical Portfolio Growth dataset -- portfolio value vs.
  // net contributions vs. investment gain, plus that day's own cash-flow
  // events, for an arbitrary date range. See docs/portfolio-growth.md.
  growth: (start?: string, end?: string) =>
    apiGet<PortfolioGrowthPoint[]>("/api/portfolio/growth", { start, end }),
  growthSummary: (asAt?: string) =>
    apiGet<PortfolioGrowthSummary>("/api/portfolio/growth/summary", { as_at: asAt }),
  growthReconciliation: () =>
    apiGet<PortfolioValueReconciliationCheck[]>("/api/portfolio/growth/reconciliation"),

  holdings: (on?: string) => apiGet<PortfolioState>("/api/portfolio/holdings", { on }),
  holdingHistory: (code: string, start?: string, end?: string) =>
    apiGet<HoldingRow[]>(`/api/portfolio/holdings/${code}/history`, { start, end }),

  allocation: (by = "asset_class", on?: string) =>
    apiGet<AllocationResult>("/api/portfolio/allocation", { by, on }),
  allocationHistory: (by = "asset_class", granularity: Granularity = "monthly") =>
    apiGet<AllocationHistoryPoint[]>("/api/portfolio/allocation/history", { by, granularity }),
  concentration: (on?: string) => apiGet<ConcentrationSnapshot>("/api/portfolio/concentration", { on }),

  income: (granularity: Granularity = "yearly", bySecurity = false) =>
    apiGet<IncomeRow[]>("/api/portfolio/income", { granularity, by_security: bySecurity }),
  incomeYield: (asAt?: string) => apiGet<IncomeYieldResponse>("/api/portfolio/income/yield", { as_at: asAt }),
  incomeGrowth: () => apiGet<IncomeGrowthRow[]>("/api/portfolio/income/growth"),

  contributions: (asAt?: string) => apiGet<ContributionSummary>("/api/portfolio/contributions", { as_at: asAt }),
  contributionsHistory: (granularity: Granularity = "yearly") =>
    apiGet<ContributionHistoryRow[]>("/api/portfolio/contributions/history", { granularity }),

  realisedGains: (start?: string, end?: string) =>
    apiGet<RealisedGainSummary>("/api/portfolio/gains/realised", { start, end }),
  unrealisedGains: (on?: string) => apiGet<UnrealisedGainSnapshot[]>("/api/portfolio/gains/unrealised", { on }),

  attribution: (start: string, end: string) => apiGet<AttributionTree>("/api/portfolio/attribution", { start, end }),
  securityAttribution: (start: string, end: string) =>
    apiGet<SecurityAttributionRow[]>("/api/portfolio/attribution/securities", { start, end }),
  attributionReconciliation: (start: string, end: string) =>
    apiGet<AttributionReconciliationPair>("/api/portfolio/attribution/reconciliation", { start, end }),

  risk: () => apiGet<RiskMetrics>("/api/portfolio/risk"),
  riskBenchmark: (period = "1Y", benchmarkId?: string) =>
    apiGet<BenchmarkComparison>("/api/portfolio/risk/benchmark", { period, benchmark_id: benchmarkId }),
  // getDrawdowns() (src/analytics/service.py) returns one summary object,
  // not a list of episodes -- fixed here after the response_model migration
  // caught this endpoint's type as previously mismatched (it was typed
  // DrawdownEpisode[] before, which the real handler never returned).
  drawdowns: () => apiGet<DrawdownAnalytics>("/api/portfolio/drawdowns"),
  highWaterMark: (on?: string) => apiGet<HighWaterMarkStatus>("/api/portfolio/drawdowns/high-water-mark", { on }),
  rollingVolatility: (windowQuarters = 8) =>
    apiGet<RollingVolatilityPoint[]>("/api/portfolio/risk/rolling", { metric: "volatility", window_quarters: windowQuarters }),
  rollingReturn: (windowDays = 90) =>
    apiGet<RollingReturnPoint[]>("/api/portfolio/risk/rolling", { metric: "return", window_days: windowDays }),
  rollingIncomeYield: () =>
    apiGet<RollingIncomeYieldPoint[]>("/api/portfolio/risk/rolling", { metric: "income_yield" }),

  calendar: (granularity: Granularity = "yearly") =>
    apiGet<CalendarPerformanceRow[]>("/api/portfolio/calendar", { granularity }),
  bestWorst: () => apiGet<BestWorstPeriods>("/api/portfolio/best-worst"),
  milestones: () => apiGet<Milestone[]>("/api/portfolio/milestones"),
  activity: (start?: string, end?: string, limit = 200) =>
    apiGet<ActivityRow[]>("/api/portfolio/activity", { start, end, limit }),
};
