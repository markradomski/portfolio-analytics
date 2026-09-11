import { describe, expect, it } from "vitest";

import { usePeriodTabs } from "../usePeriodTabs";
import type { PerformancePeriod } from "../../api/types";

function period(overrides: Partial<PerformancePeriod>): PerformancePeriod {
  return {
    label: "1Y", as_at: "2026-06-30", start_date: null, end_date: null,
    total_return: null, capital_return: null, income_return: null,
    twrr: null, xirr: null, status: "actual", note: null, ...overrides,
  };
}

describe("usePeriodTabs", () => {
  it("enables a period the backend reports as available", () => {
    const tabs = usePeriodTabs(["1Y"], [period({ label: "1Y", status: "actual", total_return: "0.1" })]);
    expect(tabs[0].disabled).toBeUndefined();
  });

  it("disables a period the backend explicitly marks unavailable, with its stated reason", () => {
    const tabs = usePeriodTabs(
      ["1M"],
      [period({ label: "1M", status: "unavailable", note: "nearest valuations span 91 days" })],
    );
    expect(tabs[0].disabled).toBe(true);
    expect(tabs[0].disabledReason).toBe("nearest valuations span 91 days");
  });

  it("disables a period the backend has no entry for at all -- never silently omitted (sec 12)", () => {
    const tabs = usePeriodTabs(["10Y"], [period({ label: "1Y" })]);
    expect(tabs[0].disabled).toBe(true);
  });

  it("never invents its own availability rule -- only the backend's status decides", () => {
    // A period the frontend might assume is "too short to matter" is still
    // enabled purely because the backend marked it actual/available.
    const tabs = usePeriodTabs(["1M"], [period({ label: "1M", status: "actual" })]);
    expect(tabs[0].disabled).toBeUndefined();
  });
});
