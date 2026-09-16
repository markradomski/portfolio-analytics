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
 * caller -- this component only handles placement.
 *
 * The flip threshold (160px) assumes a roughly 140-150px-wide tooltip --
 * true most of the time, but a narrow phone-width chart plus a
 * longer-than-usual row (a big dollar figure, a longer label) can render
 * wider than that. Capping `maxWidth` to the container's *own* width isn't
 * enough on its own: a right-anchored (flipped) tooltip narrower than the
 * whole container can still poke past the container's opposite (left) edge
 * if it's simply wider than the gap between its anchor point and that
 * edge. `maxWidth` is instead computed per side, from the anchor point to
 * the *unanchored* edge -- exactly the space actually available -- so
 * whichever edge is anchored, the other can never be exceeded either. */
export function ChartTooltip({ x, y, containerWidth, children }: ChartTooltipProps) {
  const flip = x > containerWidth - 160;
  const maxWidth = flip ? Math.max(120, x - 12) : Math.max(120, containerWidth - x - 12);
  return (
    <div
      className={styles.tooltip}
      style={{
        left: flip ? undefined : x + 12,
        right: flip ? containerWidth - x + 12 : undefined,
        top: Math.max(0, y - 12),
        maxWidth,
      }}
    >
      {children}
    </div>
  );
}
