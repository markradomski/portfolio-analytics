/**
 * Sec 13-14: the stacked allocation-over-time primitive plots exactly the
 * proportions the backend already computed -- no weight or total is
 * derived here, and a category with no observation on a given date is
 * simply absent from that date's stack, never filled in as zero.
 */
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import { AllocationHistoryChart } from "../AllocationHistoryChart/AllocationHistoryChart";
import type { AllocationHistoryPoint } from "../../../api/types";

beforeAll(() => {
  // @ts-expect-error -- test-environment polyfill; this chart has no
  // ChartContainer of its own, but jsdom still lacks ResizeObserver
  // globally for any sibling chart that might be mounted in the same tree.
  global.ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
});

const data: AllocationHistoryPoint[] = [
  { date: "2024-01-01", total: "1000", weights: { cash: "1000" }, allocation_pct: { cash: "1" } },
  {
    date: "2025-01-01", total: "1000",
    weights: { australian_equities: "700", cash: "300" },
    allocation_pct: { australian_equities: "0.7", cash: "0.3" },
  },
];

describe("AllocationHistoryChart", () => {
  it("renders without throwing for a real multi-category series", () => {
    expect(() => render(<AllocationHistoryChart data={data} width={400} height={200} />)).not.toThrow();
  });

  it("renders one band per category actually present in the data", () => {
    const { container } = render(<AllocationHistoryChart data={data} width={400} height={200} />);
    const bands = container.querySelectorAll('[data-role="allocation-band"]');
    const categories = Array.from(bands).map((b) => b.getAttribute("data-category"));
    expect(categories.sort()).toEqual(["australian_equities", "cash"]);
  });

  it("renders a meaningful empty state rather than an empty chart when there is no history", () => {
    render(<AllocationHistoryChart data={[]} width={400} height={200} />);
    expect(screen.getByText("No allocation history available yet.")).toBeInTheDocument();
  });
});
