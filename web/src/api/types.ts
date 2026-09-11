/**
 * Frontend data model, generated from the API's own OpenAPI schema
 * (Phase 5 Pre-5.5 API contract hardening).
 *
 * Every type below is a thin alias onto `components["schemas"][...]` in
 * schema.generated.ts, which openapi-typescript produces from
 * src/api/app.py's `response_model`s (src/api/models/, backed by Pydantic).
 * Regenerate schema.generated.ts after any Pydantic model change:
 *
 *   ./venv/bin/python -c "import json; from src.api.app import app;
 *     json.dump(app.openapi(), open('web/openapi.json', 'w'), indent=2)"
 *   cd web && npx openapi-typescript openapi.json -o src/api/schema.generated.ts
 *
 * See docs/api.md for the full contract and regeneration workflow.
 *
 * Money and percentages are strings, never numbers: the API sends Decimal
 * values as exact strings specifically so nothing here parses them through
 * an IEEE754 float before the formatting layer decides how to round for
 * display (formatting/money.ts). Pydantic's `DecimalString` (strict str)
 * enforces this at the API boundary; nothing on this side needs to
 * re-validate it, only never coerce it to `number`.
 */

import type { components } from "./schema.generated";

type Schemas = components["schemas"];

// -- shared vocabulary, matching src/analytics/result.py and src/history/config.py

export type DataQuality = "actual" | "calculated" | "estimated" | "limited" | "unavailable";
export type Confidence = "high" | "medium" | "low" | "none";
export type ValuationStatus = "actual" | "calculated" | "estimated" | "unavailable";
export type ReconciliationStatus = "PASS" | "FAIL" | "LIMITED";
export type AssetClass = Schemas["HoldingRow"]["asset_class"];

/** A decimal figure transported as an exact string. Never coerce this to a
 * JS `number` except at the final formatting boundary (formatting/money.ts),
 * and never for a comparison or calculation -- that would be recreating
 * financial logic in the frontend, which Phase 5 must never do. */
export type Money = string;
export type Percent = string;
export type ISODate = string;

// -- one alias per response model in src/api/models/ -------------------------

export type Metric = Schemas["Metric"];
export type Capability = Schemas["Capability"];
export type AnalyticsCapabilities = Record<string, Capability>;
export type DataCoverage = Schemas["DataCoverage"];

export type PortfolioOverview = Schemas["PortfolioOverview"];
export type ContributionSummary = Schemas["ContributionSummary"];
export type ContributionHistoryRow = Schemas["ContributionHistoryRow"];

export type PerformanceOverview = Schemas["PerformanceOverview"];
export type PerformancePeriod = Schemas["PerformancePeriod"];
export type TwrrMethodology = Schemas["TwrrMethodology"];
export type PerformanceMethodology = Schemas["PerformanceMethodology"];

export type PortfolioDailyPoint = Schemas["PortfolioDailyPoint"];
export type HoldingRow = Schemas["HoldingRow"];
export type PortfolioState = Schemas["PortfolioState"];
export type AllocationResult = Schemas["AllocationResult"];
export type AllocationHistoryPoint = Schemas["AllocationHistoryPoint"];
export type ConcentrationSnapshot = Schemas["ConcentrationSnapshot"];

export type IncomeRow = Schemas["IncomeRow"];
export type IncomeGrowthRow = Schemas["IncomeGrowthRow"];
export type IncomeYieldResponse = Schemas["IncomeYieldResponse"];

export type RealisedGainSummary = Schemas["RealisedGainSummary"];
export type UnrealisedGainSnapshot = Schemas["UnrealisedGainSnapshot"];

export type SecurityAttributionRow = Schemas["SecurityAttributionRow"];
export type AttributionTree = Schemas["AttributionTree"];
export type ReconciliationResult = Schemas["ReconciliationResult"];
export type AttributionReconciliationPair = Schemas["AttributionReconciliationPair"];

export type RiskMetrics = Schemas["RiskMetrics"];
export type DrawdownAnalytics = Schemas["DrawdownAnalytics"];
// DrawdownEpisode (src/api/models/risk.py) has no route surfacing it yet --
// history.drawdown_history() isn't wired to an endpoint, so
// openapi-typescript never emits it into components.schemas. Re-add this
// alias if/when that endpoint is added.
export type HighWaterMarkStatus = Schemas["HighWaterMarkStatus"];
export type BenchmarkComparison = Schemas["BenchmarkComparison"];
export type RollingReturnPoint = Schemas["RollingReturnPoint"];
export type RollingVolatilityPoint = Schemas["RollingVolatilityPoint"];
export type RollingIncomeYieldPoint = Schemas["RollingIncomeYieldPoint"];

export type CalendarPerformanceRow = Schemas["CalendarPerformanceRow"];
export type ExtremePeriod = Schemas["ExtremePeriod"];
export type BestWorstPeriods = Record<string, ExtremePeriod[] | string>;
export type Milestone = Schemas["Milestone"];
export type ActivityRow = Schemas["ActivityRow"];
export type HealthStatus = Schemas["HealthStatus"];

// -- Portfolio Growth (Step 9) -- the canonical dataset behind the
// redesigned primary chart. See docs/portfolio-growth.md.
export type CashFlowEvent = Schemas["CashFlowEvent"];
export type PortfolioGrowthPoint = Schemas["PortfolioGrowthPoint"];
export type PortfolioGrowthSummary = Schemas["PortfolioGrowthSummary"];
export type PortfolioValueReconciliationCheck = Schemas["PortfolioValueReconciliationCheck"];
