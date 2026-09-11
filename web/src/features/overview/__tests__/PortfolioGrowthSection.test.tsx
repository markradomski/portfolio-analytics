/**
 * The period selector (1Y/3Y/5Y/All) plus summary row wrapping
 * PortfolioGrowthChart. Mocks the API hooks at the module boundary, same
 * convention as every other screen's tests.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { PortfolioGrowthSection } from "../PortfolioGrowthSection";
import type { PortfolioGrowthPoint, PortfolioGrowthSummary } from "../../../api/types";

const mockUsePortfolioGrowth = vi.fn();
const mockUsePortfolioGrowthSummary = vi.fn();
vi.mock("../../../hooks/api/usePortfolioApi", () => ({
  usePortfolioGrowth: () => mockUsePortfolioGrowth(),
  usePortfolioGrowthSummary: () => mockUsePortfolioGrowthSummary(),
}));

beforeAll(() => {
  // @ts-expect-error -- test-environment polyfill for ChartContainer
  global.ResizeObserver = class {
    observe() { }
    disconnect() { }
  };
});

function ok<T>(data: T) {
  return { isPending: false, isError: false, data };
}

function point(dateStr: string, value: string): PortfolioGrowthPoint {
  return {
    date: dateStr, portfolio_value: value, contributions: "0", withdrawals: "0",
    net_contributions: "1000", investment_gain: "0", cash_flow_events: [],
  };
}

// Spans 6 years so 1Y/3Y/5Y/All each produce a genuinely different slice.
const longSeries: PortfolioGrowthPoint[] = [
  point("2019-01-01", "500"),
  point("2021-01-01", "800"),
  point("2023-01-01", "1500"),
  point("2025-01-01", "2500"),
  point("2025-06-30", "3000"),
];

const summary: PortfolioGrowthSummary = {
  current_value: "3000", net_contributions: "2000", investment_gain: "1000",
  growth_pct: "0.5", as_at: "2025-06-30",
};

function setup() {
  mockUsePortfolioGrowth.mockReturnValue(ok(longSeries));
  mockUsePortfolioGrowthSummary.mockReturnValue(ok(summary));
}

function renderSection(props?: {
  rateOfReturn?: string | null; contributed?: string | null; withdrawn?: string | null;
}) {
  return render(<MemoryRouter><PortfolioGrowthSection {...props} /></MemoryRouter>);
}

describe("PortfolioGrowthSection: summary", () => {
  it("renders net contributions, investment gain/loss and total balance from the API, reinforcing the chart's own decomposition", () => {
    setup();
    renderSection();
    expect(screen.getByText("Net contributions")).toBeInTheDocument();
    expect(screen.getByText("$2,000.00")).toBeInTheDocument();
    expect(screen.getByText("Investment gain")).toBeInTheDocument();
    expect(screen.getByText("+$1,000.00")).toBeInTheDocument();
    expect(screen.getByText("Total balance")).toBeInTheDocument();
    expect(screen.getByText("$3,000.00")).toBeInTheDocument();
  });

  it("prefers plain 'Contributed' / 'Withdrawn' metrics when the authoritative lifetime totals are available", () => {
    setup();
    renderSection({ contributed: "98765.43", withdrawn: "-123590.12" });
    expect(screen.getByText("Contributed")).toBeInTheDocument();
    expect(screen.getByText("$98,765.43")).toBeInTheDocument();
    expect(screen.getByText("Withdrawn")).toBeInTheDocument();
    // Shown as a plain positive amount, not the signed-negative stored value.
    expect(screen.getByText("$123,590.12")).toBeInTheDocument();
    expect(screen.queryByText("Net contributions")).not.toBeInTheDocument();
  });

  it("falls back to the single 'Net contributions' figure when lifetime totals are not supplied", () => {
    setup();
    renderSection();
    expect(screen.getByText("Net contributions")).toBeInTheDocument();
    expect(screen.queryByText("Withdrawn")).not.toBeInTheDocument();
  });

  it("shows Rate of return as a separate metric when the authoritative inception return is available", () => {
    setup();
    renderSection({ rateOfReturn: "0.615" });
    expect(screen.getByText("Rate of return")).toBeInTheDocument();
    expect(screen.getByText("+61.5%")).toBeInTheDocument();
    expect(screen.getByText(/time-weighted, since inception/)).toBeInTheDocument();
  });

  it("shows Rate of return as unavailable (never 0%) when there is not enough valuation history", () => {
    setup();
    renderSection({ rateOfReturn: null });
    expect(screen.getByText(/Not enough valuation history/)).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("shows no explanatory paragraph beneath the chart -- the legend and labels carry the meaning (Step 9A.2)", () => {
    setup();
    renderSection();
    expect(screen.queryByText(/blue area shows the total amount you've invested/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Green shows investment gains above that amount/)).not.toBeInTheDocument();
  });

  it("labels the residual metric 'Investment loss' (not a negative gain) when the authoritative figure is negative", () => {
    mockUsePortfolioGrowth.mockReturnValue(ok(longSeries));
    mockUsePortfolioGrowthSummary.mockReturnValue(ok({ ...summary, investment_gain: "-1500" }));
    renderSection();
    expect(screen.getByText("Investment loss")).toBeInTheDocument();
    expect(screen.queryByText("Investment gain")).not.toBeInTheDocument();
  });
});

describe("PortfolioGrowthSection: period selector", () => {
  it("defaults to MAX, selected in the tab list -- the long-term growth story is the point of this chart", () => {
    setup();
    renderSection();
    expect(screen.getByRole("tab", { name: "MAX" })).toHaveAttribute("aria-selected", "true");
  });

  it("offers all 8 periods, 1M through MAX, with no ALL option", () => {
    setup();
    renderSection();
    for (const label of ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "MAX"]) {
      expect(screen.getByRole("tab", { name: label })).toBeInTheDocument();
    }
    expect(screen.queryByRole("tab", { name: "All" })).not.toBeInTheDocument();
  });

  it("selecting a different period updates which tab is marked selected", async () => {
    setup();
    renderSection();
    await userEvent.click(screen.getByRole("tab", { name: "1Y" }));
    expect(screen.getByRole("tab", { name: "1Y" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "MAX" })).toHaveAttribute("aria-selected", "false");
  });
});

describe("PortfolioGrowthSection: empty / loading", () => {
  it("shows an empty message, not a blank chart, when there is no growth history yet", () => {
    mockUsePortfolioGrowth.mockReturnValue(ok([]));
    mockUsePortfolioGrowthSummary.mockReturnValue(ok(summary));
    renderSection();
    expect(screen.getByText("No portfolio history available yet.")).toBeInTheDocument();
  });
});

describe("PortfolioGrowthSection: legend", () => {
  it("always renders all four legend labels, regardless of loading state -- Gain and Loss as two separate entries", () => {
    mockUsePortfolioGrowth.mockReturnValue(ok([]));
    mockUsePortfolioGrowthSummary.mockReturnValue(ok(summary));
    renderSection();
    expect(screen.getByText("Total Balance")).toBeInTheDocument();
    expect(screen.getByText("Contributions")).toBeInTheDocument();
    expect(screen.getByText("Investment Gain")).toBeInTheDocument();
    expect(screen.getByText("Investment Loss")).toBeInTheDocument();
    expect(screen.queryByText("Investment Gain/Loss")).not.toBeInTheDocument();
  });

  it("keeps the legend present across every period selection", async () => {
    setup();
    renderSection();
    await userEvent.click(screen.getByRole("tab", { name: "1Y" }));
    expect(screen.getByText("Total Balance")).toBeInTheDocument();
    expect(screen.getByText("Investment Gain")).toBeInTheDocument();
    expect(screen.getByText("Investment Loss")).toBeInTheDocument();
    expect(screen.getByText("Contributions")).toBeInTheDocument();
  });
});
