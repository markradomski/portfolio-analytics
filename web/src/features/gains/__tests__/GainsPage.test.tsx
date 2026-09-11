import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GainsPage } from "../GainsPage";
import type { DataCoverage, RealisedGainSummary, UnrealisedGainSnapshot } from "../../../api/types";

const mockUseRealisedGains = vi.fn();
const mockUseUnrealisedGains = vi.fn();
const mockUseDataCoverage = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  useRealisedGains: () => mockUseRealisedGains(),
  useUnrealisedGains: () => mockUseUnrealisedGains(),
  useDataCoverage: () => mockUseDataCoverage(),
}));

function ok<T>(data: T) {
  return { isPending: false, isError: false, data };
}
function pending() {
  return { isPending: true, isError: false, data: undefined };
}

const realised: RealisedGainSummary = {
  period_start: "2020-09-30", period_end: "2026-06-30",
  realised_gain: "1200.50", realised_loss: "-300.10", net_realised_gain: "900.40",
};

const unrealisedRows: UnrealisedGainSnapshot[] = [
  { security_id: "VAS", code: "VAS", asset_class: "Australian Shares", market_value: "10000",
    cost_basis: "9000", unrealised_gain: "1000", unrealised_gain_pct: "0.111" },
];

const coverage: DataCoverage = {
  valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
  transaction_start: "2020-09-30", transaction_end: "2026-06-30", price_observation_count: 24,
  missing_valuation_count: 0, actual_observation_count: 24, carried_forward_observation_count: 1920,
  estimated_observation_count: 0, unavailable_observation_count: 108,
};

function setupDefaults() {
  mockUseRealisedGains.mockReturnValue(ok(realised));
  mockUseUnrealisedGains.mockReturnValue(ok(unrealisedRows));
  mockUseDataCoverage.mockReturnValue(ok(coverage));
}

describe("GainsPage", () => {
  it("renders realised and unrealised gains separately from the API, never merged into one total", () => {
    setupDefaults();
    render(<GainsPage />);
    expect(screen.getByText("$900.40")).toBeInTheDocument();
    expect(screen.getByText("VAS")).toBeInTheDocument();
    expect(screen.getByText("+11.1%")).toBeInTheDocument();
  });

  it("shows an empty message when there are no current holdings for unrealised gains", () => {
    mockUseRealisedGains.mockReturnValue(ok(realised));
    mockUseUnrealisedGains.mockReturnValue(ok([]));
    mockUseDataCoverage.mockReturnValue(ok(coverage));
    render(<GainsPage />);
    expect(screen.getByText("No holdings to show unrealised gains for.")).toBeInTheDocument();
  });

  it("shows a loading placeholder while pending", () => {
    mockUseRealisedGains.mockReturnValue(pending());
    mockUseUnrealisedGains.mockReturnValue(pending());
    mockUseDataCoverage.mockReturnValue(pending());
    render(<GainsPage />);
    expect(screen.queryByText("$900.40")).not.toBeInTheDocument();
  });

  it("uses a single h1", () => {
    setupDefaults();
    render(<GainsPage />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
