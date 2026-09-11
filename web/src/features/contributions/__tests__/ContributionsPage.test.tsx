import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ContributionsPage } from "../ContributionsPage";
import type { ContributionHistoryRow, ContributionSummary, DataCoverage } from "../../../api/types";

const mockUseContributionsSummary = vi.fn();
const mockUseContributionsHistory = vi.fn();
const mockUseDataCoverage = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  useContributionsSummary: () => mockUseContributionsSummary(),
  useContributionsHistory: () => mockUseContributionsHistory(),
  useDataCoverage: () => mockUseDataCoverage(),
}));

function ok<T>(data: T) {
  return { isPending: false, isError: false, data };
}
function pending() {
  return { isPending: true, isError: false, data: undefined };
}

const summary: ContributionSummary = {
  total_contributed: "98765.43", total_withdrawn: "-123590.12", net_contributed: "-15112.87",
  investment_growth: "15420.33", income_received: "6224.88", current_value: "118.42", as_at: "2026-06-30",
};

const historyRows: ContributionHistoryRow[] = [
  { period_end: "2025-06-30", contributions: "5000", withdrawals: "-2000", net_contributions: "3000",
    cumulative_contributions: "98765.43", cumulative_withdrawals: "-123590.12", cumulative_net: "-15112.87" },
];

const coverage: DataCoverage = {
  valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
  transaction_start: "2020-09-30", transaction_end: "2026-06-30", price_observation_count: 24,
  missing_valuation_count: 0, actual_observation_count: 24, carried_forward_observation_count: 1920,
  estimated_observation_count: 0, unavailable_observation_count: 108,
};

function setupDefaults() {
  mockUseContributionsSummary.mockReturnValue(ok(summary));
  mockUseContributionsHistory.mockReturnValue(ok(historyRows));
  mockUseDataCoverage.mockReturnValue(ok(coverage));
}

describe("ContributionsPage", () => {
  it("renders contribution totals and history rows from the API", () => {
    setupDefaults();
    render(<ContributionsPage />);
    expect(screen.getAllByText("-$15,112.87").length).toBeGreaterThan(0);
    expect(screen.getByText("2025")).toBeInTheDocument();
  });

  it("shows an unavailable reason, not a fabricated figure, when investment growth is not available", () => {
    mockUseContributionsSummary.mockReturnValue(ok({ ...summary, investment_growth: null }));
    mockUseContributionsHistory.mockReturnValue(ok(historyRows));
    mockUseDataCoverage.mockReturnValue(ok(coverage));
    render(<ContributionsPage />);
    expect(screen.getByText("Not available")).toBeInTheDocument();
  });

  it("shows an empty message when there is no contribution history yet", () => {
    mockUseContributionsSummary.mockReturnValue(ok(summary));
    mockUseContributionsHistory.mockReturnValue(ok([]));
    mockUseDataCoverage.mockReturnValue(ok(coverage));
    render(<ContributionsPage />);
    expect(screen.getByText("No contribution history recorded yet.")).toBeInTheDocument();
  });

  it("shows a loading placeholder while pending", () => {
    mockUseContributionsSummary.mockReturnValue(pending());
    mockUseContributionsHistory.mockReturnValue(pending());
    mockUseDataCoverage.mockReturnValue(pending());
    render(<ContributionsPage />);
    expect(screen.queryByText("-$15,112.87")).not.toBeInTheDocument();
  });

  it("uses a single h1", () => {
    setupDefaults();
    render(<ContributionsPage />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
