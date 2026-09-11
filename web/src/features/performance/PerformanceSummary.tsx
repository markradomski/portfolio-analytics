import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { DataQualityBadge } from "../../components/data-quality/DataQualityBadge/DataQualityBadge";
import { formatMoney, formatMoneySigned, formatPercentSigned } from "../../formatting/money";
import type { DataQuality, PerformanceOverview, PerformancePeriod } from "../../api/types";
import styles from "./PerformancePage.module.css";

const KNOWN_QUALITIES: readonly DataQuality[] = ["actual", "calculated", "estimated", "limited", "unavailable"];

/** PerformancePeriod.status is a plain string in the schema (it also
 * carries the literal "unavailable" a ValuationStatus alone doesn't) --
 * this narrows it to the badge's known vocabulary rather than passing an
 * arbitrary string through, falling back to "unavailable" for anything
 * unrecognised (never rendering a badge with a made-up quality label). */
function asDataQuality(status: string): DataQuality {
  return (KNOWN_QUALITIES as readonly string[]).includes(status) ? (status as DataQuality) : "unavailable";
}

const PERIOD_PHRASE: Record<string, string> = {
  "1M": "Over the last month", "3M": "Over the last 3 months", "6M": "Over the last 6 months",
  YTD: "Year to date", "1Y": "Over the last year", "3Y": "Over the last 3 years",
  "5Y": "Over the last 5 years", INCEPTION: "Since inception",
};

export interface PerformanceSummaryProps {
  /** The percentage figures (total/capital/income return) come from this
   * single PerformancePeriod entry -- the same one the period tabs and the
   * TWRR/XIRR section read from. A second endpoint (/performance with an
   * explicit start/end) computes an overlapping-but-not-identical set of
   * percentages for the same nominal window (it treats `start` as
   * exclusive, so its "opening value" can legitimately fall in a data gap
   * a day before an otherwise-real valuation) -- mixing the two would put
   * two different numbers on screen under the same label, so every
   * percentage here is sourced from exactly one place. */
  activePeriod: PerformancePeriod | undefined;
  /** Only its dollar fields are used -- investment_gain/contributions/
   * withdrawals, which PerformancePeriod itself doesn't carry. May be
   * unavailable (null fields) for a window whose exclusive start falls in
   * a valuation gap; shown as Unavailable rather than papered over. */
  dollarOverview: PerformanceOverview | undefined;
  periodLabel: string;
}

/**
 * Sec 6's primary summary: total return, total gain, capital return, income
 * return, for the selected period -- and only ever labelled with the
 * period the backend actually computed it over (never "since inception"
 * unless INCEPTION is what's selected).
 */
export function PerformanceSummary({ activePeriod, dollarOverview, periodLabel }: PerformanceSummaryProps) {
  const phrase = PERIOD_PHRASE[periodLabel] ?? `Over ${periodLabel}`;
  const unavailableReason = !activePeriod || activePeriod.status === "unavailable"
    ? activePeriod?.note ?? "Not enough valuation history for this period"
    : undefined;

  return (
    <div>
      <div className={styles.summaryRow}>
        <MetricValue
          label="Total return"
          value={activePeriod?.total_return != null ? formatPercentSigned(activePeriod.total_return) : null}
          rawValue={activePeriod?.total_return}
          size="large"
          unavailableReason={activePeriod?.total_return == null ? unavailableReason : undefined}
          meta={activePeriod && <DataQualityBadge quality={asDataQuality(activePeriod.status)} />}
        />
        <MetricValue
          label="Total gain"
          value={dollarOverview?.investment_gain != null ? formatMoneySigned(dollarOverview.investment_gain) : null}
          rawValue={dollarOverview?.investment_gain}
          unavailableReason={dollarOverview?.investment_gain == null ? "No valuation on the exact opening date of this window" : undefined}
        />
        <MetricValue
          label="Capital return"
          value={activePeriod?.capital_return != null ? formatPercentSigned(activePeriod.capital_return) : null}
          rawValue={activePeriod?.capital_return}
          unavailableReason={activePeriod?.capital_return == null ? unavailableReason : undefined}
        />
        <MetricValue
          label="Income return"
          value={activePeriod?.income_return != null ? formatPercentSigned(activePeriod.income_return) : null}
          rawValue={activePeriod?.income_return}
          unavailableReason={activePeriod?.income_return == null ? unavailableReason : undefined}
        />
      </div>
      <p className={styles.periodPhrase}>{phrase}</p>
      {dollarOverview && (dollarOverview.contributions !== "0" || dollarOverview.withdrawals !== "0") && (
        <p className={styles.flowNote}>
          {formatMoney(dollarOverview.contributions)} contributed and {formatMoney(dollarOverview.withdrawals)}{" "}
          withdrawn this period — external cash flow, not part of the return above.
        </p>
      )}
    </div>
  );
}
