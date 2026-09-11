/**
 * The performance/analytics API adapter: performance, standard periods,
 * methodology. Split from portfolio.ts along the same line
 * src/analytics/service.py already draws.
 */

import { apiGet } from "./client";
import type { PerformanceMethodology, PerformanceOverview, PerformancePeriod } from "./types";

export const analyticsApi = {
  performance: (start: string, end: string) =>
    apiGet<PerformanceOverview>("/api/portfolio/performance", { start, end }),
  performanceForYear: (year: number) =>
    apiGet<PerformanceOverview>(`/api/portfolio/performance/year/${year}`),
  performancePeriods: () =>
    apiGet<PerformancePeriod[]>("/api/portfolio/performance/periods"),
  performanceMethodology: () =>
    apiGet<PerformanceMethodology>("/api/portfolio/performance/methodology"),
};
