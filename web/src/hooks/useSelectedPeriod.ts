import { useSearchParams } from "react-router-dom";

import { getStoredPeriod, setStoredPeriod } from "../lib/periodStorage";
import type { PerformancePeriod } from "../api/types";

export interface SelectedPeriodUrlMapping {
  /** Translate a raw `period` URL value into this screen's own label
   * vocabulary (e.g. the shared URL spelling "MAX" -> this screen's
   * "INCEPTION"). Defaults to the identity mapping. */
  fromUrl?: (value: string) => string;
  /** The inverse of `fromUrl`, applied when writing a selection back to the
   * URL -- so every section that shares the `period` param agrees on one
   * spelling regardless of what each section calls it internally. */
  toUrl?: (value: string) => string;
}

/**
 * The URL-addressable period selection shared by any screen with a
 * standard-period selector (Overview's chart, Performance's summary/chart).
 * Reads/writes the same `period` query param every such screen uses (sec 34:
 * refresh, back/forward and sharing a link all preserve the selection, and
 * navigating between screens carries the same selected window across) and
 * resolves the matching PerformancePeriod the backend already computed --
 * this hook never derives a date range itself, only looks up the one the
 * backend returned for the selected label.
 *
 * When the URL has no `period` param at all -- a detour through a screen
 * that doesn't carry one, or a link that dropped it -- falls back to the
 * last selection persisted in localStorage, so the choice survives that
 * detour rather than silently resetting to `defaultLabel`.
 */
export function useSelectedPeriod(
  periods: PerformancePeriod[] | undefined,
  validLabels: string[],
  defaultLabel: string,
  urlMapping: SelectedPeriodUrlMapping = {},
) {
  const fromUrl = urlMapping.fromUrl ?? ((v: string) => v);
  const toUrl = urlMapping.toUrl ?? ((v: string) => v);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedRaw = searchParams.get("period") ?? getStoredPeriod();
  const requested = requestedRaw ? fromUrl(requestedRaw) : null;
  const selected = requested && validLabels.includes(requested) ? requested : defaultLabel;

  const setSelected = (value: string) => {
    setStoredPeriod(toUrl(value));
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("period", toUrl(value));
        return next;
      },
      { replace: true },
    );
  };

  const activePeriod = periods?.find((p) => p.label === selected);
  return { selected, setSelected, activePeriod };
}
