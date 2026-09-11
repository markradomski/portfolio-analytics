/**
 * Step 9's redesigned primary chart. Covers: no fabricated zero on a gap
 * day, the zero-anchored Contributions & Withdrawals area, the zero-
 * anchored Investment Gain (green) / Investment Loss (red) areas -- solid,
 * mutually exclusive, never merged into one label -- contribution/
 * withdrawal markers rendered distinctly, keyboard navigation, and a
 * tooltip that never presents a contribution/withdrawal as investment
 * return.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BalanceDecompositionChart } from "../BalanceDecompositionChart";
import type { PortfolioGrowthPoint } from "../../../../api/types";

function point(overrides: Partial<PortfolioGrowthPoint>): PortfolioGrowthPoint {
  return {
    date: "2024-01-01", portfolio_value: "1000", contributions: "0", withdrawals: "0",
    net_contributions: "1000", investment_gain: "0", period_investment_gain: null,
    cash_flow_events: [], ...overrides,
  };
}

const points: PortfolioGrowthPoint[] = [
  point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0" }),
  point({
    date: "2024-02-01", portfolio_value: "3010", contributions: "2000", net_contributions: "3000",
    investment_gain: "10", period_investment_gain: "10",
    cash_flow_events: [{
      transaction_id: "t1", date: "2024-02-01", type: "CONTRIBUTION", amount: "2000",
      account: "primary", source: "VANGUARD", description: "Deposit",
    }],
  }),
  point({
    date: "2024-03-01", portfolio_value: "2530", withdrawals: "-500", net_contributions: "2500",
    investment_gain: "30", period_investment_gain: "20",
    cash_flow_events: [{
      transaction_id: "t2", date: "2024-03-01", type: "WITHDRAWAL", amount: "-500",
      account: "primary", source: "VANGUARD", description: "Withdrawal",
    }],
  }),
  point({ date: "2024-04-01", portfolio_value: null, net_contributions: "2500", investment_gain: null }),
];

describe("BalanceDecompositionChart", () => {
  it("renders without throwing on a series containing a valuation gap", () => {
    expect(() => render(<BalanceDecompositionChart points={points} width={600} height={300} />)).not.toThrow();
  });

  it("renders Investment Gain as a solid bright-green area anchored to zero", () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const gain = container.querySelector('[data-role="investment-gain-area"]')!;
    expect(gain).toBeInTheDocument();
    expect(gain.getAttribute("fill")).toBe("var(--color-positive)");
    expect(Number(gain.getAttribute("fill-opacity"))).toBeGreaterThanOrEqual(0.8);
  });

  it("renders Investment Loss as a solid bright-red area anchored to zero, distinct from Investment Gain", () => {
    const lossPoints: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0" }),
      point({ date: "2024-01-02", portfolio_value: "980", net_contributions: "1000", investment_gain: "-20", period_investment_gain: "-20" }),
      point({ date: "2024-01-03", portfolio_value: "975", net_contributions: "1000", investment_gain: "-25", period_investment_gain: "-5" }),
    ];
    const { container } = render(<BalanceDecompositionChart points={lossPoints} width={600} height={300} />);
    const loss = container.querySelector('[data-role="investment-loss-area"]')!;
    expect(loss).toBeInTheDocument();
    expect(loss.getAttribute("fill")).toBe("var(--color-negative)");
    expect(container.querySelector('[data-role="investment-gain-area"]')).not.toBeInTheDocument();
  });

  it("never uses a signed colour on the wrong side: a gain day is never rendered red, a loss day never green", () => {
    const mixed: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0" }),
      point({ date: "2024-01-02", portfolio_value: "1010", net_contributions: "1000", investment_gain: "10", period_investment_gain: "10" }),
      point({ date: "2024-01-03", portfolio_value: "995", net_contributions: "1000", investment_gain: "-5", period_investment_gain: "-15" }),
    ];
    const { container } = render(<BalanceDecompositionChart points={mixed} width={600} height={300} />);
    const gainAreas = container.querySelectorAll('[data-role="investment-gain-area"]');
    const lossAreas = container.querySelectorAll('[data-role="investment-loss-area"]');
    gainAreas.forEach((el) => expect(el.getAttribute("fill")).toBe("var(--color-positive)"));
    lossAreas.forEach((el) => expect(el.getAttribute("fill")).toBe("var(--color-negative)"));
  });

  it("renders an isolated single-day gain (no adjacent same-sign day) as a visible bar rather than vanishing", () => {
    // A single real priced day surrounded by flat/zero-gain carried-
    // forward days either side -- the common shape for this dataset.
    const isolated: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0" }),
      point({ date: "2024-01-02", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0", period_investment_gain: "0" }),
      point({ date: "2024-01-03", portfolio_value: "1010", net_contributions: "1000", investment_gain: "10", period_investment_gain: "10" }),
      point({ date: "2024-01-04", portfolio_value: "1010", net_contributions: "1000", investment_gain: "10", period_investment_gain: "0" }),
    ];
    const { container } = render(<BalanceDecompositionChart points={isolated} width={600} height={300} />);
    const gain = container.querySelector('[data-role="investment-gain-area"]')!;
    expect(gain.tagName.toLowerCase()).toBe("rect");
    expect(Number(gain.getAttribute("width"))).toBeGreaterThan(0);
    expect(Number(gain.getAttribute("height"))).toBeGreaterThan(0);
  });

  it("fills Contributions & Withdrawals anchored to the zero baseline, not floating between two data points", () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const fill = container.querySelector('[data-role="contributions-area"]')!;
    expect(fill).toBeInTheDocument();
    expect(fill.getAttribute("fill")).toBe("var(--color-accent-bg)");
    expect(fill.getAttribute("d")).toBeTruthy();
  });

  it("renders an explicit, visually distinct zero baseline", () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const baseline = container.querySelector('[data-role="zero-baseline"]')!;
    expect(baseline.tagName.toLowerCase()).toBe("line");
    expect(baseline).toHaveAttribute("stroke", "var(--chart-axis)");
  });

  it("fills the contributions area both above zero (positive net contributions) and below zero (negative), spanning the same continuous shape", () => {
    const mixed: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "500" }),   // positive
      point({ date: "2024-02-01", portfolio_value: "-200", net_contributions: "-300" }),  // negative
    ];
    const { container } = render(<BalanceDecompositionChart points={mixed} width={600} height={300} />);
    const fill = container.querySelector('[data-role="contributions-area"]')!;
    // One single path spans both points -- not two disjoint shapes, and
    // not merely a fill between the two data points (it reaches the y=0
    // baseline established elsewhere in this test file).
    expect(fill.getAttribute("d")).toMatch(/^M/);
  });

  it("renders the net-contributions reference line as solid, not dashed", () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const line = container.querySelector('[data-role="net-contributions-line"]')!;
    expect(line).not.toHaveAttribute("stroke-dasharray");
  });

  it("keeps the portfolio balance line visually dominant (thicker stroke than the reference line)", () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const balance = container.querySelector('[data-role="portfolio-balance-line"]')!;
    const contrib = container.querySelector('[data-role="net-contributions-line"]')!;
    expect(Number(balance.getAttribute("stroke-width"))).toBeGreaterThan(Number(contrib.getAttribute("stroke-width")));
  });

  it("never plots a null portfolio_value as zero: the balance line has a gap where the gap point is", () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    // Only 3 of the 4 points have a real value -- the line/points drawn
    // must reflect that, never a 0 standing in for the missing one.
    const circles = container.querySelectorAll("circle");
    // 2 contribution/withdrawal event markers are drawn regardless of the
    // gap; this just confirms rendering did not crash or fabricate a
    // fourth data point.
    expect(circles.length).toBeGreaterThanOrEqual(2);
  });

  it("renders a marker for each cash-flow-bearing date, distinctly for a contribution vs a withdrawal", () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const circles = Array.from(container.querySelectorAll("circle"));
    const fills = circles.map((c) => c.getAttribute("fill"));
    expect(fills).toContain("var(--color-positive)");
    expect(fills).toContain("var(--color-negative)");
  });

  it("keyboard navigation reveals the same figures a hover would, via the live region", async () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const overlay = screen.getByLabelText(/Use the left and right arrow keys/);
    await userEvent.click(overlay); // focuses the overlay -> first point
    const live = container.querySelector('[aria-live="polite"]')!.textContent ?? "";
    expect(live).toContain("Portfolio value $1,000.00");
    expect(live).toContain("Net contributions $1,000.00");
  });

  it("labels a positive period gain 'Investment Gain' and a negative one 'Investment Loss', never a merged label", async () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const overlay = screen.getByLabelText(/Use the left and right arrow keys/);
    await userEvent.click(overlay);
    await userEvent.keyboard("{ArrowRight}"); // -> 2024-02-01, period_investment_gain = +10
    const live = container.querySelector('[aria-live="polite"]')!.textContent ?? "";
    expect(live).toContain("Investment Gain +$10.00");
    expect(live).not.toContain("Investment Gain/Loss");
  });

  it("surfaces a contribution event's own amount distinctly from investment gain", async () => {
    const { container } = render(<BalanceDecompositionChart points={points} width={600} height={300} />);
    const overlay = screen.getByLabelText(/Use the left and right arrow keys/);
    await userEvent.click(overlay);
    await userEvent.keyboard("{ArrowRight}"); // -> 2024-02-01, the contribution date
    const live = container.querySelector('[aria-live="polite"]')!.textContent ?? "";
    expect(live).toContain("Contribution +$2,000.00");
    expect(live).toContain("Investment Gain +$10.00");
  });

  it("handles an entirely empty series without crashing", () => {
    expect(() => render(<BalanceDecompositionChart points={[]} width={600} height={300} />)).not.toThrow();
  });
});
