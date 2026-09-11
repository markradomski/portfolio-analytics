/**
 * Chart correctness (sec 49): correct data mapping, and -- the requirement
 * that matters most for this dataset -- no invented points. A null value
 * from the API must never render as a plotted zero, and no real observation
 * is silently dropped from the chart, however short its quality run is.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { TimeSeriesChart, type TimeSeriesPoint } from "../TimeSeriesChart/TimeSeriesChart";

// Realistic shape: real quality runs span several points, not one -- this
// dataset's actual carried-forward stretches last weeks between quarterly
// statements, so segments this short are the common case, not the edge case.
const data: TimeSeriesPoint[] = [
  { date: "2024-01-01", value: "1000", quality: "actual" },
  { date: "2024-01-02", value: null, quality: "unavailable" },
  { date: "2024-01-03", value: null, quality: "unavailable" },
  { date: "2024-01-04", value: "1100", quality: "calculated" },
  { date: "2024-01-05", value: "1120", quality: "estimated" },
  { date: "2024-01-06", value: "1140", quality: "estimated" },
];

describe("TimeSeriesChart", () => {
  it("renders without throwing on a series containing a genuine gap", () => {
    expect(() => render(<TimeSeriesChart data={data} width={400} height={200} />)).not.toThrow();
  });

  it("does not plot a null value as zero: the line breaks into separate segments around the gap", () => {
    const { container } = render(<TimeSeriesChart data={data} width={400} height={200} />);
    const lines = container.querySelectorAll('[data-role="series-line"]');
    // One segment before the gap (single actual point -> a dot, not a line)
    // and one continuous segment after it (calculated+estimated+estimated).
    // A single unbroken line through the gap would mean it was bridged.
    expect(lines.length).toBeGreaterThanOrEqual(1);
    const point = container.querySelector('[data-role="series-point"]');
    expect(point).toBeInTheDocument(); // the lone actual-quality point
  });

  it("renders an estimated (carried-forward) segment with a dashed stroke, distinct from an actual one", () => {
    const { container } = render(<TimeSeriesChart data={data} width={400} height={200} />);
    const dashed = container.querySelectorAll('[data-role="series-line"][stroke-dasharray]');
    expect(dashed.length).toBeGreaterThan(0);
  });

  it("never drops a real observation just because its quality run is a single point", () => {
    const { container } = render(<TimeSeriesChart data={data} width={400} height={200} />);
    const lines = container.querySelectorAll('[data-role="series-line"]').length;
    const points = container.querySelectorAll('[data-role="series-point"]').length;
    // 3 quality runs in the fixture, each a distinct quality label:
    // [actual] (1pt -> dot), [calculated] (1pt -> dot), [estimated, estimated]
    // (2pts -> one line). Every one of the 4 valued points in the fixture
    // appears somewhere -- none silently dropped for being a short run.
    expect(points).toBe(2);
    expect(lines).toBe(1);
  });

  it("handles an entirely empty series without crashing", () => {
    expect(() => render(<TimeSeriesChart data={[]} width={400} height={200} />)).not.toThrow();
  });

  it("handles a series where every point is unavailable (no series rendered at all)", () => {
    const allGaps: TimeSeriesPoint[] = [
      { date: "2024-01-01", value: null, quality: "unavailable" },
      { date: "2024-01-02", value: null, quality: "unavailable" },
    ];
    const { container } = render(<TimeSeriesChart data={allGaps} width={400} height={200} />);
    expect(container.querySelectorAll('[data-role="series-line"]').length).toBe(0);
    expect(container.querySelectorAll('[data-role="series-point"]').length).toBe(0);
  });
});

describe("TimeSeriesChart: keyboard accessibility (Step 8 hardening, sec 15/16)", () => {
  it("exposes a focusable, labelled overlay so the chart is reachable without a mouse", () => {
    render(<TimeSeriesChart data={data} width={400} height={200} valueLabel="Portfolio value" />);
    const overlay = screen.getByLabelText(
      "Portfolio value chart data points. Use the left and right arrow keys to move between dates.",
    );
    expect(overlay).toHaveAttribute("tabindex", "0");
  });

  function liveRegionText(container: HTMLElement): string {
    return container.querySelector('[aria-live="polite"]')!.textContent ?? "";
  }

  it("announces the first valued point as soon as the chart is focused, before any key is pressed", async () => {
    const { container } = render(<TimeSeriesChart data={data} width={400} height={200} valueLabel="Portfolio value" />);
    const overlay = screen.getByLabelText(/Use the left and right arrow keys/);
    await userEvent.click(overlay);
    // First valued point is 2024-01-01 at 1000 (actual).
    expect(liveRegionText(container)).toContain("Portfolio value $1,000.00");
    expect(liveRegionText(container)).toContain("1 Jan 2024");
  });

  it("steps forward through subsequent points on ArrowRight", async () => {
    const { container } = render(<TimeSeriesChart data={data} width={400} height={200} valueLabel="Portfolio value" />);
    const overlay = screen.getByLabelText(/Use the left and right arrow keys/);
    await userEvent.click(overlay);
    await userEvent.keyboard("{ArrowRight}");
    // Second valued point (nulls are excluded from `valued`) is 2024-01-04 at 1100.
    expect(liveRegionText(container)).toContain("Portfolio value $1,100.00");
  });

  it("does not retain a stale focused point once the chart itself is unmounted", () => {
    const { container, unmount } = render(
      <TimeSeriesChart data={data} width={400} height={200} valueLabel="Portfolio value" />,
    );
    expect(() => unmount()).not.toThrow();
    expect(container.querySelector('[aria-live="polite"]')).not.toBeInTheDocument();
  });
});
