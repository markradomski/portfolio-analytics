/**
 * The Performance screen's data layer (sec 28): coordinates every static
 * request the screen needs. Period-dependent requests (attribution,
 * reconciliation) are fetched in PerformancePage itself, parameterised by
 * the selected period's own start_date/end_date -- see useSelectedPeriod.
 * This hook performs no financial calculation: every field it returns is
 * an unmodified API response value, and several of its queries
 * (overview/capabilities/periods/methodology/calendar) share a cache key
 * with the Overview screen's own hooks, so navigating between the two
 * costs no extra request when the cache is still warm (sec 29).
 */
import {
  useBestWorst, useCalendarPerformance, useCapabilities, useDrawdowns,
  usePerformanceMethodology, usePerformancePeriods, usePortfolioOverview,
} from "../../hooks/api/usePortfolioApi";

export function usePerformanceData() {
  return {
    overview: usePortfolioOverview(),
    capabilities: useCapabilities(),
    periods: usePerformancePeriods(),
    methodology: usePerformanceMethodology(),
    calendar: useCalendarPerformance(),
    bestWorst: useBestWorst(),
    drawdowns: useDrawdowns(),
  };
}
