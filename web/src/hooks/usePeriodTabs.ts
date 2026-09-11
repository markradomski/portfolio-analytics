import type { PerformancePeriod } from "../api/types";
import type { TabItem } from "../design-system/Tabs/Tabs";

/** The Overview's period selector (sec 8/12): every label's availability
 * comes from the backend's own getReturns() entry for that label, never a
 * frontend rule about how much history "should" exist. A label the backend
 * has no entry for at all is treated the same as one it explicitly marked
 * unavailable -- there is nothing to show for it either way. */
export function usePeriodTabs(labels: string[], periods: PerformancePeriod[] | undefined): TabItem[] {
  const byLabel = new Map((periods ?? []).map((p) => [p.label, p]));
  return labels.map((label) => {
    const period = byLabel.get(label);
    if (!period || period.status === "unavailable") {
      return { value: label, label, disabled: true, disabledReason: period?.note ?? "Not enough history for this period" };
    }
    return { value: label, label };
  });
}
