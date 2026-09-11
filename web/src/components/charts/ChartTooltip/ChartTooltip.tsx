import type { ReactNode } from "react";

import styles from "./ChartTooltip.module.css";

export interface ChartTooltipProps {
  x: number;
  y: number;
  containerWidth: number;
  children: ReactNode;
}

/** The one tooltip shape every chart uses (sec 36): positioned relative to
 * the hovered point, flipped to stay inside the container near the right
 * edge. Content (date/value/data-quality/context) is supplied by the
 * caller -- this component only handles placement. */
export function ChartTooltip({ x, y, containerWidth, children }: ChartTooltipProps) {
  const flip = x > containerWidth - 160;
  return (
    <div
      className={styles.tooltip}
      style={{ left: flip ? undefined : x + 12, right: flip ? containerWidth - x + 12 : undefined, top: Math.max(0, y - 12) }}
    >
      {children}
    </div>
  );
}
