import { useMemo } from "react";
import * as d3 from "d3";

import { formatDate, formatPercentPlain } from "../../../formatting/money";
import { Axis } from "../Axis/Axis";
import { ChartTooltip } from "../ChartTooltip/ChartTooltip";
import { Crosshair } from "../Crosshair/Crosshair";
import { useNearestPoint } from "../../../hooks/useNearestPoint";
import type { AllocationHistoryPoint } from "../../../api/types";
import styles from "./AllocationHistoryChart.module.css";

export interface AllocationHistoryChartProps {
  /** history/allocation_history() rows, already computed by the backend --
   * this component stacks and scales them for display, it never derives a
   * weight or a total itself. */
  data: AllocationHistoryPoint[];
  width: number;
  height: number;
  categoryLabels?: Record<string, string>;
}

const PALETTE = [
  "var(--chart-series-1)", "var(--chart-series-2)", "var(--chart-series-3)",
  "var(--chart-series-4)", "var(--chart-series-5)", "var(--chart-series-6)",
];
const MARGIN = { top: 16, right: 16, bottom: 28, left: 40 };

/**
 * Sec 13-14: a 100%-stacked area chart of allocation over time, built as
 * its own small reusable primitive since none of the existing charts plot
 * a set of proportions through time. Every band's height at every date is
 * exactly the `allocation_pct` value the backend already computed for
 * that category on that date -- d3.stack only lays the already-known
 * proportions out for drawing, it never computes a proportion itself.
 * Categories are keyed by name (never "Other" collapsed silently) and a
 * bucket the API marks with no observation at all is simply absent from
 * the stack that date, not filled in as zero.
 */
export function AllocationHistoryChart({ data, width, height, categoryLabels = {} }: AllocationHistoryChartProps) {
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;

  const categories = useMemo(() => {
    const keys = new Set<string>();
    for (const row of data) for (const key of Object.keys(row.allocation_pct ?? {})) keys.add(key);
    return Array.from(keys).sort();
  }, [data]);

  const parsed = useMemo(
    () => data.map((row) => ({
      date: new Date(row.date),
      raw: row,
      ...Object.fromEntries(categories.map((c) => [c, row.allocation_pct?.[c] ? Number(row.allocation_pct[c]) : 0])),
    })),
    [data, categories],
  );

  const stackGen = useMemo(() => d3.stack<(typeof parsed)[number]>().keys(categories), [categories]);
  const series = useMemo(() => (parsed.length ? stackGen(parsed) : []), [stackGen, parsed]);

  const xScale = useMemo(
    () => d3.scaleTime().domain(d3.extent(parsed, (d) => d.date) as [Date, Date]).range([0, innerWidth]),
    [parsed, innerWidth],
  );
  const yScale = useMemo(() => d3.scaleLinear().domain([0, 1]).range([innerHeight, 0]), [innerHeight]);

  const area = useMemo(
    () => d3.area<d3.SeriesPoint<(typeof parsed)[number]>>()
      .x((d) => xScale(d.data.date))
      .y0((d) => yScale(d[0]))
      .y1((d) => yScale(d[1]))
      .curve(d3.curveStepAfter),
    [xScale, yScale],
  );

  const { hovered, onPointerMove, onPointerLeave, onFocus, onBlur, onKeyDown } = useNearestPoint(
    parsed, (d) => d.date, xScale,
  );

  if (parsed.length === 0) {
    return <p className={styles.empty}>No allocation history available yet.</p>;
  }

  return (
    <>
    <svg width={width} height={height} role="group" aria-label="Allocation over time, interactive chart">
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        <Axis scale={yScale} orientation="left" tickCount={4} grid gridLength={innerWidth}
              tickFormat={(v) => formatPercentPlain(String(v))} />
        <Axis scale={xScale} orientation="bottom" transform={`translate(0,${innerHeight})`} tickCount={6} />

        {series.map((s, i) => (
          <path key={s.key} data-role="allocation-band" data-category={s.key}
                d={area(s) ?? undefined} fill={PALETTE[i % PALETTE.length]} fillOpacity={0.85} />
        ))}

        <rect
          className={styles.interactionLayer}
          width={innerWidth} height={innerHeight} fill="transparent"
          tabIndex={0}
          aria-label="Allocation chart data points. Use the left and right arrow keys to move between dates."
          onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}
          onFocus={onFocus} onBlur={onBlur} onKeyDown={onKeyDown}
        />

        {hovered && <Crosshair x={xScale(hovered.date)} height={innerHeight} />}
      </g>

      {hovered && (
        <foreignObject x={0} y={0} width={width} height={height} style={{ overflow: "visible", pointerEvents: "none" }}>
          <ChartTooltip x={xScale(hovered.date) + MARGIN.left} y={MARGIN.top} containerWidth={width}>
            <div className={styles.date}>{formatDate(hovered.raw.date)}</div>
            {categories.map((c) => {
              const pct = hovered.raw.allocation_pct?.[c];
              if (pct === undefined) return null;
              return (
                <div key={c} className={styles.row}>
                  <span>{categoryLabels[c] ?? c}</span>
                  <span>{pct === null ? "Unavailable" : formatPercentPlain(pct)}</span>
                </div>
              );
            })}
          </ChartTooltip>
        </foreignObject>
      )}
    </svg>
    <p className={styles.srOnly} aria-live="polite">
      {hovered
        ? `${formatDate(hovered.raw.date)}: ${categories
            .map((c) => {
              const pct = hovered.raw.allocation_pct?.[c];
              return pct === undefined ? null : `${categoryLabels[c] ?? c} ${pct === null ? "unavailable" : formatPercentPlain(pct)}`;
            })
            .filter(Boolean)
            .join(", ")}.`
        : ""}
    </p>
    </>
  );
}
