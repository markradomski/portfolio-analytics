/**
 * HoldingsPage acceptance coverage (sec 27). Mocks the data hooks at the
 * module boundary -- QueryBoundary only needs the {isPending, isError,
 * data} shape react-query results carry, so a plain object stands in for a
 * real query without a QueryClientProvider.
 */
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { HoldingsPage } from "../HoldingsPage";
import type {
  AllocationHistoryPoint, AllocationResult, ConcentrationSnapshot, HoldingRow, PortfolioOverview,
  PortfolioState, UnrealisedGainSnapshot,
} from "../../../api/types";

const mockUseHoldingsData = vi.fn();
vi.mock("../useHoldingsData", () => ({ useHoldingsData: () => mockUseHoldingsData() }));

const mockUseHoldingHistory = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({ useHoldingHistory: () => mockUseHoldingHistory() }));

beforeAll(() => {
  // @ts-expect-error -- test-environment polyfill for ChartContainer
  global.ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
});

function ok<T>(data: T) {
  return { isPending: false, isError: false, data };
}
function pending() {
  return { isPending: true, isError: false, data: undefined };
}

function dailyPoint(holdings: HoldingRow[], overrides: Partial<PortfolioState> = {}): PortfolioState {
  return {
    date: "2026-06-30", total_value: "118.42", securities_value: "0", cash: "118.42", cost_basis: "0",
    invested_capital: "0", realised_gain: "0", unrealised_gain: "0", dividends: "0", distributions: "0",
    income: "0", fees: "0", cumulative_contributions: "98765.43", cumulative_withdrawals: "-123590.12",
    high_water_mark: "118.42", drawdown_value: null, drawdown_pct: null, return_index: "172.35",
    index_as_at: "2026-06-30", return_high_water: null, return_drawdown_pct: null, valuation_status: "actual",
    valuation_source: "VANGUARD", price_as_at: "2026-06-30", source_count: 1, calculation_method: "actual",
    holdings, ...overrides,
  };
}

const overview: PortfolioOverview = {
  as_at: "2026-06-30", current_value: "118.42", total_contributed: "98765.43",
  total_withdrawn: "-123590.12", net_contributed: "-15112.87", investment_growth: "15420.33",
  income_received: "6224.88",
  data_coverage: {
    valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
    transaction_start: "2020-09-30", transaction_end: "2026-06-30", price_observation_count: 24,
    missing_valuation_count: 0, actual_observation_count: 24, carried_forward_observation_count: 1920,
    estimated_observation_count: 0, unavailable_observation_count: 108,
  },
};

const unavailableAllocation: AllocationResult = {
  by: "asset_class", status: "unavailable", date: null, total: null, weights: null, allocation_pct: null,
  note: "no allocation computed for 2026-06-30",
};

const concentration: ConcentrationSnapshot = {
  date: "2026-06-30", largest_holding_pct: null, top_5_pct: null, top_10_pct: null, herfindahl_index: null,
  holding_count: 0,
};

const allocHistory: AllocationHistoryPoint[] = [
  { date: "2020-12-31", total: "21015.78", weights: { VAS: "5158.16", cash: "100" },
    allocation_pct: { VAS: "0.245", cash: "0.005" } },
];

const fullyDivestedData = {
  overview: ok(overview),
  capabilities: ok({}),
  holdings: ok(dailyPoint([])),
  unrealisedGains: ok<UnrealisedGainSnapshot[]>([]),
  concentration: ok(concentration),
  allocationBySecurity: ok(unavailableAllocation),
  allocationByAssetClass: ok({ ...unavailableAllocation, by: "asset_class" }),
  allocationHistory: ok(allocHistory),
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/holdings" element={<HoldingsPage />} />
        <Route path="/holdings/:code" element={<HoldingsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("HoldingsPage: fully-divested portfolio", () => {
  it("shows zero current holdings distinctly from an error, while historical allocation remains visible", () => {
    mockUseHoldingsData.mockReturnValue(fullyDivestedData);
    renderAt("/holdings");
    expect(screen.getByText(/fully divested to cash/)).toBeInTheDocument();
    // Historical allocation is NOT hidden just because current holdings are empty.
    expect(screen.getByText("Allocation over time")).toBeInTheDocument();
    expect(screen.getByText(/2020-12-31/)).toBeInTheDocument();
  });

  it("shows allocation as Unavailable, never as a fabricated 0%, when the API reports it unavailable", () => {
    mockUseHoldingsData.mockReturnValue(fullyDivestedData);
    renderAt("/holdings");
    expect(screen.getByText("no allocation computed for 2026-06-30")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("cash is shown as its own figure, not as a missing security", () => {
    mockUseHoldingsData.mockReturnValue(fullyDivestedData);
    renderAt("/holdings");
    const snapshot = screen.getByText("Portfolio snapshot").closest("section")!;
    expect(within(snapshot).getByText("Cash")).toBeInTheDocument();
    expect(within(snapshot).getAllByText("$118.42").length).toBe(2); // Total value and Cash are both $118.42 for a fully-divested cash-only portfolio
  });
});

describe("HoldingsPage: populated holdings", () => {
  const holding: HoldingRow = {
    date: "2024-09-30", security_id: "sec-1", code: "VAS", units: "100.5000", price: "90.00",
    market_value: "9045.00", cost_basis: "8000.00", unrealised_gain: "1045.00", allocation_pct: "0.9",
    asset_class: "australian_equities", valuation_status: "actual", price_as_at: "2024-09-30",
  };
  const gain: UnrealisedGainSnapshot = {
    security_id: "sec-1", code: "VAS", asset_class: "australian_equities", market_value: "9045.00",
    cost_basis: "8000.00", unrealised_gain: "1045.00", unrealised_gain_pct: "0.1306",
  };
  const populated = {
    ...fullyDivestedData,
    holdings: ok(dailyPoint([holding])),
    unrealisedGains: ok<UnrealisedGainSnapshot[]>([gain]),
    concentration: ok({ ...concentration, holding_count: 1 }),
  };

  it("renders the exact API-provided value, weight, gain and gain % -- never a recomputed weight", () => {
    mockUseHoldingsData.mockReturnValue(populated);
    renderAt("/holdings");
    const table = screen.getByRole("table");
    expect(within(table).getByText("VAS")).toBeInTheDocument();
    expect(within(table).getByText("$9,045.00")).toBeInTheDocument();
    expect(within(table).getByText("90.0%")).toBeInTheDocument(); // allocation_pct=0.9, verbatim
    expect(within(table).getByText("+$1,045.00")).toBeInTheDocument();
    expect(within(table).getByText("+13.1%")).toBeInTheDocument();
  });

  it("links a holding row to its security detail route", () => {
    mockUseHoldingsData.mockReturnValue(populated);
    renderAt("/holdings");
    expect(screen.getByRole("link", { name: "VAS" })).toHaveAttribute("href", "/holdings/VAS");
  });
});

describe("HoldingsPage: security detail", () => {
  it("shows a fully-divested security's history without treating the missing current holding as an error", () => {
    mockUseHoldingsData.mockReturnValue(fullyDivestedData);
    mockUseHoldingHistory.mockReturnValue(ok([
      { date: "2024-01-01", security_id: "sec-1", code: "VAS", units: "10", price: "90",
        market_value: "900", cost_basis: "800", unrealised_gain: "100", allocation_pct: "0.5",
        asset_class: "australian_equities", valuation_status: "actual", price_as_at: "2024-01-01" },
    ]));
    renderAt("/holdings/VAS");
    expect(screen.getByText("VAS")).toBeInTheDocument();
    expect(screen.getByText(/fully divested/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Value" })).toBeInTheDocument();
  });
});

describe("HoldingsPage: loading and accessibility", () => {
  it("shows a loading placeholder, not an empty snapshot, while pending", () => {
    mockUseHoldingsData.mockReturnValue({ ...fullyDivestedData, holdings: pending() });
    renderAt("/holdings");
    expect(screen.queryByText("$118.42")).not.toBeInTheDocument();
  });

  it("uses a single h1", () => {
    mockUseHoldingsData.mockReturnValue(fullyDivestedData);
    renderAt("/holdings");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
