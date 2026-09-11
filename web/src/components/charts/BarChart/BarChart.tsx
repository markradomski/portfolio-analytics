import { useMemo, useState } from "react";
import * as d3 from "d3";

import { formatMoney } from "../../../formatting/money";
import { Axis } from "../Axis/Axis";
import { ChartTooltip } from "../ChartTooltip/ChartTooltip";
import styles from "./BarChart.module.css";

export interface BarDatum {
  label: string;
  value: string; // API-provided figure, plotted as-is
  tone?: "positive" | "negative" | "neutral";
}

export interface BarChartProps {
  data: BarDatum[];
  width: number;
  height: number;
  valueLabel?: string;
}

const MARGIN = { top: 16, right: 16, bottom: 28, left: 64 };

/** Calendar-period and income-timeline chart primitive (sec 19, 26): one bar
 * per period, coloured by sign when the caller supplies a tone (e.g.
 * positive/negative annual return) or a single accent when it doesn't
 * (income, which has no "negative" side). */
export function BarChart({ data, width, height, valueLabel = "Value" }: BarChartProps) {
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const xScale = useMemo(
    () => d3.scaleBand().domain(data.map((d) => d.label)).range([0, innerWidth]).padding(0.3),
    [data, innerWidth],
  );
  const yScale = useMemo(() => {
    const values = data.map((d) => Number(d.value));
    const [min, max] = [Math.min(0, ...values), Math.max(0, ...values)];
    return d3.scaleLinear().domain([min, max]).nice().range([innerHeight, 0]);
  }, [data, innerHeight]);

  const zeroY = yScale(0);
  const toneColor = { positive: "var(--color-positive)", negative: "var(--color-negative)", neutral: "var(--color-accent)" };

  return (
    <svg width={width} height={height}>
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        <Axis scale={yScale} orientation="left" tickCount={5} grid gridLength={innerWidth}
              tickFormat={(v) => formatMoney(String(v))} />
        <Axis scale={xScale} orientation="bottom" transform={`translate(0,${innerHeight})`} />

        {data.map((d, i) => {
          const value = Number(d.value);
          const barY = Math.min(zeroY, yScale(value));
          const barHeight = Math.abs(yScale(value) - zeroY);
          const x = xScale(d.label) ?? 0;
          return (
            <rect
              key={d.label}
              x={x}
              y={barY}
              width={xScale.bandwidth()}
              height={Math.max(barHeight, 1)}
              fill={toneColor[d.tone ?? (value >= 0 ? "positive" : "negative")]}
              opacity={hoveredIndex === null || hoveredIndex === i ? 1 : 0.4}
              onPointerEnter={() => setHoveredIndex(i)}
              onPointerLeave={() => setHoveredIndex(null)}
            />
          );
        })}
      </g>

      {hoveredIndex !== null && (
        <foreignObject x={0} y={0} width={width} height={height} style={{ overflow: "visible", pointerEvents: "none" }}>
          <ChartTooltip
            x={MARGIN.left + (xScale(data[hoveredIndex].label) ?? 0) + xScale.bandwidth() / 2}
            y={MARGIN.top}
            containerWidth={width}
          >
            <div className={styles.label}>{data[hoveredIndex].label}</div>
            <div className={styles.value}>{valueLabel} {formatMoney(data[hoveredIndex].value)}</div>
          </ChartTooltip>
        </foreignObject>
      )}
    </svg>
  );
}
