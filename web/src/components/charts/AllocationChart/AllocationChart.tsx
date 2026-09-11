import { useMemo, useState } from "react";

import { formatMoney, formatPercentPlain } from "../../../formatting/money";
import styles from "./AllocationChart.module.css";

export interface AllocationSegment {
  key: string;
  label: string;
  value: string; // market value, API-provided
  weight: string | null; // allocation_pct, API-provided -- null means unavailable, never treated as 0
  /** Distinguishes a genuine classification from an absent one (sec 6):
   * "unknown" renders visually distinct from a real category, never
   * silently folded into "Other". */
  kind?: "known" | "unknown";
}

export interface AllocationChartProps {
  segments: AllocationSegment[];
  width: number;
}

const PALETTE = [
  "var(--chart-series-1)", "var(--chart-series-2)", "var(--chart-series-3)",
  "var(--chart-series-4)", "var(--chart-series-5)", "var(--chart-series-6)",
];

/**
 * A single proportional stacked bar plus a legend/table -- chosen over a pie
 * chart for information density (sec 17: "avoid excessive use of pie
 * charts... choose based on information density"). Each segment's own label
 * carries its exact value and weight, so precision isn't lost to the visual
 * encoding the way a pie chart's angle comparison loses it.
 */
export function AllocationChart({ segments, width }: AllocationChartProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const total = useMemo(() => segments.reduce((sum, s) => sum + Number(s.value || 0), 0), [segments]);

  let cursor = 0;
  const withOffsets = segments.map((s, i) => {
    const w = total > 0 ? (Number(s.value) / total) * width : 0;
    const seg = { ...s, x: cursor, barWidth: w, color: PALETTE[i % PALETTE.length] };
    cursor += w;
    return seg;
  });

  return (
    <div>
      <svg width={width} height={28} role="img" aria-label="Portfolio allocation, proportional to market value">
        {withOffsets.map((s) => (
          <rect
            key={s.key}
            x={s.x}
            y={0}
            width={Math.max(s.barWidth, 0)}
            height={28}
            fill={s.kind === "unknown" ? "var(--color-unknown)" : s.color}
            opacity={hovered === null || hovered === s.key ? 1 : 0.4}
            onPointerEnter={() => setHovered(s.key)}
            onPointerLeave={() => setHovered(null)}
          />
        ))}
      </svg>
      <ul className={styles.legend}>
        {withOffsets.map((s) => (
          <li
            key={s.key}
            className={styles.legendItem}
            onPointerEnter={() => setHovered(s.key)}
            onPointerLeave={() => setHovered(null)}
            style={{ opacity: hovered === null || hovered === s.key ? 1 : 0.5 }}
          >
            <span
              className={styles.swatch}
              style={{ background: s.kind === "unknown" ? "var(--color-unknown)" : s.color }}
              aria-hidden="true"
            />
            <span className={styles.label}>{s.label}</span>
            <span className={styles.weight}>
              {s.weight === null ? "Unavailable" : formatPercentPlain(s.weight)}
            </span>
            <span className={styles.value}>{formatMoney(s.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
