import type { ReactNode } from "react";

import { sign } from "../../formatting/money";
import styles from "./MetricValue.module.css";

export interface MetricValueProps {
  label: string;
  /** Already-formatted display string (formatMoney/formatPercentSigned/etc)
   * -- this component never formats a raw API value itself, keeping the
   * "where does formatting happen" boundary in one place. */
  value: string | null;
  /** Drives colour by sign, using the same classification formatting/money's
   * sign() applies -- pass the *raw* API value here, not the display string,
   * since sign() needs the actual number. */
  rawValue?: string | null;
  size?: "default" | "large";
  meta?: ReactNode;
  /** When set, `value` is ignored and an explicit unavailable message is
   * shown instead -- never a bare "N/A" (sec 10). */
  unavailableReason?: string;
}

export function MetricValue({ label, value, rawValue, size = "default", meta, unavailableReason }: MetricValueProps) {
  const toneClass = rawValue ? styles[sign(rawValue)] : "";
  return (
    <div className={styles.wrap}>
      <span className={styles.label}>{label}</span>
      {unavailableReason ? (
        <span className={styles.unavailable}>{unavailableReason}</span>
      ) : (
        <span className={[styles.value, size === "large" ? styles.large : "", toneClass].join(" ")}>
          {value ?? "—"}
        </span>
      )}
      {meta && <div className={styles.meta}>{meta}</div>}
    </div>
  );
}
