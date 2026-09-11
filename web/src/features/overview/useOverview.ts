/**
 * The Overview's data layer (sec 20): coordinates every request the screen
 * needs and hands back typed React Query results. OverviewPage never
 * imports portfolioApi/analyticsApi directly -- it reads only from this
 * hook. This hook performs no financial calculation: every field it
 * returns is an unmodified API response value.
 *
 * `history`/`activity`/`capabilities`/`methodology`/`incomeYield` are not
 * rendered directly by OverviewPage (the Portfolio Growth chart reads its
 * own dedicated usePortfolioGrowth()/usePortfolioGrowthSummary() instead,
 * per Step 9) -- they're kept here deliberately as a warm-cache prefetch:
 * Performance and History already fetch the same `history`/`activity`
 * query keys, and Performance/Income already fetch the same
 * `capabilities`/`methodology`/`incomeYield` keys, so navigating from
 * Overview to any of them costs no extra request once the cache is warm.
 */
import {
  useActivity, useAllocation, useCapabilities, useHoldings, useIncome,
  useIncomeYield, usePerformanceMethodology, usePerformancePeriods,
  usePortfolioHistory, usePortfolioOverview, useUnrealisedGains,
} from "../../hooks/api/usePortfolioApi";

export function useOverviewData() {
  return {
    overview: usePortfolioOverview(),
    capabilities: useCapabilities(),
    periods: usePerformancePeriods(),
    methodology: usePerformanceMethodology(),
    allocation: useAllocation("asset_class"),
    holdings: useHoldings(),
    unrealisedGains: useUnrealisedGains(),
    income: useIncome("yearly"),
    incomeYield: useIncomeYield(),
    // Fetched once, unbounded (sec 33: avoid a repeated request per period
    // tab) -- OverviewChart slices this single series client-side by each
    // period's own start_date/end_date instead of re-fetching per tab.
    history: usePortfolioHistory(),
    activity: useActivity(),
  };
}
