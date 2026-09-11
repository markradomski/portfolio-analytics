/**
 * IncomePage acceptance coverage (sec 33). Mocks the data hooks at the
 * module boundary, same convention as PerformancePage.test.tsx.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { IncomePage } from "../IncomePage";
import type { DataCoverage, IncomeGrowthRow, IncomeRow, IncomeYieldResponse, Metric } from "../../../api/types";

const mockUseIncome = vi.fn();
const mockUseIncomeGrowth = vi.fn();
const mockUseIncomeYield = vi.fn();
const mockUseDataCoverage = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  useIncome: () => mockUseIncome(),
  useIncomeGrowth: () => mockUseIncomeGrowth(),
  useIncomeYield: () => mockUseIncomeYield(),
  useDataCoverage: () => mockUseDataCoverage(),
}));

function ok<T>(data: T) {
  return { isPending: false, isError: false, data };
}
function pending() {
  return { isPending: true, isError: false, data: undefined };
}

function metric(overrides: Partial<Metric>): Metric {
  return {
    name: "trailing_income_yield", value: "0.032", methodology: "TRAILING_12M", data_quality: "actual",
    source: "computed", available: true, reason: null, ...overrides,
  };
}

const yieldResponse: IncomeYieldResponse = {
  trailing: metric({ name: "trailing_income_yield" }),
  forward: metric({ name: "forward_income_yield", value: "0.029" }),
};

const incomeRows: IncomeRow[] = [
  { period_end: "2025-06-30", code: null, dividends: "500", distributions: "1200", interests: "10",
    gross_income: "1710", franking_credits: "150", tax_withheld: "0", net_income: "1860" },
];

const growthRows: IncomeGrowthRow[] = [
  { year: "2025", gross_income: "1710", growth_pct: "0.08", decomposition: "yoy" },
];

const coverage: DataCoverage = {
  valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
  transaction_start: "2020-09-30", transaction_end: "2026-06-30", price_observation_count: 24,
  missing_valuation_count: 0, actual_observation_count: 24, carried_forward_observation_count: 1920,
  estimated_observation_count: 0, unavailable_observation_count: 108,
};

function setupDefaults() {
  mockUseIncome.mockReturnValue(ok(incomeRows));
  mockUseIncomeGrowth.mockReturnValue(ok(growthRows));
  mockUseIncomeYield.mockReturnValue(ok(yieldResponse));
  mockUseDataCoverage.mockReturnValue(ok(coverage));
}

describe("IncomePage", () => {
  it("renders trailing/forward yield and income rows from the API", () => {
    setupDefaults();
    render(<IncomePage />);
    expect(screen.getByText("+3.2%")).toBeInTheDocument();
    expect(screen.getByText("+2.9%")).toBeInTheDocument();
    expect(screen.getAllByText("2025").length).toBeGreaterThan(0);
  });

  it("shows an unavailable reason, not 0%, when yield is not available", () => {
    mockUseIncome.mockReturnValue(ok(incomeRows));
    mockUseIncomeGrowth.mockReturnValue(ok(growthRows));
    mockUseIncomeYield.mockReturnValue(
      ok({
        trailing: metric({ available: false, value: null, reason: "No distributions in the trailing period" }),
        forward: metric({ available: false, value: null, reason: "No forward estimate available" }),
      }),
    );
    mockUseDataCoverage.mockReturnValue(ok(coverage));
    render(<IncomePage />);
    expect(screen.getByText("No distributions in the trailing period")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("shows an empty message, not a blank table, when there is no income yet", () => {
    mockUseIncome.mockReturnValue(ok([]));
    mockUseIncomeGrowth.mockReturnValue(ok([]));
    mockUseIncomeYield.mockReturnValue(ok(yieldResponse));
    mockUseDataCoverage.mockReturnValue(ok(coverage));
    render(<IncomePage />);
    expect(screen.getByText("No income recorded yet.")).toBeInTheDocument();
  });

  it("shows a loading placeholder while pending", () => {
    mockUseIncome.mockReturnValue(pending());
    mockUseIncomeGrowth.mockReturnValue(pending());
    mockUseIncomeYield.mockReturnValue(pending());
    mockUseDataCoverage.mockReturnValue(pending());
    render(<IncomePage />);
    expect(screen.queryByText("+3.2%")).not.toBeInTheDocument();
  });

  it("uses a single h1", () => {
    setupDefaults();
    render(<IncomePage />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
