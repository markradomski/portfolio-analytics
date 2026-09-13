import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { sliceByPeriod } from "../PortfolioGrowthSection";
import type { PortfolioGrowthPoint } from "../../../api/types";

function point(dateStr: string): PortfolioGrowthPoint {
  return {
    date: dateStr, portfolio_value: "1000", contributions: "0", withdrawals: "0",
    net_contributions: "1000", investment_gain: "0", cash_flow_events: [],
  };
}

const series = [
  point("2019-01-01"), point("2021-06-30"), point("2023-06-30"),
  point("2024-06-30"), point("2025-06-30"),
];

describe("sliceByPeriod", () => {
  it("MAX returns every point unchanged", () => {
    expect(sliceByPeriod(series, "MAX")).toEqual(series);
  });

  it("1Y keeps only points within one year of the series' own last date", () => {
    const sliced = sliceByPeriod(series, "1Y");
    expect(sliced.map((p) => p.date)).toEqual(["2024-06-30", "2025-06-30"]);
  });

  it("3Y keeps points within three years of the last date", () => {
    const sliced = sliceByPeriod(series, "3Y");
    expect(sliced.map((p) => p.date)).toEqual(["2023-06-30", "2024-06-30", "2025-06-30"]);
  });

  it("5Y keeps points within five years of the last date", () => {
    const sliced = sliceByPeriod(series, "5Y");
    expect(sliced.map((p) => p.date)).toEqual(["2021-06-30", "2023-06-30", "2024-06-30", "2025-06-30"]);
  });

  it("returns an empty array unchanged rather than throwing", () => {
    expect(sliceByPeriod([], "1Y")).toEqual([]);
  });

  it("1M keeps points within a month of the last date", () => {
    const monthly = [point("2025-05-01"), point("2025-06-01"), point("2025-06-25"), point("2025-06-30")];
    expect(sliceByPeriod(monthly, "1M").map((p) => p.date)).toEqual(["2025-06-01", "2025-06-25", "2025-06-30"]);
  });

  it("3M keeps points within three months of the last date", () => {
    const quarterly = [point("2025-01-01"), point("2025-04-01"), point("2025-06-30")];
    expect(sliceByPeriod(quarterly, "3M").map((p) => p.date)).toEqual(["2025-04-01", "2025-06-30"]);
  });

  it("6M keeps points within six months of the last date", () => {
    const half = [point("2024-11-01"), point("2025-01-15"), point("2025-06-30")];
    expect(sliceByPeriod(half, "6M").map((p) => p.date)).toEqual(["2025-01-15", "2025-06-30"]);
  });

  describe("YTD", () => {
    const RealDate = Date;
    beforeEach(() => {
      // "Today" is 10 Sept 2026 -- YTD must start 1 Jan of *this* year,
      // never "the last 12 months".
      vi.setSystemTime(new RealDate(2026, 8, 10));
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    it("starts on 1 January of the current calendar year, not 12 months back", () => {
      const points = [
        point("2025-06-30"),   // last year -- must be excluded
        point("2026-01-01"),   // exactly the YTD boundary -- must be included
        point("2026-06-30"),
      ];
      expect(sliceByPeriod(points, "YTD").map((p) => p.date)).toEqual(["2026-01-01", "2026-06-30"]);
    });

    it("anchors to the series' own latest year, not the browser's wall-clock year, when the series ends before 'now'", () => {
      // "Today" is 2026 (see beforeEach), but the series -- like the demo
      // dataset -- ends in 2024. YTD must still return the tail of 2024,
      // not an empty array (the exact bug this regression test covers).
      const points = [point("2023-06-30"), point("2024-01-01"), point("2024-06-30")];
      expect(sliceByPeriod(points, "YTD").map((p) => p.date)).toEqual(["2024-01-01", "2024-06-30"]);
    });

    it("picks the first available point on or after 1 January when no exact 1 Jan point exists", () => {
      const points = [point("2023-11-30"), point("2024-02-15"), point("2024-06-30")];
      expect(sliceByPeriod(points, "YTD").map((p) => p.date)).toEqual(["2024-02-15", "2024-06-30"]);
    });
  });

  it("gracefully clamps to the earliest available date rather than returning an empty series (insufficient history)", () => {
    // Only ~2 years of history exist; 5Y must fall back to everything
    // available rather than producing an empty chart.
    const shortHistory = [point("2024-06-30"), point("2025-01-01"), point("2025-06-30")];
    expect(sliceByPeriod(shortHistory, "5Y")).toEqual(shortHistory);
  });
});
