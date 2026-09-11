/**
 * The Holdings screen's data layer (sec 19-20): coordinates every static
 * request the screen needs. Security-detail requests (holding history) are
 * fetched in SecurityDetail itself, parameterised by the selected code, so
 * they only fire when a security is actually selected. This hook performs
 * no financial calculation -- every field it returns is an unmodified API
 * response value, and several queries (overview/capabilities) share a
 * cache key with the Overview/Performance screens, so navigating between
 * screens costs no extra request when the cache is still warm.
 */
import {
  useAllocation, useAllocationHistory, useCapabilities, useConcentration, useHoldings,
  usePortfolioOverview, useUnrealisedGains,
} from "../../hooks/api/usePortfolioApi";

export function useHoldingsData() {
  return {
    overview: usePortfolioOverview(),
    capabilities: useCapabilities(),
    holdings: useHoldings(),
    unrealisedGains: useUnrealisedGains(),
    concentration: useConcentration(),
    allocationBySecurity: useAllocation("security"),
    allocationByAssetClass: useAllocation("asset_class"),
    allocationHistory: useAllocationHistory("asset_class", "yearly"),
  };
}
