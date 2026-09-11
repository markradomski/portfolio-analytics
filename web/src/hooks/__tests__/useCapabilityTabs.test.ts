import { describe, expect, it } from "vitest";

import { useCapabilityTabs } from "../useCapabilityTabs";
import type { AnalyticsCapabilities } from "../../api/types";

describe("useCapabilityTabs", () => {
  const capabilities: AnalyticsCapabilities = {
    daily_returns: { available: false, reason: "Insufficient daily valuation observations" },
    quarterly_returns: { available: true, reason: null },
  };

  it("disables a period the API marks unavailable, with its stated reason", () => {
    const tabs = useCapabilityTabs(
      [{ value: "1D", label: "1D", capabilityKey: "daily_returns" }],
      capabilities,
    );
    expect(tabs[0].disabled).toBe(true);
    expect(tabs[0].disabledReason).toBe("Insufficient daily valuation observations");
  });

  it("enables a period the API marks available", () => {
    const tabs = useCapabilityTabs(
      [{ value: "3M", label: "3M", capabilityKey: "quarterly_returns" }],
      capabilities,
    );
    expect(tabs[0].disabled).toBeUndefined();
  });

  it("never applies a frontend-invented rule -- absence of a capability entry does not disable", () => {
    const tabs = useCapabilityTabs([{ value: "5Y", label: "5Y" }], capabilities);
    expect(tabs[0].disabled).toBeUndefined();
  });

  it("leaves a period enabled while capabilities are still loading (undefined)", () => {
    const tabs = useCapabilityTabs([{ value: "1Y", label: "1Y", capabilityKey: "quarterly_returns" }], undefined);
    expect(tabs[0].disabled).toBeUndefined();
  });
});
