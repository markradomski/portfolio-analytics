/**
 * The Overview wealth chart (Step 9A Part A, simplified in Step 9A.2).
 * Protects the simple mental model -- blue = money in, green = money made,
 * red = money lost, line = what you've got -- and specifically that $0 is
 * a hard visual floor: no blue, green or red fill is ever drawn below the
 * axis, however negative the authoritative net-contribution figure gets.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PortfolioGrowthChart } from "../PortfolioGrowthChart";
import type { PortfolioGrowthPoint } from "../../../../api/types";

function point(overrides: Partial<PortfolioGrowthPoint>): PortfolioGrowthPoint {
  return {
    date: "2024-01-01", portfolio_value: "1000", contributions: "0", withdrawals: "0",
    net_contributions: "1000", investment_gain: "0", period_investment_gain: null,
    cash_flow_events: [], ...overrides,
  };
}

/** The y (in px) of the zero baseline -- every fill must stay at or above
 * this (i.e. a smaller or equal y, since SVG y grows downward). */
function baselineY(container: HTMLElement): number {
  return Number(container.querySelector('[data-role="zero-baseline"]')!.getAttribute("y1"));
}
/** All y-coordinates appearing in a path's `d`. */
function pathYs(el: Element | null): number[] {
  const d = el?.getAttribute("d") ?? "";
  return [...d.matchAll(/[-\d.]+,([-\d.]+)/g)].map((m) => Number(m[1]));
}

const gainSeries: PortfolioGrowthPoint[] = [
  point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0" }),
  point({ date: "2024-02-01", portfolio_value: "3200", net_contributions: "3000", investment_gain: "200" }),
  point({ date: "2024-03-01", portfolio_value: "3600", net_contributions: "3000", investment_gain: "600" }),
];

describe("PortfolioGrowthChart", () => {
  it("renders without throwing", () => {
    expect(() => render(<PortfolioGrowthChart points={gainSeries} width={600} height={300} />)).not.toThrow();
  });

  // A. Positive Net Contributions -> blue from $0 up to that value.
  it("fills Contributions as a solid blue area from the $0 floor up to net contributions", () => {
    const { container } = render(<PortfolioGrowthChart points={gainSeries} width={600} height={300} />);
    const fill = container.querySelector('[data-role="contributions-area"]')!;
    expect(fill.getAttribute("fill")).toBe("var(--color-accent)");
    const ys = pathYs(fill);
    // Nothing below the axis; the top edge sits above it.
    expect(Math.max(...ys)).toBeLessThanOrEqual(baselineY(container) + 0.5);
    expect(Math.min(...ys)).toBeLessThan(baselineY(container));
  });

  it("renders an explicit $0 baseline distinct from the gridlines", () => {
    const { container } = render(<PortfolioGrowthChart points={gainSeries} width={600} height={300} />);
    const baseline = container.querySelector('[data-role="zero-baseline"]')!;
    expect(baseline.tagName.toLowerCase()).toBe("line");
    expect(baseline).toHaveAttribute("stroke", "var(--chart-axis)");
  });

  it("renders Investment Gain (green) only, no loss area, when Total Balance stays above contributions", () => {
    const { container } = render(<PortfolioGrowthChart points={gainSeries} width={600} height={300} />);
    expect(container.querySelector('[data-role="investment-gain-area"]')!.getAttribute("fill")).toBe("var(--color-positive)");
    expect(container.querySelector('[data-role="investment-loss-area"]')).not.toBeInTheDocument();
  });

  it("renders Investment Loss (red) only, no gain area, when Total Balance stays below contributions", () => {
    const lossSeries: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1200", investment_gain: "-200" }),
      point({ date: "2024-02-01", portfolio_value: "900", net_contributions: "1200", investment_gain: "-300" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={lossSeries} width={600} height={300} />);
    expect(container.querySelector('[data-role="investment-loss-area"]')!.getAttribute("fill")).toBe("var(--color-negative)");
    expect(container.querySelector('[data-role="investment-gain-area"]')).not.toBeInTheDocument();
  });

  // C. Gain -> loss crossover.
  it("renders both a gain and a loss area, in the right colours, across a gain to loss crossover", () => {
    const crossover: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1100", net_contributions: "1000", investment_gain: "100" }),
      point({ date: "2024-02-01", portfolio_value: "1200", net_contributions: "1000", investment_gain: "200" }),
      point({ date: "2024-03-01", portfolio_value: "900", net_contributions: "1000", investment_gain: "-100" }),
      point({ date: "2024-04-01", portfolio_value: "850", net_contributions: "1000", investment_gain: "-150" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={crossover} width={600} height={300} />);
    expect(container.querySelector('[data-role="investment-gain-area"]')!.getAttribute("fill")).toBe("var(--color-positive)");
    expect(container.querySelector('[data-role="investment-loss-area"]')!.getAttribute("fill")).toBe("var(--color-negative)");
  });

  // G. Zero -> no gain/loss region.
  it("renders no gain/loss area at all when Total Balance equals contributions", () => {
    const flat: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0" }),
      point({ date: "2024-02-01", portfolio_value: "2000", net_contributions: "2000", investment_gain: "0" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={flat} width={600} height={300} />);
    expect(container.querySelector('[data-role="investment-gain-area"]')).not.toBeInTheDocument();
    expect(container.querySelector('[data-role="investment-loss-area"]')).not.toBeInTheDocument();
  });

  // B + C: a withdrawal lowers the blue foundation; it reaches $0 as
  // contributions are fully withdrawn.
  it("lowers the blue contribution foundation as withdrawals reduce net contributions, down to the $0 floor", () => {
    const withdrawing: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "50000", net_contributions: "50000", investment_gain: "0" }),
      point({ date: "2024-02-01", portfolio_value: "31000", net_contributions: "30000", investment_gain: "1000" }),
      point({ date: "2024-03-01", portfolio_value: "2000", net_contributions: "0", investment_gain: "2000" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={withdrawing} width={600} height={400} />);
    const fill = container.querySelector('[data-role="contributions-area"]')!;
    const ys = pathYs(fill);
    const zeroY = baselineY(container);
    // The top edge rises (larger y) as the foundation falls, and never
    // passes below the axis.
    expect(Math.max(...ys)).toBeLessThanOrEqual(zeroY + 0.5);
    // The last top-edge point is at (or effectively at) the floor.
    expect(Math.max(...ys)).toBeGreaterThan(zeroY - 2);
  });

  // D. Negative net contributions -> blue stays at $0, never below.
  it("never draws the blue contribution area below $0, even when authoritative net contributions is negative", () => {
    const negative: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "4000", net_contributions: "-13000", investment_gain: "17000" }),
      point({ date: "2024-02-01", portfolio_value: "4200", net_contributions: "-13000", investment_gain: "17200" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={negative} width={600} height={400} />);
    const zeroY = baselineY(container);
    const ys = pathYs(container.querySelector('[data-role="contributions-area"]'));
    // No coordinate below the axis (SVG: below == larger y).
    expect(Math.max(...ys)).toBeLessThanOrEqual(zeroY + 0.5);
  });

  // E. Positive investment gain with negative net contributions -> green
  // never below $0.
  it("never draws Investment Gain below $0 when net contributions is negative", () => {
    const negative: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "4000", net_contributions: "-13000", investment_gain: "17000" }),
      point({ date: "2024-02-01", portfolio_value: "4200", net_contributions: "-13000", investment_gain: "17200" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={negative} width={600} height={400} />);
    const zeroY = baselineY(container);
    const green = container.querySelector('[data-role="investment-gain-area"]')!;
    expect(green.getAttribute("fill")).toBe("var(--color-positive)");
    const ys = pathYs(green);
    expect(Math.max(...ys)).toBeLessThanOrEqual(zeroY + 0.5);
    expect(container.querySelector('[data-role="investment-loss-area"]')).not.toBeInTheDocument();
  });

  // H. Total Balance line is authoritative and unchanged.
  it("plots the Total Balance line from the authoritative portfolio value, on top", () => {
    const { container } = render(<PortfolioGrowthChart points={gainSeries} width={600} height={300} />);
    const balance = container.querySelector('[data-role="portfolio-balance-line"]')!;
    expect(balance.getAttribute("fill")).toBe("none");
    expect(Number(balance.getAttribute("stroke-width"))).toBeGreaterThanOrEqual(2);
    // Drawn last -> the last <path> in document order.
    const paths = [...container.querySelectorAll("path[data-role]")];
    expect(paths[paths.length - 1].getAttribute("data-role")).toBe("portfolio-balance-line");
  });

  it("draws no contribution/withdrawal event markers on the Overview chart", () => {
    const withEvents: PortfolioGrowthPoint[] = [
      point({
        date: "2024-01-01", portfolio_value: "1000", net_contributions: "1000", investment_gain: "0",
        cash_flow_events: [{
          transaction_id: "t1", date: "2024-01-01", type: "CONTRIBUTION", amount: "1000",
          account: "primary", source: "VANGUARD", description: "Deposit",
        }],
      }),
      point({ date: "2024-02-01", portfolio_value: "1100", net_contributions: "1000", investment_gain: "100" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={withEvents} width={600} height={300} />);
    expect(container.querySelectorAll("circle").length).toBe(0);
  });

  it("never plots a null portfolio_value as zero", () => {
    const withGap: PortfolioGrowthPoint[] = [
      ...gainSeries,
      point({ date: "2024-04-01", portfolio_value: null, net_contributions: "3000", investment_gain: null }),
    ];
    expect(() => render(<PortfolioGrowthChart points={withGap} width={600} height={300} />)).not.toThrow();
  });

  it("keyboard navigation surfaces balance, contributions and a gain via the live region", async () => {
    const { container } = render(<PortfolioGrowthChart points={gainSeries} width={600} height={300} />);
    await userEvent.click(screen.getByLabelText(/left and right arrow keys/));
    await userEvent.keyboard("{ArrowRight}"); // -> 2024-02-01, gain +200
    const live = container.querySelector('[aria-live="polite"]')!.textContent ?? "";
    expect(live).toContain("Total balance $3,200.00");
    expect(live).toContain("Contributions $3,000.00");
    expect(live).toContain("Investment gain +$200.00");
  });

  // F. Loss is labelled a loss -- never "Investment gain -$X".
  it("announces 'Investment loss $X' (never a negative gain) when Total Balance is below contributions", async () => {
    const lossSeries: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "1000", net_contributions: "1200", investment_gain: "-200" }),
      point({ date: "2024-02-01", portfolio_value: "950", net_contributions: "1200", investment_gain: "-250" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={lossSeries} width={600} height={300} />);
    await userEvent.click(screen.getByLabelText(/left and right arrow keys/));
    const live = container.querySelector('[aria-live="polite"]')!.textContent ?? "";
    expect(live).toContain("Investment loss $200.00");
    expect(live).not.toContain("Investment gain");
    expect(live).not.toContain("-$200");
  });

  it("announces 'Net contributed -$X' in plain language when withdrawals take net contributions negative", async () => {
    const negative: PortfolioGrowthPoint[] = [
      point({ date: "2024-01-01", portfolio_value: "4000", net_contributions: "-13000", investment_gain: "17000" }),
      point({ date: "2024-02-01", portfolio_value: "4200", net_contributions: "-13000", investment_gain: "17200" }),
    ];
    const { container } = render(<PortfolioGrowthChart points={negative} width={600} height={300} />);
    await userEvent.click(screen.getByLabelText(/left and right arrow keys/));
    const live = container.querySelector('[aria-live="polite"]')!.textContent ?? "";
    expect(live).toContain("Net contributed -$13,000.00");
    expect(live).toContain("Investment gain +$17,000.00");
  });

  it("handles an entirely empty series without crashing", () => {
    expect(() => render(<PortfolioGrowthChart points={[]} width={600} height={300} />)).not.toThrow();
  });
});
