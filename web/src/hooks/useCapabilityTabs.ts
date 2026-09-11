import type { AnalyticsCapabilities } from "../api/types";
import type { TabItem } from "../design-system/Tabs/Tabs";

/**
 * Turns a period label list into Tabs items whose disabled state and reason
 * come entirely from getAnalyticsCapabilities() -- never a frontend rule
 * like `if (years < 1)` (sec 39). A period this hook doesn't find a
 * matching capability for is left enabled, since the absence of a
 * capability entry is not itself a reason to disable something the caller
 * asked to show.
 */
export function useCapabilityTabs(
  labels: { value: string; label: string; capabilityKey?: string }[],
  capabilities: AnalyticsCapabilities | undefined,
): TabItem[] {
  return labels.map(({ value, label, capabilityKey }) => {
    const capability = capabilityKey ? capabilities?.[capabilityKey] : undefined;
    if (!capability || capability.available) {
      return { value, label };
    }
    return { value, label, disabled: true, disabledReason: capability.reason ?? undefined };
  });
}
