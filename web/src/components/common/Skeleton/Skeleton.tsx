import styles from "./Skeleton.module.css";

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  radius?: "small" | "medium" | "large";
}

/** Sec 37: every API-backed view gets a deliberate loading placeholder --
 * never a blank screen, and never a fake financial figure shown while
 * loading. This renders shape only, no numbers. */
export function Skeleton({ width = "100%", height = "1em", radius = "small" }: SkeletonProps) {
  return (
    <span
      className={styles.skeleton}
      style={{ width, height, borderRadius: `var(--radius-${radius})` }}
      aria-hidden="true"
    />
  );
}

export function ChartSkeleton({ height = 320 }: { height?: number }) {
  return (
    <div className={styles.chartSkeleton} style={{ height }} aria-hidden="true">
      <Skeleton height="100%" radius="medium" />
    </div>
  );
}
