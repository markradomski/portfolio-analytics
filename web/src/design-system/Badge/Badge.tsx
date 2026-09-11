import type { ReactNode } from "react";

import styles from "./Badge.module.css";

export type BadgeTone =
  | "positive" | "negative" | "warning" | "neutral" | "accent"
  | "quality-actual" | "quality-calculated" | "quality-estimated"
  | "quality-limited" | "quality-unavailable";

export interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  /** Renders a small dot alongside the text -- an additional, non-colour
   * visual cue, since colour alone must never carry the meaning (sec 32). */
  withDot?: boolean;
}

export function Badge({ tone = "neutral", children, withDot = true }: BadgeProps) {
  const toneClass = styles[tone as keyof typeof styles];
  return (
    <span className={`${styles.badge} ${toneClass}`}>
      {withDot && <span className={styles.dot} aria-hidden="true" />}
      {children}
    </span>
  );
}
