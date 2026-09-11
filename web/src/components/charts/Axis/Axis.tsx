import { useEffect, useRef } from "react";
import * as d3 from "d3";

export interface AxisProps<Domain extends d3.AxisDomain> {
  scale: d3.AxisScale<Domain>;
  orientation: "bottom" | "left";
  transform?: string;
  tickCount?: number;
  tickFormat?: (value: Domain) => string;
  grid?: boolean;
  gridLength?: number;
}

/** A thin React wrapper around d3-axis. D3 owns the tick generation, scale
 * math and path geometry (sec 2); React owns only when this effect re-runs.
 * Rendered as a plain <g>, updated imperatively via d3.select -- this is the
 * one sanctioned place a D3 selection touches the DOM directly, since
 * d3-axis has no declarative React equivalent worth reinventing.
 *
 * Generic over the scale's own domain type (number/Date/string) rather than
 * the AxisDomain union directly -- d3's scaleLinear/scaleTime/scaleBand
 * each have a narrower, mutually-incompatible concrete type than the union,
 * which real @types/d3 (added to close the Phase 5.1-5.4 build-mode gap)
 * now enforces structurally where the previous untyped `d3: any` import
 * silently accepted anything. */
export function Axis<Domain extends d3.AxisDomain>({
  scale, orientation, transform, tickCount, tickFormat, grid, gridLength,
}: AxisProps<Domain>) {
  const ref = useRef<SVGGElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const axis = orientation === "bottom" ? d3.axisBottom(scale) : d3.axisLeft(scale);
    if (tickCount) axis.ticks(tickCount);
    if (tickFormat) axis.tickFormat(tickFormat as unknown as (d: Domain, i: number) => string);
    if (grid) axis.tickSizeInner(-(gridLength ?? 0)).tickSizeOuter(0);

    const selection = d3.select(ref.current);
    selection.call(axis as never);
    selection.select(".domain").attr("stroke", "var(--chart-axis)");
    selection.selectAll(".tick line").attr("stroke", grid ? "var(--chart-grid)" : "var(--chart-axis)");
    selection.selectAll(".tick text")
      .attr("fill", "var(--color-text-muted)")
      .attr("font-size", "11px")
      .attr("font-family", "var(--font-body)");
  }, [scale, orientation, tickCount, tickFormat, grid, gridLength]);

  return <g ref={ref} transform={transform} />;
}
