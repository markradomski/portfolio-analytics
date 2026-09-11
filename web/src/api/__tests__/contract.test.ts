/**
 * Guards against the backend and these hand-authored types drifting apart.
 *
 * The OpenAPI schema couldn't fully generate types.ts (see the comment at
 * the top of that file -- response bodies serialise as `unknown` without a
 * per-endpoint Pydantic response_model). Until that's added, this is the
 * next best thing: real API responses, captured from the synthetic test
 * fixture (never real portfolio figures -- see ../__fixtures__), checked
 * against the field names types.ts declares as required. It would not catch
 * a new field the backend added, but it does catch a renamed or removed one,
 * which is the failure mode that actually breaks the frontend silently.
 */
import { describe, expect, it } from "vitest";

import capabilities from "../__fixtures__/capabilities.json";
import coverage from "../__fixtures__/coverage.json";
import overview from "../__fixtures__/overview.json";
import performance from "../__fixtures__/performance.json";
import reconciliation from "../__fixtures__/reconciliation.json";
import risk from "../__fixtures__/risk.json";

function assertHasKeys(subject: unknown, keys: string[], label: string) {
  const obj = subject as Record<string, unknown>;
  for (const key of keys) {
    expect(obj, `${label} is missing "${key}"`).toHaveProperty(key);
  }
}

describe("API contract: PortfolioOverview", () => {
  it("has every field the frontend type declares", () => {
    assertHasKeys(overview, [
      "as_at", "current_value", "total_contributed", "total_withdrawn",
      "net_contributed", "investment_growth", "income_received", "data_coverage",
    ], "PortfolioOverview");
    assertHasKeys(overview.data_coverage, [
      "valuation_start", "valuation_end", "valuation_observation_count",
      "transaction_start", "transaction_end", "price_observation_count",
      "missing_valuation_count", "actual_observation_count",
      "carried_forward_observation_count", "estimated_observation_count",
      "unavailable_observation_count",
    ], "DataCoverage");
  });

  it("sends money as a string, never a number", () => {
    expect(typeof overview.total_contributed).toBe("string");
    expect(typeof overview.current_value).toBe("string");
  });
});

describe("API contract: DataCoverage (standalone endpoint)", () => {
  it("matches the same shape as the embedded copy in overview", () => {
    assertHasKeys(coverage, Object.keys(overview.data_coverage), "DataCoverage");
  });
});

describe("API contract: AnalyticsCapabilities", () => {
  it("every entry has available + reason", () => {
    for (const [name, cap] of Object.entries(capabilities as Record<string, { available: unknown; reason: unknown }>)) {
      expect(cap, name).toHaveProperty("available");
      expect(cap, name).toHaveProperty("reason");
      expect(typeof cap.available, name).toBe("boolean");
    }
  });
});

describe("API contract: PerformanceOverview", () => {
  it("has every field the frontend type declares", () => {
    assertHasKeys(performance, [
      "period_start", "period_end", "opening_value", "closing_value",
      "contributions", "withdrawals", "net_external_flow", "investment_gain",
      "income", "fees", "total_return", "capital_return", "income_return",
      "twrr", "xirr", "data_quality",
    ], "PerformanceOverview");
  });
});

describe("API contract: RiskMetrics / Metric", () => {
  it("every metric carries the full metadata envelope", () => {
    for (const [name, metric] of Object.entries(risk as Record<string, Record<string, unknown>>)) {
      assertHasKeys(metric, [
        "name", "value", "methodology", "data_quality", "available", "reason",
        "observations", "confidence",
      ], name);
    }
  });

  it("an unavailable metric has a null value and a stated reason, never a fabricated number", () => {
    const sharpe = (risk as Record<string, { value: unknown; available: boolean; reason: string | null }>).sharpe_ratio;
    if (!sharpe.available) {
      expect(sharpe.value).toBeNull();
      expect(sharpe.reason).toBeTruthy();
    }
  });
});

describe("API contract: ReconciliationResult", () => {
  it("has the exact hardening-spec vocabulary plus legacy aliases", () => {
    for (const key of ["growth", "attribution"] as const) {
      assertHasKeys((reconciliation as Record<string, unknown>)[key], [
        "attributed_change", "actual_change", "residual", "tolerance",
        "reconciliation_status", "difference", "status",
      ], key);
    }
  });

  it("reconciliation_status is one of the three defined values", () => {
    for (const key of ["growth", "attribution"] as const) {
      const result = (reconciliation as Record<string, { reconciliation_status: string }>)[key];
      expect(["PASS", "FAIL", "LIMITED"]).toContain(result.reconciliation_status);
    }
  });
});
