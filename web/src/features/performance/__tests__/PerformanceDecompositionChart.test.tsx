/**
 * The advanced Performance balance-decomposition section (Step 9A Part B).
 * The chart itself is the detailed BalanceDecompositionChart primitive
 * (tested directly in its own suite, since it lives inside a ChartContainer
 * whose ResizeObserver never fires in jsdom); this suite covers the feature
 * wrapper -- the legend, the caption, the Chart/Table toggle, the period
 * slice reaching the chart, and the data-state fallbacks that keep the
 * section visible (Step 9A.1). No figure shown here is built from
 * arithmetic on two API fields.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import { PerformanceDecompositionChart } from "../PerformanceDecompositionChart";
import type { PerformanceOverview, PortfolioGrowthPoint } from "../../../api/types";

beforeAll(() => {
  // @ts-expect-error -- ResizeObserver polyfill for ChartContainer
  global.ResizeObserver = class { observe() {} disconnect() {} };
});

const overview: PerformanceOverview = {
  period_start: "2025-06-30", period_end: "2026-06-30", opening_value: "10000", closing_value: "12500",
  contributions: "3000", withdrawals: "-1000", net_external_flow: "2000", investment_gain: "500",
  income: "120", fees: "20", total_return: "0.04", capital_return: "0.03", income_return: "0.01",
  twrr: "0.038", xirr: "0.041", data_quality: "actual",
};

function point(overrides: Partial<PortfolioGrowthPoint>): PortfolioGrowthPoint {
  return {
    date: "2025-01-01", portfolio_value: "1000", contributions: "0", withdrawals: "0",
    net_contributions: "1000", investment_gain: "0", period_investment_gain: null,
    cash_flow_events: [], ...overrides,
  };
}

const points: PortfolioGrowthPoint[] = [
  point({ date: "2024-01-01", portfolio_value: "5000", net_contributions: "5000", investment_gain: "0" }),
  point({ date: "2025-01-01", portfolio_value: "9000", net_contributions: "8000", investment_gain: "1000" }),
  point({ date: "2025-07-01", portfolio_value: "11000", net_contributions: "9500", investment_gain: "1500" }),
  point({ date: "2026-01-01", portfolio_value: "12500", net_contributions: "10000", investment_gain: "2500" }),
];

const base = {
  points, overview, windowStart: undefined as string | undefined,
  windowEnd: undefined as string | undefined, periodLabel: "1Y",
};

describe("PerformanceDecompositionChart", () => {
  it("renders the persistent four-item legend, gain and loss never merged", () => {
    render(<PerformanceDecompositionChart {...base} />);
    expect(screen.getByText("Total Balance")).toBeInTheDocument();
    expect(screen.getByText("Contributions & Withdrawals")).toBeInTheDocument();
    expect(screen.getByText("Investment Gain")).toBeInTheDocument();
    expect(screen.getByText("Investment Loss")).toBeInTheDocument();
    expect(screen.queryByText("Investment Gain/Loss")).not.toBeInTheDocument();
  });

  it("frames the section as a dollar decomposition, explicitly not a rate of return", () => {
    render(<PerformanceDecompositionChart {...base} />);
    expect(screen.getByText(/A dollar decomposition, not a rate of return/)).toBeInTheDocument();
  });

  it("slices the growth series to the selected window before it reaches the chart", () => {
    render(
      <PerformanceDecompositionChart {...base} windowStart="2025-01-01" windowEnd="2025-12-31" periodLabel="1Y" />,
    );
    // ChartContainer always renders its accessible summary, even where a
    // 0-width jsdom container never paints an SVG -- 2 of the 4 fixture
    // points fall inside 2025.
    expect(screen.getByText(/2 data points/)).toBeInTheDocument();
  });

  it("switches to a table of the authoritative period bridge, verbatim", async () => {
    render(<PerformanceDecompositionChart {...base} />);
    await userEvent.click(screen.getByRole("tab", { name: "Table" }));
    expect(screen.getByText("Beginning balance")).toBeInTheDocument();
    expect(screen.getByText("Net external flow")).toBeInTheDocument();
    expect(screen.getByText("+$2,000.00")).toBeInTheDocument();  // net_external_flow, verbatim
    expect(screen.getByText("$12,500.00")).toBeInTheDocument();  // closing_value, verbatim
  });

  it("never invents a market-gain-loss dollar split -- table shows total investment return and income only", async () => {
    render(<PerformanceDecompositionChart {...base} />);
    await userEvent.click(screen.getByRole("tab", { name: "Table" }));
    expect(screen.getByText("Investment return")).toBeInTheDocument();
    expect(screen.getByText("Income (within investment return)")).toBeInTheDocument();
    expect(screen.queryByText(/Market gain\/loss/i)).not.toBeInTheDocument();
  });

  it("keeps the Chart view visible with an explicit message when the period has no valued history", () => {
    const gap = points.map((p) => ({ ...p, portfolio_value: null }));
    render(<PerformanceDecompositionChart {...base} points={gap} />);
    expect(screen.getByText(/No valued portfolio history in this period/)).toBeInTheDocument();
  });

  it("keeps the Table view visible with an explicit message when a boundary valuation is missing", async () => {
    render(<PerformanceDecompositionChart {...base} overview={{ ...overview, opening_value: null }} />);
    await userEvent.click(screen.getByRole("tab", { name: "Table" }));
    expect(screen.getByText(/no valuation on one of its boundary dates/)).toBeInTheDocument();
  });

  it("still decomposes a fully-divested portfolio (tiny closing balance, large withdrawal)", async () => {
    const divested: PerformanceOverview = {
      ...overview, opening_value: "60000", closing_value: "130", contributions: "0",
      withdrawals: "-75000", net_external_flow: "-75000", investment_gain: "15130",
    };
    render(<PerformanceDecompositionChart {...base} overview={divested} periodLabel="INCEPTION" />);
    await userEvent.click(screen.getByRole("tab", { name: "Table" }));
    expect(screen.getAllByText("-$75,000.00").length).toBeGreaterThan(0);  // withdrawals, verbatim
    expect(screen.getByText("$130.00")).toBeInTheDocument();               // closing_value, verbatim
  });
});
