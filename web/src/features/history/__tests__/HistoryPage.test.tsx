import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { HistoryPage } from "../HistoryPage";
import type { ActivityRow, DataCoverage } from "../../../api/types";

const mockUseActivity = vi.fn();
const mockUseDataCoverage = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  useActivity: () => mockUseActivity(),
  useDataCoverage: () => mockUseDataCoverage(),
}));

function ok<T>(data: T) {
  return { isPending: false, isError: false, data };
}
function pending() {
  return { isPending: true, isError: false, data: undefined };
}

const rows: ActivityRow[] = [
  { transaction_id: "t1", trade_date: "2025-06-30", type: "BUY", code: "VAS", units: "10.5", price: "95.20",
    net_amount: "-999.60", description: "Buy VAS" },
];

const coverage: DataCoverage = {
  valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
  transaction_start: "2020-09-30", transaction_end: "2026-06-30", price_observation_count: 24,
  missing_valuation_count: 0, actual_observation_count: 24, carried_forward_observation_count: 1920,
  estimated_observation_count: 0, unavailable_observation_count: 108,
};

function setupDefaults() {
  mockUseActivity.mockReturnValue(ok(rows));
  mockUseDataCoverage.mockReturnValue(ok(coverage));
}

describe("HistoryPage", () => {
  it("renders the transaction ledger from the API", () => {
    setupDefaults();
    render(<HistoryPage />);
    expect(screen.getByText("VAS")).toBeInTheDocument();
    expect(screen.getByText("Buy VAS")).toBeInTheDocument();
    expect(screen.getByText("-$999.60")).toBeInTheDocument();
  });

  it("shows an empty message, not a blank table, when there are no transactions yet", () => {
    mockUseActivity.mockReturnValue(ok([]));
    mockUseDataCoverage.mockReturnValue(ok(coverage));
    render(<HistoryPage />);
    expect(screen.getByText("No transactions recorded yet.")).toBeInTheDocument();
  });

  it("shows a loading placeholder while pending", () => {
    mockUseActivity.mockReturnValue(pending());
    mockUseDataCoverage.mockReturnValue(pending());
    render(<HistoryPage />);
    expect(screen.queryByText("VAS")).not.toBeInTheDocument();
  });

  it("uses a single h1", () => {
    setupDefaults();
    render(<HistoryPage />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
