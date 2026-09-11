import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { RiskPage } from "../RiskPage";
import type {
  BenchmarkComparison, DataCoverage, DrawdownAnalytics, HighWaterMarkStatus, Metric, RiskMetrics,
} from "../../../api/types";

const mockUseRiskMetrics = vi.fn();
const mockUseDrawdowns = vi.fn();
const mockUseHighWaterMark = vi.fn();
const mockUseRiskBenchmark = vi.fn();
const mockUseDataCoverage = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  useRiskMetrics: () => mockUseRiskMetrics(),
  useDrawdowns: () => mockUseDrawdowns(),
  useHighWaterMark: () => mockUseHighWaterMark(),
  useRiskBenchmark: () => mockUseRiskBenchmark(),
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
    name: "volatility", value: "0.12", methodology: "ANNUALISED_STD_DEV", data_quality: "actual",
    source: "computed", available: true, reason: null, ...overrides,
  };
}

const risk: RiskMetrics = {
  volatility: metric({ name: "volatility" }),
  sharpe_ratio: metric({ name: "sharpe_ratio", available: false, value: null, reason: "No risk-free rate configured" }),
  sortino_ratio: metric({ name: "sortino_ratio", available: false, value: null, reason: "No risk-free rate configured" }),
};

const drawdowns: DrawdownAnalytics = {
  maximum_drawdown_pct: "-0.144", maximum_drawdown_peak: "2021-12-31", maximum_drawdown_trough: "2022-09-30",
  average_drawdown_pct: "-0.11", episode_count: 2, longest_underwater_days: 730,
  longest_underwater_peak: "2021-12-31", fastest_recovery_days: 91,
};

const highWaterMark: HighWaterMarkStatus = {
  date: "2026-06-30", current_value: "118.42", high_water_mark: "40000",
  distance_from_high: "-39873.12", distance_from_high_pct: "-0.997", days_since_high: 1200,
};

const benchmarkUnavailable: BenchmarkComparison = {
  portfolio_return: null, benchmark_return: null, relative_return: null,
  portfolio_methodology: "TWRR", benchmark_methodology: null, methodology_mismatch: false,
  status: "unavailable", note: "No benchmark registered.", benchmark_id: null, benchmark_name: null,
};

const coverage: DataCoverage = {
  valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
  transaction_start: "2020-09-30", transaction_end: "2026-06-30", price_observation_count: 24,
  missing_valuation_count: 0, actual_observation_count: 24, carried_forward_observation_count: 1920,
  estimated_observation_count: 0, unavailable_observation_count: 108,
};

function setupDefaults() {
  mockUseRiskMetrics.mockReturnValue(ok(risk));
  mockUseDrawdowns.mockReturnValue(ok(drawdowns));
  mockUseHighWaterMark.mockReturnValue(ok(highWaterMark));
  mockUseRiskBenchmark.mockReturnValue(ok(benchmarkUnavailable));
  mockUseDataCoverage.mockReturnValue(ok(coverage));
}

describe("RiskPage", () => {
  it("renders volatility and drawdown metrics from the API", () => {
    setupDefaults();
    render(<MemoryRouter><RiskPage /></MemoryRouter>);
    expect(screen.getByText("+12.0%")).toBeInTheDocument();
    expect(screen.getByText("-14.4%")).toBeInTheDocument();
  });

  it("shows Sharpe/Sortino as unavailable with the backend's reason, never as 0, when no risk-free rate is configured", () => {
    setupDefaults();
    render(<MemoryRouter><RiskPage /></MemoryRouter>);
    expect(screen.getAllByText("No risk-free rate configured").length).toBeGreaterThanOrEqual(2);
  });

  it("shows benchmark comparison as unavailable with a reason, never as 0%, when no benchmark is registered", () => {
    setupDefaults();
    render(<MemoryRouter><RiskPage /></MemoryRouter>);
    expect(screen.getByText("No benchmark registered.")).toBeInTheDocument();
  });

  it("renders a real benchmark comparison when one is available", () => {
    mockUseRiskMetrics.mockReturnValue(ok(risk));
    mockUseDrawdowns.mockReturnValue(ok(drawdowns));
    mockUseHighWaterMark.mockReturnValue(ok(highWaterMark));
    mockUseRiskBenchmark.mockReturnValue(
      ok({
        ...benchmarkUnavailable, portfolio_return: "0.10", benchmark_return: "0.08", relative_return: "0.02",
        status: "actual", benchmark_name: "ASX 300",
      }),
    );
    mockUseDataCoverage.mockReturnValue(ok(coverage));
    render(<MemoryRouter><RiskPage /></MemoryRouter>);
    expect(screen.getByText("+2.0%")).toBeInTheDocument();
  });

  it("shows a loading placeholder while pending", () => {
    mockUseRiskMetrics.mockReturnValue(pending());
    mockUseDrawdowns.mockReturnValue(pending());
    mockUseHighWaterMark.mockReturnValue(pending());
    mockUseRiskBenchmark.mockReturnValue(pending());
    mockUseDataCoverage.mockReturnValue(pending());
    render(<MemoryRouter><RiskPage /></MemoryRouter>);
    expect(screen.queryByText("+12.0%")).not.toBeInTheDocument();
  });

  it("uses a single h1", () => {
    setupDefaults();
    render(<MemoryRouter><RiskPage /></MemoryRouter>);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
