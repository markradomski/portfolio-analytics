import { useMemo } from "react";
import * as d3 from "d3";

import { formatDate, formatMoney, sign } from "../../../formatting/money";
import type { ValuationStatus } from "../../../api/types";
import { Axis } from "../Axis/Axis";
import { ChartTooltip } from "../ChartTooltip/ChartTooltip";
import { Crosshair } from "../Crosshair/Crosshair";
import { useNearestPoint } from "../../../hooks/useNearestPoint";
import styles from "./TimeSeriesChart.module.css";

export interface TimeSeriesPoint {
  date: string; // ISO
  value: string | null; // null = genuinely unavailable, never plotted as zero
  quality: ValuationStatus;
}

export interface FlowMarker {
  date: string;
  amount: string; // positive = contribution, negative = withdrawal
}

export interface TimeSeriesChartProps {
  data: TimeSeriesPoint[];
  flows?: FlowMarker[];
  width: number;
  height: number;
  valueLabel?: string;
  /** How to render a raw value for the axis and tooltip -- defaults to
   * currency, since every existing caller plots a dollar value. A screen
   * plotting a non-money series (Performance's return index, sec 10: never
   * present that as though it were a dollar curve) passes its own
   * formatter rather than this component silently mislabelling it. */
  formatValue?: (value: string) => string;
}

const MARGIN = { top: 16, right: 16, bottom: 28, left: 64 };

function qualityLabel(quality: ValuationStatus): string {
  switch (quality) {
    case "actual": return "Vanguard reported";
    case "calculated": return "Priced this date";
    case "estimated": return "Carried forward from last known price";
    case "unavailable": return "No price available";
    default: return quality;
  }
}

/**
 * The primary historical chart primitive (sec 8-9): plots a value series
 * with the data-quality distinction visible in the line itself -- an
 * ESTIMATED (carried-forward) segment renders lighter and dashed, never
 * indistinguishable from an ACTUAL/CALCULATED one. A null value breaks the
 * line rather than being plotted as zero (never fabricates a point).
 *
 * Contributions/withdrawals overlay as small markers above/below the line,
 * visually distinct from the line itself -- so "I added money" is never
 * confused with "the portfolio grew" (sec 47).
 */
export function TimeSeriesChart({ data, flows = [], width, height, valueLabel = "Value", formatValue = formatMoney }: TimeSeriesChartProps) {
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;

  const parsed = useMemo(
    () => data.map((d) => ({ ...d, dateObj: new Date(d.date), num: d.value === null ? null : Number(d.value) })),
    [data],
  );
  const valued = useMemo(() => parsed.filter((d) => d.num !== null), [parsed]);

  const xScale = useMemo(
    () => d3.scaleTime().domain(d3.extent(parsed, (d) => d.dateObj) as [Date, Date]).range([0, innerWidth]),
    [parsed, innerWidth],
  );
  const yScale = useMemo(() => {
    const [min, max] = d3.extent(valued, (d) => d.num as number);
    const pad = ((max ?? 0) - (min ?? 0)) * 0.08 || 1;
    return d3.scaleLinear().domain([(min ?? 0) - pad, (max ?? 0) + pad]).nice().range([innerHeight, 0]);
  }, [valued, innerHeight]);

  const line = useMemo(
    () => d3.line<(typeof parsed)[number]>()
      .defined((d) => d.num !== null)
      .x((d) => xScale(d.dateObj))
      .y((d) => yScale(d.num as number))
      .curve(d3.curveMonotoneX),
    [xScale, yScale],
  );
  const area = useMemo(
    () => d3.area<(typeof parsed)[number]>()
      .defined((d) => d.num !== null)
      .x((d) => xScale(d.dateObj))
      .y0(innerHeight)
      .y1((d) => yScale(d.num as number))
      .curve(d3.curveMonotoneX),
    [xScale, yScale, innerHeight],
  );

  // Split into contiguous runs by quality so an estimated stretch can be
  // styled differently without breaking the visual continuity of the line.
  const segments = useMemo(() => {
    const out: { quality: ValuationStatus | "gap"; points: typeof parsed }[] = [];
    for (const point of parsed) {
      const key = point.num === null ? "gap" : point.quality;
      const last = out[out.length - 1];
      if (last && last.quality === key) last.points.push(point);
      else out.push({ quality: key, points: [point] });
    }
    return out;
  }, [parsed]);

  const { hovered, onPointerMove, onPointerLeave, onFocus, onBlur, onKeyDown } = useNearestPoint(
    valued, (d) => d.dateObj, xScale,
  );

  return (
    <>
    <svg width={width} height={height} role="group" aria-label={`${valueLabel} over time, interactive chart`}>
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        <Axis scale={yScale} orientation="left" tickCount={5} grid gridLength={innerWidth}
              tickFormat={(v) => formatValue(String(v))} />
        <Axis scale={xScale} orientation="bottom" transform={`translate(0,${innerHeight})`} tickCount={6} />

        {segments.map((segment, i) => {
          if (segment.quality === "gap") return null;
          const dashed = segment.quality === "estimated";
          // A segment with only one point (a single day of a given quality
          // surrounded by gaps or a quality change either side) has nothing
          // to draw a line between -- rendered as a dot instead of being
          // silently dropped, since every real observation must appear
          // somewhere in the chart.
          if (segment.points.length < 2) {
            const point = segment.points[0];
            if (point.num === null) return null;
            return (
              <circle
                key={i}
                data-role="series-point"
                cx={xScale(point.dateObj)}
                cy={yScale(point.num)}
                r={3}
                fill="var(--color-accent)"
                fillOpacity={dashed ? 0.55 : 1}
              />
            );
          }
          return (
            <g key={i}>
              <path data-role="series-area" d={area(segment.points) ?? undefined} fill="var(--color-accent)" fillOpacity={dashed ? 0.04 : 0.08} />
              <path
                data-role="series-line"
                data-quality={segment.quality}
                d={line(segment.points) ?? undefined}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth={dashed ? 1.25 : 2}
                strokeOpacity={dashed ? 0.55 : 1}
                strokeDasharray={dashed ? "3,3" : undefined}
              />
            </g>
          );
        })}

        {flows.map((flow, i) => {
          const x = xScale(new Date(flow.date));
          if (x < 0 || x > innerWidth) return null;
          const isContribution = Number(flow.amount) > 0;
          return (
            <g key={i} transform={`translate(${x},0)`}>
              <line
                y1={isContribution ? innerHeight : 0} y2={isContribution ? innerHeight - 8 : 8}
                stroke={isContribution ? "var(--color-positive)" : "var(--color-negative)"}
                strokeWidth={2}
              />
            </g>
          );
        })}

        <rect
          className={styles.interactionLayer}
          width={innerWidth}
          height={innerHeight}
          fill="transparent"
          tabIndex={0}
          aria-label={`${valueLabel} chart data points. Use the left and right arrow keys to move between dates.`}
          onPointerMove={onPointerMove}
          onPointerLeave={onPointerLeave}
          onFocus={onFocus}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
        />

        {hovered && (
          <Crosshair x={xScale(hovered.dateObj)} height={innerHeight}
                     y={hovered.num !== null ? yScale(hovered.num) : undefined} />
        )}
      </g>

      {hovered && (
        <foreignObject x={0} y={0} width={width} height={height} style={{ overflow: "visible", pointerEvents: "none" }}>
          <ChartTooltip x={xScale(hovered.dateObj) + MARGIN.left} y={MARGIN.top} containerWidth={width}>
            <div className={styles.date}>{formatDate(hovered.date)}</div>
            <div className={styles.value} data-sign={sign(hovered.value)}>
              {valueLabel} {hovered.value !== null ? formatValue(hovered.value) : "—"}
            </div>
            <div className={styles.quality}>
              {qualityLabel(hovered.quality)}
            </div>
          </ChartTooltip>
        </foreignObject>
      )}
    </svg>
    <p className={styles.srOnly} aria-live="polite">
      {hovered
        ? `${formatDate(hovered.date)}: ${valueLabel} ${hovered.value !== null ? formatValue(hovered.value) : "not available"}. ${qualityLabel(hovered.quality)}.`
        : ""}
    </p>
    </>
  );
}
