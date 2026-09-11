import { formatDate } from "../../../formatting/money";
import type { DataCoverage } from "../../../api/types";
import styles from "./DataCoverageBadge.module.css";

export interface DataCoverageBadgeProps {
  coverage: DataCoverage;
}

/** The compact coverage line (sec 11): "24 valuation observations ·
 * quarterly source data" -- reads entirely from getDataCoverage(), never a
 * frontend guess about how sparse the data is. Meant for progressive
 * disclosure: a single line by default, expandable detail via
 * MethodologyPopover where a screen wants more. */
export function DataCoverageBadge({ coverage }: DataCoverageBadgeProps) {
  if (coverage.valuation_observation_count === 0) {
    return <span className={styles.line}>No valuation history available yet</span>;
  }
  const frequency = inferFrequencyLabel(coverage);
  return (
    <span className={styles.line}>
      {formatDate(coverage.valuation_start)} – {formatDate(coverage.valuation_end)} ·{" "}
      {coverage.valuation_observation_count} valuation observation{coverage.valuation_observation_count === 1 ? "" : "s"} ·{" "}
      {frequency}
    </span>
  );
}

function inferFrequencyLabel(coverage: DataCoverage): string {
  if (!coverage.valuation_start || !coverage.valuation_end || coverage.valuation_observation_count < 2) {
    return "sparse source data";
  }
  const days =
    (new Date(coverage.valuation_end).getTime() - new Date(coverage.valuation_start).getTime()) /
    (1000 * 60 * 60 * 24) /
    (coverage.valuation_observation_count - 1);
  if (days > 80) return "quarterly source data";
  if (days > 25) return "monthly source data";
  if (days > 5) return "weekly source data";
  return "daily source data";
}
