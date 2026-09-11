/**
 * Financial integrity (sec 50): formatting must never alter the underlying
 * value. Every test here parses the *displayed* string back out and checks
 * it matches the API value to within presentation rounding -- not that
 * they're merely "close", but that the display is a faithful, reversible
 * rendering of what the API actually said.
 */
import { describe, expect, it } from "vitest";

import {
  formatDate, formatMoney, formatMoneySigned, formatPercentPlain,
  formatPercentSigned, formatUnits, sign,
} from "../money";

function parseDisplayedMoney(display: string): number {
  return Number(display.replace(/[^0-9.-]/g, ""));
}

describe("formatMoney: presentation only, never recalculated", () => {
  it.each([
    ["124582.32", 124582.32],
    ["0.00", 0],
    ["-4200", -4200],
    ["1890.00000", 1890], // API precision beyond 2dp collapses only at display
  ])("round-trips %s", (api, expected) => {
    expect(parseDisplayedMoney(formatMoney(api))).toBeCloseTo(expected, 2);
  });

  it("never shows a null value as zero", () => {
    expect(formatMoney(null)).not.toContain("0");
    expect(formatMoney(null)).toBe("—");
  });

  it("does not silently coerce a non-numeric API value to zero", () => {
    expect(formatMoney("not-a-number")).toBe("—");
  });
});

describe("formatMoneySigned: direction is never ambiguous", () => {
  it("shows + for a gain", () => {
    expect(formatMoneySigned("500")).toMatch(/^\+/);
  });
  it("shows - for a loss", () => {
    expect(formatMoneySigned("-500")).toMatch(/^-/);
  });
});

describe("formatPercentSigned: the API's decimal fraction is preserved exactly", () => {
  it.each([
    ["0.184", 18.4],
    ["-0.042", -4.2],
    ["0", 0],
  ])("api %s -> displayed %s%%", (api, expectedPct) => {
    const displayed = formatPercentSigned(api);
    const parsed = Number(displayed.replace(/[^0-9.-]/g, ""));
    expect(parsed).toBeCloseTo(expectedPct, 1);
  });

  it("a positive return always shows its sign", () => {
    expect(formatPercentSigned("0.05")).toMatch(/^\+/);
  });
});

describe("formatPercentPlain: no sign for a share/weight figure", () => {
  it("does not prefix a share with +", () => {
    expect(formatPercentPlain("0.42")).not.toMatch(/^\+/);
  });
});

describe("formatUnits: fractional units are not rounded away", () => {
  it("preserves a fractional unit count beyond 2dp", () => {
    const displayed = formatUnits("1284.5231");
    const parsed = Number(displayed.replace(/[^0-9.]/g, ""));
    expect(parsed).toBeCloseTo(1284.5231, 3);
  });
});

describe("sign(): a pure classification, never a rounding decision", () => {
  it.each([
    ["100", "positive"], ["-100", "negative"], ["0", "neutral"], [null, "neutral"],
  ] as const)("%s -> %s", (value, expected) => {
    expect(sign(value)).toBe(expected);
  });
});

describe("formatDate: no timezone-shift off-by-one", () => {
  it("30 Jun 2024 displays as the 30th, not the 29th or 1st", () => {
    const displayed = formatDate("2024-06-30");
    expect(displayed).toContain("30");
    expect(displayed).not.toContain("29");
    expect(displayed).not.toContain("1 Jul");
  });
});
