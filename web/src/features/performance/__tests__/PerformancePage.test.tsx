/**
 * PerformancePage acceptance coverage (sec 33). Mocks the data hooks at the
 * module boundary -- QueryBoundary only needs the {isPending, isError,
 * data} shape react-query results carry, so a plain object stands in for a
 * real query without a QueryClientProvider.
 */
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { PerformancePage } from "../PerformancePage";
import type {
  AttributionReconciliationPair, AttributionTree, BestWorstPeriods, CalendarPerformanceRow,
  DrawdownAnalytics, PerformanceMethodology, PerformanceOverview, PerformancePeriod, PortfolioDailyPoint,
  PortfolioGrowthPoint, PortfolioOverview,
} from "../../../api/types";

const mockUsePerformanceData = vi.fn();
vi.mock("../usePerformanceData", () => ({ usePerformanceData: () => mockUsePerformanceData() }));

const mockUsePerformanceOverview = vi.fn();
const mockUseAttribution = vi.fn();
const mockUseAttributionReconciliation = vi.fn();
const mockUsePortfolioHistory = vi.fn();
const mockUsePortfolioGrowth = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  usePerformanceOverview: () => mockUsePerformanceOverview(),
  useAttribution: () => mockUseAttribution(),
  useAttributionReconciliation: () => mockUseAttributionReconciliation(),
  usePortfolioHistory: () => mockUsePortfolioHistory(),
  usePortfolioGrowth: () => mockUsePortfolioGrowth(),
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
  return { isPending: false, isError: true, data: undefined, error: new Error("network down") };
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

function period(overrides: Partial<PerformancePeriod>): PerformancePeriod {
  return {
    label: "1Y", as_at: "2026-06-30", start_date: "2025-06-30", end_date: "2026-06-30",
    total_return: "0.199", capital_return: "0.16", income_return: "0.057", twrr: "0.151",
    xirr: "0.004", status: "actual", note: null, ...overrides,
  };
}

const methodology: PerformanceMethodology = {
  return_methodology: {},
  twrr: {
    twrr_methodology: "SUBPERIOD_LINKED", twrr_methodology_note: "Chained sub-period returns.",
    cash_flow_adjustment_method: "EXACT_DATED", cash_flow_adjustment_note: "Flows dated exactly.",
    cash_flow_observation_quality: "SUFFICIENT", valuation_observation_count: 24,
  },
};

const attribution: AttributionTree = {
  period: { start: "2025-06-30", end: "2026-06-30" },
  external_cash_flows: "-3600",
  investment_return: {
    total: "10.98",
    capital_appreciation: { total: "-85.07", securities: {} },
    income: { dividends: "99.49", distributions: "0", interest: "0" },
  },
  cash: { interest_income: null, fees: null, profit: null, data_quality: "unavailable" },
  fees: "3.44", taxes: "0", other_adjustments: "0",
};

const reconciliation: AttributionReconciliationPair = {
  growth: { attributed_change: "10.98", actual_change: "10.98", residual: "0", tolerance: "0.05",
    reconciliation_status: "PASS", opening_value: null, closing_value: null, external_flows: null,
    note: null, difference: "0", status: "PASS" },
  attribution: { attributed_change: "10.98", actual_change: "10.98", residual: "0", tolerance: "0.05",
    reconciliation_status: "PASS", opening_value: null, closing_value: null, external_flows: null,
    note: null, difference: "0", status: "PASS" },
};

function dailyPoint(overrides: Partial<PortfolioDailyPoint>): PortfolioDailyPoint {
  return {
    date: "2026-06-30", total_value: "118.42", securities_value: "0", cash: "118.42", cost_basis: "0",
    invested_capital: "0", realised_gain: "0", unrealised_gain: null, dividends: "0", distributions: "0",
    income: "0", fees: "0", cumulative_contributions: "98765.43", cumulative_withdrawals: "-123590.12",
    high_water_mark: "118.42", drawdown_value: null, drawdown_pct: null, return_index: "153.21",
    index_as_at: "2026-06-30", return_high_water: null, return_drawdown_pct: null,
    valuation_status: "actual", valuation_source: "VANGUARD", price_as_at: "2026-06-30", source_count: 1,
    calculation_method: "actual", ...overrides,
  };
}

const calendarRows: CalendarPerformanceRow[] = [
  { period: "2025", twrr: "0.105", xirr: "0.061", income: "50", contributions: "0", withdrawals: "0",
    closing_value: "40000", valuation_status: "actual" },
  { period: "2026", twrr: "0.17", xirr: "0.06", income: "10", contributions: "0", withdrawals: "-3600",
    closing_value: "118.42", valuation_status: "actual" },
];

const bestWorst: BestWorstPeriods = {
  year: [
    { label: "best_year", period_start: "2021-01-01", period_end: "2021-12-31", return_pct: "0.174",
      absolute_change: null, opening_value: null, closing_value: null },
    { label: "worst_year", period_start: "2022-01-01", period_end: "2022-12-31", return_pct: "-0.094",
      absolute_change: null, opening_value: null, closing_value: null },
  ],
  day: "unavailable -- consecutive valuations are 91 days apart",
};

const drawdowns: DrawdownAnalytics = {
  maximum_drawdown_pct: "-0.144", maximum_drawdown_peak: "2021-12-31", maximum_drawdown_trough: "2022-09-30",
  average_drawdown_pct: "-0.11", episode_count: 2, longest_underwater_days: 730,
  longest_underwater_peak: "2021-12-31", fastest_recovery_days: 91,
};

const dollarOverview: PerformanceOverview = {
  period_start: "2025-06-30", period_end: "2026-06-30", opening_value: "9800", closing_value: "118.42",
  contributions: "0", withdrawals: "-3600", net_external_flow: "-3600", investment_gain: "348.64",
  income: "99.49", fees: "3.44", total_return: "0.199", capital_return: "0.16", income_return: "0.057",
  twrr: "0.151", xirr: "0.004", data_quality: "actual",
};

function growthPoint(overrides: Partial<PortfolioGrowthPoint>): PortfolioGrowthPoint {
  return {
    date: "2025-06-30", portfolio_value: "9800", contributions: "0", withdrawals: "0",
    net_contributions: "9451.36", investment_gain: "348.64", period_investment_gain: null,
    cash_flow_events: [], ...overrides,
  };
}

const growthSeries: PortfolioGrowthPoint[] = [
  growthPoint({ date: "2020-09-30", portfolio_value: "10000", net_contributions: "10000", investment_gain: "0" }),
  growthPoint({ date: "2023-06-30", portfolio_value: "45000", net_contributions: "40000", investment_gain: "5000" }),
  growthPoint({ date: "2025-06-30", portfolio_value: "9800", net_contributions: "9451.36", investment_gain: "348.64" }),
  growthPoint({ date: "2026-06-30", portfolio_value: "118.42", net_contributions: "-15112.87", investment_gain: "15420.33" }),
];

const staticData = {
  overview: ok(overview),
  capabilities: ok({}),
  periods: ok([period({})]),
  methodology: ok(methodology),
  calendar: ok(calendarRows),
  bestWorst: ok(bestWorst),
  drawdowns: ok(drawdowns),
};

function setupDefaults() {
  mockUsePerformanceData.mockReturnValue(staticData);
  mockUsePerformanceOverview.mockReturnValue(ok(dollarOverview));
  mockUseAttribution.mockReturnValue(ok(attribution));
  mockUseAttributionReconciliation.mockReturnValue(ok(reconciliation));
  mockUsePortfolioHistory.mockReturnValue(ok([dailyPoint({})]));
  mockUsePortfolioGrowth.mockReturnValue(ok(growthSeries));
}

function renderPage() {
  return render(<MemoryRouter><PerformancePage /></MemoryRouter>);
}

describe("PerformancePage: summary", () => {
  it("renders total return, total gain, capital return and income return from the API", () => {
    setupDefaults();
    renderPage();
    expect(screen.getByText("+19.9%")).toBeInTheDocument();
    expect(screen.getByText("+$348.64")).toBeInTheDocument();
    expect(screen.getByText("+16.0%")).toBeInTheDocument();
    expect(screen.getByText("+5.7%")).toBeInTheDocument();
  });

  it("shows an unavailable reason, not 0%, when the period has no return", () => {
    mockUsePerformanceData.mockReturnValue({
      ...staticData,
      periods: ok([period({ total_return: null, capital_return: null, income_return: null, twrr: null,
        xirr: null, status: "unavailable", note: "Only one real valuation" })]),
    });
    mockUsePerformanceOverview.mockReturnValue(ok({ ...dollarOverview, investment_gain: null }));
    mockUseAttribution.mockReturnValue(ok(attribution));
    mockUseAttributionReconciliation.mockReturnValue(ok(reconciliation));
    mockUsePortfolioHistory.mockReturnValue(ok([dailyPoint({})]));
  mockUsePortfolioGrowth.mockReturnValue(ok(growthSeries));
    renderPage();
    expect(screen.getAllByText("Only one real valuation").length).toBeGreaterThan(0);
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    expect(screen.queryByText("+0.0%")).not.toBeInTheDocument();
  });
});

describe("PerformancePage: period selector", () => {
  it("disables a period the backend marks unavailable, with its reason as the accessible tooltip", () => {
    setupDefaults();
    mockUsePerformanceData.mockReturnValue({
      ...staticData,
      periods: ok([
        period({}),
        period({ label: "1M", status: "unavailable", note: "nearest valuations span 91 days" }),
      ]),
    });
    renderPage();
    const tab1M = screen.getByRole("tab", { name: "1M" });
    expect(tab1M).toBeDisabled();
    expect(tab1M).toHaveAttribute("title", "nearest valuations span 91 days");
  });

  it("marks the default-selected period as selected", () => {
    setupDefaults();
    renderPage();
    expect(screen.getByRole("tab", { name: "1Y" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("PerformancePage: TWRR / XIRR", () => {
  it("shows TWRR with its methodology name, not a generic label", () => {
    setupDefaults();
    renderPage();
    expect(screen.getByText("+15.1%")).toBeInTheDocument();
    expect(screen.getByText("Sub-period linked")).toBeInTheDocument();
  });

  it("shows XIRR distinctly from TWRR", () => {
    setupDefaults();
    renderPage();
    expect(screen.getByText("+0.4%")).toBeInTheDocument();
  });

  it("shows XIRR as unavailable with a reason, never as 0%, when the backend has no XIRR", () => {
    mockUsePerformanceData.mockReturnValue({
      ...staticData,
      periods: ok([period({ xirr: null, note: null })]),
    });
    mockUsePerformanceOverview.mockReturnValue(ok(dollarOverview));
    mockUseAttribution.mockReturnValue(ok(attribution));
    mockUseAttributionReconciliation.mockReturnValue(ok(reconciliation));
    mockUsePortfolioHistory.mockReturnValue(ok([dailyPoint({})]));
  mockUsePortfolioGrowth.mockReturnValue(ok(growthSeries));
    renderPage();
    expect(screen.getByText("Not available for this period")).toBeInTheDocument();
  });
});

describe("PerformancePage: return decomposition", () => {
  it("renders capital growth, income sub-lines and external cash flows without summing them", () => {
    setupDefaults();
    renderPage();
    expect(screen.getByText("Capital growth")).toBeInTheDocument();
    expect(screen.getByText("Dividends")).toBeInTheDocument();
    expect(screen.getByText("External cash flows")).toBeInTheDocument();
    // Income is never a frontend-summed total of dividends+distributions+interest.
    expect(screen.queryByText(/^Income$/)).not.toBeInTheDocument();
  });

  it("shows the reconciliation status using Phase 4's own vocabulary on request", () => {
    setupDefaults();
    renderPage();
    expect(screen.getByText("Explained")).toBeInTheDocument();
  });

  it("discloses residual and tolerance on demand", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    setupDefaults();
    renderPage();
    await userEvent.click(screen.getByText("Performance reconciliation"));
    expect(screen.getByText("Residual")).toBeInTheDocument();
    expect(screen.getByText("Tolerance")).toBeInTheDocument();
  });
});

describe("PerformancePage: calendar", () => {
  it("renders each year's TWRR with positive/negative distinguishable", () => {
    setupDefaults();
    renderPage();
    const table = screen.getByRole("table");
    expect(within(table).getByText("2025")).toBeInTheDocument();
    expect(within(table).getByText("+10.5%")).toBeInTheDocument();
  });

  it("marks the current, still-running year as partial", () => {
    setupDefaults();
    renderPage();
    expect(screen.getByText("Year to date")).toBeInTheDocument();
  });
});

describe("PerformancePage: section inventory (Step 9A additive regression)", () => {
  it("keeps every pre-existing section AND adds the new Balance decomposition section", () => {
    setupDefaults();
    renderPage();
    // The advanced chart is ADDED; none of these existing sections is removed.
    for (const heading of [
      "Performance summary",
      "Performance history",
      "Balance decomposition", // <- new, Step 9A Part B
      "Return decomposition",
      "Methodology",
      "Calendar performance",
      "Best / worst periods",
      "Drawdown",
      "Data coverage",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    }
  });

  it("places the new Balance decomposition section between Performance history and Return decomposition", () => {
    setupDefaults();
    renderPage();
    const order = screen
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    const history = order.indexOf("Performance history");
    const bridge = order.indexOf("Balance decomposition");
    const returnDecomp = order.indexOf("Return decomposition");
    expect(history).toBeLessThan(bridge);
    expect(bridge).toBeLessThan(returnDecomp);
  });

  it("renders real decomposition content under the heading, not an empty card", () => {
    // Guards against the section silently degrading to just a heading:
    // the caption, the persistent legend and the Chart/Table toggle must
    // all be present for the normal real-data response shape.
    setupDefaults();
    renderPage();
    const section = screen.getByRole("heading", { name: "Balance decomposition" }).closest("section")!;
    expect(within(section).getByText(/A dollar decomposition, not a rate of return/)).toBeInTheDocument();
    expect(within(section).getByRole("tab", { name: "Chart" })).toBeInTheDocument();
    expect(within(section).getByRole("tab", { name: "Table" })).toBeInTheDocument();
    // The persistent legend names every series, gain and loss never merged.
    expect(within(section).getByText("Total Balance")).toBeInTheDocument();
    expect(within(section).getByText("Contributions & Withdrawals")).toBeInTheDocument();
    expect(within(section).getByText("Investment Gain")).toBeInTheDocument();
    expect(within(section).getByText("Investment Loss")).toBeInTheDocument();
    // The accessible summary always carries the real numbers even where a
    // 0-width ChartContainer would not paint an SVG.
    expect(
      within(section).getByText(/Total balance, net contributions and investment gain or loss/),
    ).toBeInTheDocument();
  });

  it("keeps the Balance decomposition section visible when a boundary valuation is unavailable (never returns null)", async () => {
    mockUsePerformanceData.mockReturnValue(staticData);
    mockUsePerformanceOverview.mockReturnValue(ok({ ...dollarOverview, opening_value: null }));
    mockUseAttribution.mockReturnValue(ok(attribution));
    mockUseAttributionReconciliation.mockReturnValue(ok(reconciliation));
    mockUsePortfolioHistory.mockReturnValue(ok([dailyPoint({})]));
    mockUsePortfolioGrowth.mockReturnValue(ok(growthSeries));
    const { default: userEvent } = await import("@testing-library/user-event");
    renderPage();
    const section = screen.getByRole("heading", { name: "Balance decomposition" }).closest("section")!;
    // The chart still renders (the growth series is intact); the missing
    // boundary valuation only blocks the Table's period bridge.
    expect(within(section).getByRole("tab", { name: "Chart" })).toBeInTheDocument();
    await userEvent.click(within(section).getByRole("tab", { name: "Table" }));
    expect(within(section).getByText(/no valuation on one of its boundary dates/)).toBeInTheDocument();
  });

  it("keeps the Balance decomposition section visible as a loading skeleton, then a recoverable error", () => {
    mockUsePerformanceData.mockReturnValue(staticData);
    mockUsePerformanceOverview.mockReturnValue(failed());
    mockUseAttribution.mockReturnValue(ok(attribution));
    mockUseAttributionReconciliation.mockReturnValue(ok(reconciliation));
    mockUsePortfolioHistory.mockReturnValue(ok([dailyPoint({})]));
  mockUsePortfolioGrowth.mockReturnValue(ok(growthSeries));
    renderPage();
    // Heading still present; the QueryBoundary error state renders inside.
    expect(screen.getByRole("heading", { name: "Balance decomposition" })).toBeInTheDocument();
    const section = screen.getByRole("heading", { name: "Balance decomposition" }).closest("section")!;
    expect(within(section).getByText(/Couldn't load this/)).toBeInTheDocument();
  });
});

describe("PerformancePage: fully-divested portfolio", () => {
  it("still renders historical performance when there are no current holdings involved at all", () => {
    // PerformancePage never requests holdings -- historical performance is
    // computed from the return series and attribution alone (sec 23).
    setupDefaults();
    renderPage();
    expect(screen.getByText("Performance")).toBeInTheDocument();
    expect(screen.getByText("+19.9%")).toBeInTheDocument();
  });
});

describe("PerformancePage: loading / error / independence of sections", () => {
  it("shows a loading placeholder, not an empty summary, while pending", () => {
    mockUsePerformanceData.mockReturnValue(staticData);
    mockUsePerformanceOverview.mockReturnValue(pending());
    mockUseAttribution.mockReturnValue(ok(attribution));
    mockUseAttributionReconciliation.mockReturnValue(ok(reconciliation));
    mockUsePortfolioHistory.mockReturnValue(ok([dailyPoint({})]));
  mockUsePortfolioGrowth.mockReturnValue(ok(growthSeries));
    renderPage();
    expect(screen.queryByText("+19.9%")).not.toBeInTheDocument();
  });

  it("a failed calendar request does not take down the summary section", () => {
    mockUsePerformanceData.mockReturnValue({ ...staticData, calendar: failed() });
    mockUsePerformanceOverview.mockReturnValue(ok(dollarOverview));
    mockUseAttribution.mockReturnValue(ok(attribution));
    mockUseAttributionReconciliation.mockReturnValue(ok(reconciliation));
    mockUsePortfolioHistory.mockReturnValue(ok([dailyPoint({})]));
  mockUsePortfolioGrowth.mockReturnValue(ok(growthSeries));
    renderPage();
    expect(screen.getByText("+19.9%")).toBeInTheDocument();
    expect(screen.getAllByText(/Couldn't load this/).length).toBeGreaterThan(0);
  });
});

describe("PerformancePage: accessibility", () => {
  it("uses a single h1 with a logical heading hierarchy under it", () => {
    setupDefaults();
    renderPage();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getAllByRole("heading", { level: 2 }).length).toBeGreaterThan(0);
  });
});
