import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { MethodologyPopover } from "../../components/data-quality/MethodologyPopover/MethodologyPopover";
import { UnavailableMetric } from "../../components/data-quality/UnavailableMetric/UnavailableMetric";
import { formatPercentSigned } from "../../formatting/money";
import type { PerformancePeriod, TwrrMethodology } from "../../api/types";
import styles from "./PerformancePage.module.css";

export interface MethodologyPanelProps {
  activePeriod: PerformancePeriod | undefined;
  twrrMethodology: TwrrMethodology;
}

/**
 * Sec 13-15: TWRR and XIRR side by side, each carrying its own methodology
 * disclosure rather than a generic "calculated return" label -- and an
 * explanation of *why* two legitimate figures can differ, without implying
 * either one is more "correct" (sec 15's explicit instruction).
 */
export function MethodologyPanel({ activePeriod, twrrMethodology }: MethodologyPanelProps) {
  const twrr = activePeriod?.twrr;
  const xirr = activePeriod?.xirr;
  const unavailable = !activePeriod || activePeriod.status === "unavailable";

  return (
    <div className={styles.methodologyGrid}>
      <div>
        <MetricValue
          label="Time-weighted return (TWRR)"
          value={twrr != null ? formatPercentSigned(twrr) : null}
          rawValue={twrr}
          unavailableReason={twrr == null ? (unavailable ? activePeriod?.note ?? "Not enough valuation history" : "Not available for this period") : undefined}
        />
        <MethodologyPopover
          summary={twrrMethodology.twrr_methodology === "SUBPERIOD_LINKED" ? "Sub-period linked" : twrrMethodology.twrr_methodology}
          detail={twrrMethodology.twrr_methodology_note}
        />
      </div>

      <div>
        <MetricValue
          label="Money-weighted return (XIRR)"
          value={xirr != null ? formatPercentSigned(xirr) : null}
          rawValue={xirr}
          unavailableReason={xirr == null ? (unavailable ? activePeriod?.note ?? "Not enough valuation history" : "Not available for this period") : undefined}
        />
        <MethodologyPopover
          summary="Cash-flow adjusted"
          detail={twrrMethodology.cash_flow_adjustment_note}
        />
      </div>

      <div className={styles.methodologyExplainer}>
        {twrr != null && xirr != null ? (
          <p>
            TWRR neutralises the timing of contributions and withdrawals, measuring the portfolio's own investment
            performance. XIRR incorporates exactly when and how much cash moved in and out. The two can legitimately
            differ — neither is "the" correct answer, they answer different questions.
          </p>
        ) : (
          <UnavailableMetric
            title="TWRR vs XIRR comparison"
            reason="Both figures are needed to compare them, and at least one is unavailable for this period."
          />
        )}
      </div>
    </div>
  );
}
