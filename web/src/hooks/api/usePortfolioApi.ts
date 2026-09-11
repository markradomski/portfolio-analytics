/**
 * Thin React Query wrappers over the API adapter (sec 1/5). Every screen
 * fetches data through one of these, never through a bare useEffect+fetch
 * -- so loading/error states, caching and refetch behaviour are consistent
 * everywhere, and no component ever touches src/api/client.ts directly.
 */
import { useQuery } from "@tanstack/react-query";

import { portfolioApi, type Granularity } from "../../api/portfolio";
import { analyticsApi } from "../../api/analytics";

const STALE_TIME = 5 * 60 * 1000; // portfolio history changes at most quarterly

export function usePortfolioOverview(asAt?: string) {
  return useQuery({ queryKey: ["overview", asAt], queryFn: () => portfolioApi.overview(asAt), staleTime: STALE_TIME });
}

export function useCapabilities() {
  return useQuery({ queryKey: ["capabilities"], queryFn: portfolioApi.capabilities, staleTime: STALE_TIME });
}

export function useDataCoverage() {
  return useQuery({ queryKey: ["coverage"], queryFn: portfolioApi.coverage, staleTime: STALE_TIME });
}

export function usePortfolioHistory(start?: string, end?: string) {
  return useQuery({
    queryKey: ["history", start, end],
    queryFn: () => portfolioApi.history(start, end),
    staleTime: STALE_TIME,
  });
}

// Step 9: fetched once, unbounded (same convention as usePortfolioHistory
// above and Overview's own history fetch) -- PortfolioGrowthChart slices
// this single series client-side by period (1Y/3Y/5Y/All) rather than
// re-fetching per tab.
export function usePortfolioGrowth(start?: string, end?: string) {
  return useQuery({
    queryKey: ["growth", start, end],
    queryFn: () => portfolioApi.growth(start, end),
    staleTime: STALE_TIME,
  });
}

export function usePortfolioGrowthSummary(asAt?: string) {
  return useQuery({
    queryKey: ["growth-summary", asAt],
    queryFn: () => portfolioApi.growthSummary(asAt),
    staleTime: STALE_TIME,
  });
}

export function usePortfolioGrowthReconciliation() {
  return useQuery({
    queryKey: ["growth-reconciliation"],
    queryFn: portfolioApi.growthReconciliation,
    staleTime: STALE_TIME,
  });
}

export function usePerformancePeriods() {
  return useQuery({ queryKey: ["performance-periods"], queryFn: analyticsApi.performancePeriods, staleTime: STALE_TIME });
}

/** The dollar-denominated counterpart to a PerformancePeriod entry -- the
 * same window's opening/closing value and investment_gain in currency
 * terms, which getReturns() itself does not carry (it's percentage-only).
 * Reuses the existing /api/portfolio/performance endpoint rather than
 * adding a new one (sec 8). */
export function usePerformanceOverview(start?: string, end?: string) {
  return useQuery({
    queryKey: ["performance-overview", start, end],
    queryFn: () => analyticsApi.performance(start!, end!),
    enabled: Boolean(start && end),
    staleTime: STALE_TIME,
  });
}

export function usePerformanceForYear(year: number) {
  return useQuery({
    queryKey: ["performance-year", year],
    queryFn: () => analyticsApi.performanceForYear(year),
    staleTime: STALE_TIME,
  });
}

export function useRiskMetrics() {
  return useQuery({ queryKey: ["risk"], queryFn: portfolioApi.risk, staleTime: STALE_TIME });
}

export function useAllocation(by = "asset_class") {
  return useQuery({ queryKey: ["allocation", by], queryFn: () => portfolioApi.allocation(by), staleTime: STALE_TIME });
}

export function useMilestones() {
  return useQuery({ queryKey: ["milestones"], queryFn: portfolioApi.milestones, staleTime: STALE_TIME });
}

export function useHoldings(on?: string) {
  return useQuery({ queryKey: ["holdings", on], queryFn: () => portfolioApi.holdings(on), staleTime: STALE_TIME });
}

export function useUnrealisedGains(on?: string) {
  return useQuery({
    queryKey: ["gains-unrealised", on],
    queryFn: () => portfolioApi.unrealisedGains(on),
    staleTime: STALE_TIME,
  });
}

export function useIncome(granularity: "yearly" | "monthly" | "quarterly" = "yearly") {
  return useQuery({ queryKey: ["income", granularity], queryFn: () => portfolioApi.income(granularity), staleTime: STALE_TIME });
}

export function useIncomeYield(asAt?: string) {
  return useQuery({ queryKey: ["income-yield", asAt], queryFn: () => portfolioApi.incomeYield(asAt), staleTime: STALE_TIME });
}

export function useActivity(start?: string, end?: string) {
  return useQuery({
    queryKey: ["activity", start, end],
    queryFn: () => portfolioApi.activity(start, end),
    staleTime: STALE_TIME,
  });
}

export function usePerformanceMethodology() {
  return useQuery({
    queryKey: ["performance-methodology"],
    queryFn: analyticsApi.performanceMethodology,
    staleTime: STALE_TIME,
  });
}

export function useCalendarPerformance() {
  return useQuery({ queryKey: ["calendar"], queryFn: () => portfolioApi.calendar("yearly"), staleTime: STALE_TIME });
}

export function useBestWorst() {
  return useQuery({ queryKey: ["best-worst"], queryFn: portfolioApi.bestWorst, staleTime: STALE_TIME });
}

export function useDrawdowns() {
  return useQuery({ queryKey: ["drawdowns"], queryFn: portfolioApi.drawdowns, staleTime: STALE_TIME });
}

export function useAttribution(start?: string, end?: string) {
  return useQuery({
    queryKey: ["attribution", start, end],
    queryFn: () => portfolioApi.attribution(start!, end!),
    enabled: Boolean(start && end),
    staleTime: STALE_TIME,
  });
}

export function useAttributionReconciliation(start?: string, end?: string) {
  return useQuery({
    queryKey: ["attribution-reconciliation", start, end],
    queryFn: () => portfolioApi.attributionReconciliation(start!, end!),
    enabled: Boolean(start && end),
    staleTime: STALE_TIME,
  });
}

export function useConcentration(on?: string) {
  return useQuery({ queryKey: ["concentration", on], queryFn: () => portfolioApi.concentration(on), staleTime: STALE_TIME });
}

export function useAllocationHistory(by = "asset_class", granularity: Granularity = "yearly") {
  return useQuery({
    queryKey: ["allocation-history", by, granularity],
    queryFn: () => portfolioApi.allocationHistory(by, granularity),
    staleTime: STALE_TIME,
  });
}

export function useHoldingHistory(code: string | undefined, start?: string, end?: string) {
  return useQuery({
    queryKey: ["holding-history", code, start, end],
    queryFn: () => portfolioApi.holdingHistory(code!, start, end),
    enabled: Boolean(code),
    staleTime: STALE_TIME,
  });
}

export function useIncomeGrowth() {
  return useQuery({ queryKey: ["income-growth"], queryFn: portfolioApi.incomeGrowth, staleTime: STALE_TIME });
}

export function useContributionsSummary(asAt?: string) {
  return useQuery({
    queryKey: ["contributions-summary", asAt],
    queryFn: () => portfolioApi.contributions(asAt),
    staleTime: STALE_TIME,
  });
}

export function useContributionsHistory(granularity: Granularity = "yearly") {
  return useQuery({
    queryKey: ["contributions-history", granularity],
    queryFn: () => portfolioApi.contributionsHistory(granularity),
    staleTime: STALE_TIME,
  });
}

export function useRealisedGains(start?: string, end?: string) {
  return useQuery({
    queryKey: ["realised-gains", start, end],
    queryFn: () => portfolioApi.realisedGains(start, end),
    staleTime: STALE_TIME,
  });
}

export function useHighWaterMark(on?: string) {
  return useQuery({
    queryKey: ["high-water-mark", on],
    queryFn: () => portfolioApi.highWaterMark(on),
    staleTime: STALE_TIME,
  });
}

export function useRiskBenchmark(period = "1Y", benchmarkId?: string) {
  return useQuery({
    queryKey: ["risk-benchmark", period, benchmarkId],
    queryFn: () => portfolioApi.riskBenchmark(period, benchmarkId),
    staleTime: STALE_TIME,
  });
}
