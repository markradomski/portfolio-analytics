import { useMemo } from "react";
import * as d3 from "d3";

import { formatDate, formatPercentSigned } from "../../../formatting/money";
import { Axis } from "../Axis/Axis";
import { ChartTooltip } from "../ChartTooltip/ChartTooltip";
import { useNearestPoint } from "../../../hooks/useNearestPoint";
import styles from "./DrawdownChart.module.css";

export interface DrawdownPoint {
  date: string;
  drawdownPct: string | null; // API-provided distance from high-water mark, never computed here
}

export interface DrawdownEpisodeMarker {
  peakDate: string;
  troughDate: string;
  recoveryDate: string | null;
}

export interface DrawdownChartProps {
  data: DrawdownPoint[];
  episodes?: DrawdownEpisodeMarker[];
  width: number;
  height: number;
}

const MARGIN = { top: 16, right: 16, bottom: 28, left: 56 };

/** Plots the flow-neutral drawdown series Phase 4 already computed (sec 23:
 * "do not calculate high-water marks in the frontend") -- this component
 * only draws the numbers it's given and shades the peak-to-recovery window
 * for each episode Phase 4 identified. */
export function DrawdownChart({ data, episodes = [], width, height }: DrawdownChartProps) {
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;

  const parsed = useMemo(
    () => data.map((d) => ({ ...d, dateObj: new Date(d.date), num: d.drawdownPct === null ? null : Number(d.drawdownPct) })),
    [data],
  );
  const valued = useMemo(() => parsed.filter((d) => d.num !== null), [parsed]);

  const xScale = useMemo(
    () => d3.scaleTime().domain(d3.extent(parsed, (d) => d.dateObj) as [Date, Date]).range([0, innerWidth]),
    [parsed, innerWidth],
  );
  const yScale = useMemo(() => {
    const min = d3.min(valued, (d) => d.num as number) ?? -0.1;
    return d3.scaleLinear().domain([Math.min(min, 0) * 1.1, 0]).range([innerHeight, 0]);
  }, [valued, innerHeight]);

  const area = useMemo(
    () => d3.area<(typeof parsed)[number]>()
      .defined((d) => d.num !== null)
      .x((d) => xScale(d.dateObj)).y0(yScale(0)).y1((d) => yScale(d.num as number))
      .curve(d3.curveMonotoneX),
    [xScale, yScale],
  );
  const line = useMemo(
    () => d3.line<(typeof parsed)[number]>()
      .defined((d) => d.num !== null)
      .x((d) => xScale(d.dateObj)).y((d) => yScale(d.num as number))
      .curve(d3.curveMonotoneX),
    [xScale, yScale],
  );

  const { hovered, onPointerMove, onPointerLeave } = useNearestPoint(valued, (d) => d.dateObj, xScale);

  return (
    <svg width={width} height={height}>
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        <Axis scale={yScale} orientation="left" tickCount={4} grid gridLength={innerWidth}
              tickFormat={(v) => formatPercentSigned(String(v))} />
        <Axis scale={xScale} orientation="bottom" transform={`translate(0,${innerHeight})`} tickCount={6} />

        {episodes.map((episode, i) => {
          const x1 = xScale(new Date(episode.peakDate));
          const x2 = xScale(new Date(episode.recoveryDate ?? episode.troughDate));
          return <rect key={i} x={x1} y={0} width={Math.max(x2 - x1, 1)} height={innerHeight} fill="var(--color-negative-bg)" />;
        })}

        <path d={area(parsed) ?? undefined} fill="var(--color-negative)" fillOpacity={0.12} />
        <path d={line(parsed) ?? undefined} fill="none" stroke="var(--color-negative)" strokeWidth={1.5} />
        <line x1={0} x2={innerWidth} y1={yScale(0)} y2={yScale(0)} stroke="var(--chart-axis)" strokeWidth={1} />

        <rect width={innerWidth} height={innerHeight} fill="transparent" onPointerMove={onPointerMove} onPointerLeave={onPointerLeave} />
      </g>

      {hovered && (
        <foreignObject x={0} y={0} width={width} height={height} style={{ overflow: "visible", pointerEvents: "none" }}>
          <ChartTooltip x={xScale(hovered.dateObj) + MARGIN.left} y={MARGIN.top} containerWidth={width}>
            <div className={styles.date}>{formatDate(hovered.date)}</div>
            <div className={styles.value}>{formatPercentSigned(hovered.drawdownPct)} from high</div>
          </ChartTooltip>
        </foreignObject>
      )}
    </svg>
  );
}
