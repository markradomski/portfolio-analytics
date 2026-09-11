import { useSearchParams } from "react-router-dom";

import type { PerformancePeriod } from "../api/types";

/**
 * The URL-addressable period selection shared by any screen with a
 * standard-period selector (Overview's chart, Performance's summary/chart).
 * Reads/writes the `period` query param (sec 34: refresh, back/forward and
 * sharing a link all preserve the selection) and resolves the matching
 * PerformancePeriod the backend already computed -- this hook never derives
 * a date range itself, only looks up the one the backend returned for the
 * selected label.
 */
export function useSelectedPeriod(
  periods: PerformancePeriod[] | undefined,
  validLabels: string[],
  defaultLabel: string,
) {
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("period");
  const selected = requested && validLabels.includes(requested) ? requested : defaultLabel;

  const setSelected = (value: string) =>
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("period", value);
        return next;
      },
      { replace: true },
    );

  const activePeriod = periods?.find((p) => p.label === selected);
  return { selected, setSelected, activePeriod };
}
