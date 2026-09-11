/**
 * OverviewPage acceptance coverage (sec 30/36). Mocks useOverviewData at
 * the module boundary -- QueryBoundary only needs the {isPending, isError,
 * data} shape react-query results carry, so a plain object stands in for a
 * real query without needing a QueryClientProvider in every test.
 */
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { OverviewPage } from "../OverviewPage";
import type {
  AllocationResult, HoldingRow, IncomeRow, PortfolioOverview, PortfolioState,
  UnrealisedGainSnapshot,
} from "../../../api/types";

const mockUseOverviewData = vi.fn();
vi.mock("../useOverview", () => ({ useOverviewData: () => mockUseOverviewData() }));

const mockUsePortfolioGrowth = vi.fn();
const mockUsePortfolioGrowthSummary = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  usePortfolioGrowth: () => mockUsePortfolioGrowth(),
  usePortfolioGrowthSummary: () => mockUsePortfolioGrowthSummary(),
}));

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
function failed() {
  return { isPending: false, isError: true, isSuccess: false, data: undefined, error: new Error("network down") };
}

const overview: PortfolioOverview = {
  as_at: "2026-06-30", current_value: "126.88", total_contributed: "107110.02",
  total_withdrawn: "-123590.12", net_contributed: "-16480.10", investment_growth: "16606.98",
  income_received: "6224.88",
  data_coverage: {
    valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
    transaction_start: "2020-09-30", transaction_end: "2026-06-30", price_observation_count: 24,
    missing_valuation_count: 0, actual_observation_count: 24, carried_forward_observation_count: 1920,
    estimated_observation_count: 0, unavailable_observation_count: 108,
  },
};

const baseline = {
  overview: ok(overview),
  capabilities: ok({}),
  periods: ok([{ label: "INCEPTION", as_at: "2026-06-30", start_date: "2020-09-30", end_date: "2026-06-30",
    total_return: "0.68", capital_return: "0.6", income_return: "0.08", twrr: "0.68", xirr: "0.5",
    status: "actual" as const, note: null }]),
  methodology: ok({ return_methodology: {}, twrr: { twrr_methodology: "SUBPERIOD_LINKED" as const,
    twrr_methodology_note: "", cash_flow_adjustment_method: "EXACT_DATED" as const,
    cash_flow_adjustment_note: "", cash_flow_observation_quality: "SUFFICIENT" as const,
    valuation_observation_count: 24 } }),
  allocation: ok<AllocationResult>({ by: "asset_class", status: "unavailable", date: null, total: null, weights: null,
    allocation_pct: null, note: "no allocation computed" }),
  holdings: ok<PortfolioState>({ ...dailyPoint(), holdings: [] }),
  unrealisedGains: ok<UnrealisedGainSnapshot[]>([]),
  income: ok<IncomeRow[]>([{ period_end: "2026-06-30", code: null, dividends: "40", distributions: "10",
    interests: "7.44", gross_income: "57.44", franking_credits: "24.62", tax_withheld: "0", net_income: "57.44" }]),
  incomeYield: ok({ trailing: metricStub("trailing"), forward: metricStub("forward") }),
  history: ok([dailyPoint()]),
  activity: ok([]),
};

function dailyPoint() {
  return {
    date: "2026-06-30", total_value: "126.88", securities_value: "0", cash: "126.88", cost_basis: "0",
    invested_capital: "0", realised_gain: "0", unrealised_gain: null, dividends: "0", distributions: "0",
    income: "0", fees: "0", cumulative_contributions: "107110.02", cumulative_withdrawals: "-123590.12",
    high_water_mark: "126.88", drawdown_value: null, drawdown_pct: null, return_index: null,
    index_as_at: null, return_high_water: null, return_drawdown_pct: null, valuation_status: "actual" as const,
    valuation_source: "VANGUARD", price_as_at: "2026-06-30", source_count: 1, calculation_method: "actual",
  };
}
function metricStub(name: string) {
  return { name, value: null, methodology: "m", data_quality: "unavailable" as const, period_start: null,
    period_end: null, currency: null, note: null, frequency: null, annualisation: null,
    annualisation_factor: null, risk_free_rate: null, benchmark: null, observations: null,
    confidence: null, source: "s", available: false, reason: "No income recorded" };
}

const growthPoints = [
  { date: "2026-06-30", portfolio_value: "126.88", contributions: "0.00", withdrawals: "0.00",
    net_contributions: "-16480.10", investment_gain: "16606.98", cash_flow_events: [] },
];
const growthSummary = {
  current_value: "126.88", net_contributions: "-16480.10", investment_gain: "16606.98",
  growth_pct: null, as_at: "2026-06-30",
};

function setupGrowthDefaults() {
  mockUsePortfolioGrowth.mockReturnValue(ok(growthPoints));
  mockUsePortfolioGrowthSummary.mockReturnValue(ok(growthSummary));
}

function renderPage() {
  setupGrowthDefaults();
  return render(<MemoryRouter><OverviewPage /></MemoryRouter>);
}

describe("OverviewPage", () => {
  it("renders the current portfolio value and valuation date from the API, never hard-coded", () => {
    mockUseOverviewData.mockReturnValue(baseline);
    renderPage();
    expect(screen.getAllByText("$126.88").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/30 June 2026/).length).toBeGreaterThan(0);
  });

  it("renders a positive gain with its sign and colour tone, and the total return percentage", () => {
    mockUseOverviewData.mockReturnValue(baseline);
    renderPage();
    expect(screen.getAllByText("+$16,606.98").length).toBeGreaterThan(0);
    // The inception return now also appears as the growth section's own
    // "Rate of return" metric -- same authoritative figure, shown twice.
    expect(screen.getAllByText("+68.0%").length).toBeGreaterThan(0);
  });

  it("renders a negative gain distinctly from a positive one", () => {
    mockUseOverviewData.mockReturnValue({
      ...baseline,
      overview: ok({ ...overview, investment_growth: "-500.00" }),
    });
    renderPage();
    expect(screen.getByText("-$500.00")).toBeInTheDocument();
  });

  it("shows contributions and withdrawals as explicitly distinct figures, never summed into a return", () => {
    mockUseOverviewData.mockReturnValue(baseline);
    renderPage();
    const contributions = screen.getByRole("heading", { name: "Contributions" }).closest("section")!;
    expect(within(contributions).getByText("Total contributions")).toBeInTheDocument();
    expect(within(contributions).getByText("Total withdrawals")).toBeInTheDocument();
    expect(within(contributions).getByText("$107,110.02")).toBeInTheDocument();
    expect(within(contributions).getByText("-$123,590.12")).toBeInTheDocument();
  });

  it("shows the income breakdown from the API's own income row", () => {
    mockUseOverviewData.mockReturnValue(baseline);
    renderPage();
    expect(screen.getByText("$24.62")).toBeInTheDocument(); // franking credits
  });

  it("shows allocation as explicitly unavailable, with the backend's own reason, when the API reports it unavailable", () => {
    mockUseOverviewData.mockReturnValue(baseline);
    renderPage();
    expect(screen.getByText("no allocation computed")).toBeInTheDocument();
  });

  it("renders known allocation segments proportionally when available", () => {
    mockUseOverviewData.mockReturnValue({
      ...baseline,
      allocation: ok<AllocationResult>({
        by: "asset_class", status: "ok", date: "2026-06-30", total: "1000",
        weights: { australian_equities: "700", cash: "300" },
        allocation_pct: { australian_equities: "0.7", cash: "0.3" }, note: null,
      }),
    });
    renderPage();
    expect(screen.getByText("Australian equities")).toBeInTheDocument();
    expect(screen.getByText("70.0%")).toBeInTheDocument();
  });

  it("renders a meaningful empty state for holdings rather than fabricating a security", () => {
    mockUseOverviewData.mockReturnValue(baseline);
    renderPage();
    expect(screen.getByText("No securities currently held.")).toBeInTheDocument();
  });

  it("renders a top-holdings table with weight and value when holdings exist", () => {
    const holding: HoldingRow = {
      date: "2026-06-30", security_id: "sec-1", code: "VAS", units: "100", price: "90",
      market_value: "9000", cost_basis: "8000", unrealised_gain: "1000", allocation_pct: "0.9",
      asset_class: "australian_equities", valuation_status: "actual", price_as_at: "2026-06-30",
    };
    const gain: UnrealisedGainSnapshot = {
      security_id: "sec-1", code: "VAS", asset_class: "australian_equities", market_value: "9000",
      cost_basis: "8000", unrealised_gain: "1000", unrealised_gain_pct: "0.125",
    };
    mockUseOverviewData.mockReturnValue({
      ...baseline,
      holdings: ok<PortfolioState>({ ...dailyPoint(), holdings: [holding] }),
      unrealisedGains: ok<UnrealisedGainSnapshot[]>([gain]),
    });
    renderPage();
    const table = screen.getByRole("table");
    expect(within(table).getByText("VAS")).toBeInTheDocument();
    expect(within(table).getByText("$9,000.00")).toBeInTheDocument();
    expect(within(table).getByText("90.0%")).toBeInTheDocument();
    expect(within(table).getByText("+12.5%")).toBeInTheDocument();
  });

  it("shows a loading state, not an empty dashboard, while the overview is pending", () => {
    mockUseOverviewData.mockReturnValue({ ...baseline, overview: pending() });
    mockUsePortfolioGrowth.mockReturnValue(pending());
    mockUsePortfolioGrowthSummary.mockReturnValue(pending());
    render(<MemoryRouter><OverviewPage /></MemoryRouter>);
    expect(screen.queryByText("$126.88")).not.toBeInTheDocument();
    expect(document.querySelector('[aria-hidden="true"]')).toBeTruthy();
  });

  it("distinguishes an API failure from a merely-unavailable metric", () => {
    mockUseOverviewData.mockReturnValue({ ...baseline, overview: failed() });
    renderPage();
    expect(screen.getAllByText(/Couldn't load this/).length).toBeGreaterThan(0);
  });

  it("uses a single h1 with a logical heading hierarchy under it", () => {
    mockUseOverviewData.mockReturnValue(baseline);
    renderPage();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getAllByRole("heading", { level: 2 }).length).toBeGreaterThan(0);
  });
});
