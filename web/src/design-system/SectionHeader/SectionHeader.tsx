import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import styles from "./SectionHeader.module.css";

export interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  /** An understated "View X →" navigation affordance (Overview sec 19) --
   * a route to the deeper analysis screen this section summarises. */
  viewAllHref?: string;
  viewAllLabel?: string;
  action?: ReactNode;
}

/** The recurring section label used across the Overview (and, going
 * forward, any screen with more than one grouped block): a small-caps
 * title, an optional one-line subtitle, and an understated link onward to
 * the full analysis screen. Kept in the design system rather than the
 * Overview page because every one of Performance/Holdings/Income/
 * Contributions repeats this exact shape (sec 27: "only add if it
 * demonstrates clear reuse"). */
export function SectionHeader({ title, subtitle, viewAllHref, viewAllLabel, action }: SectionHeaderProps) {
  return (
    <div className={styles.wrap}>
      <div>
        <h2 className={styles.title}>{title}</h2>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
      <div className={styles.actions}>
        {action}
        {viewAllHref && (
          <Link to={viewAllHref} className={styles.link}>
            {viewAllLabel ?? "View all"} <span aria-hidden="true">→</span>
          </Link>
        )}
      </div>
    </div>
  );
}
