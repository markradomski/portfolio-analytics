import { Badge } from "../../../design-system/Badge/Badge";
import styles from "./UnavailableMetric.module.css";

export interface UnavailableMetricProps {
  title: string;
  reason: string;
  /** An optional call to action -- e.g. "Add a benchmark" -- when the gap is
   * something the user could actually resolve, distinct from a gap that's
   * inherent to the source data. */
  action?: React.ReactNode;
}

/** Sec 10/38/41: an unavailable metric is never a bare "N/A". Always a
 * title, a plain-language reason sourced from the API's own `reason` field,
 * and optionally a way forward. */
export function UnavailableMetric({ title, reason, action }: UnavailableMetricProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <span className={styles.title}>{title}</span>
        <Badge tone="quality-unavailable" withDot={false}>Unavailable</Badge>
      </div>
      <p className={styles.reason}>{reason}</p>
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
