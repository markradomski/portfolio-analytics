import { useMemo } from "react";
import * as d3 from "d3";

import { formatDate, formatMoney, formatMoneyCompact, formatMoneySigned, sign } from "../../../formatting/money";
import type { CashFlowEvent, PortfolioGrowthPoint } from "../../../api/types";
import { Axis } from "../Axis/Axis";
import { ChartTooltip } from "../ChartTooltip/ChartTooltip";
import { Crosshair } from "../Crosshair/Crosshair";
import { useNearestPoint } from "../../../hooks/useNearestPoint";
import styles from "./BalanceDecompositionChart.module.css";

export interface BalanceDecompositionChartProps {
  /** Already sliced to the selected period by the caller (sec 15: the same
   * "fetch once, unbounded; slice client-side by period" convention every
   * other period-controlled chart in this app uses -- see
   * usePortfolioGrowth's own doc comment). */
  points: PortfolioGrowthPoint[];
  width: number;
  height: number;
}

const MARGIN = { top: 16, right: 16, bottom: 28, left: 72 };

interface Parsed {
  date: Date;
  dateStr: string;
  value: number | null;
  netContrib: number;
  investmentGain: number | null;
  /** This day's own gain/loss (not cumulative) -- see PortfolioGrowthPoint
   * .period_investment_gain's own docstring for the formula. Drives the
   * Investment Gain (green, above zero) / Investment Loss (red, below
   * zero) areas -- the two are mutually exclusive at every point, since
   * this is a single signed number. */
  periodGain: number | null;
  events: CashFlowEvent[];
  raw: PortfolioGrowthPoint;
}

/** A minimum on-screen width (px) for a gain/loss day that has no adjacent
 * same-sign day either side -- an isolated single-point "run" has no
 * second x-position to build a real d3.area shape from, so it renders as
 * a narrow bar instead of vanishing. Genuinely common for this dataset:
 * investment gain/loss only changes on an actual priced date, which can
 * be quarters apart, surrounded by flat (zero-gain) carried-forward days. */
const ISOLATED_BAR_WIDTH = 5;

/**
 * The advanced "Balance decomposition" chart on the Performance screen
 * (Step 9A Part B). This is the detailed, analytical sibling of the
 * Overview's simple PortfolioGrowthChart: it lived on Overview through
 * Step 9 and moved here in Step 9A, where Overview took the pared-back
 * wealth snapshot and Performance kept the full decomposition -- event
 * markers, per-period gain/loss, a rich hover tooltip and keyboard
 * navigation. Four visually distinct elements, in ascending prominence:
 *
 * 1. Contributions & Withdrawals -- a subtle light-blue area anchored to
 *    the zero baseline (never floating between two data points): fills
 *    upward from 0 when net contributions are positive, downward from 0
 *    when negative. This communicates *cash moved*, independent of
 *    performance -- it is not a portfolio-value line and must never be
 *    mistaken for one.
 * 2. Investment Gain / Investment Loss -- this day's own gain or loss
 *    (period_investment_gain, not the cumulative investment_gain), also
 *    anchored to zero: solid bright green above zero on a gain day, solid
 *    bright red below zero on a loss day. The two are mutually exclusive
 *    at every point (one signed number can only be one or the other) and
 *    are never merged into one "Investment Gain/Loss" legend entry -- a
 *    viewer must be able to tell gain from loss without hovering.
 * 3. Net Contributions -- a solid, subtle reference line.
 * 4. Total Balance -- the dominant line, drawn last (on top).
 *
 * A third "growth" *line* was deliberately not added -- the Investment
 * Gain/Loss areas already show that story; a persistent <ChartLegend>
 * names every element so none of this depends on hover to be understood.
 *
 * Every number plotted is read directly from a PortfolioGrowthPoint --
 * this component sorts, scales and draws; it performs no financial
 * calculation of its own (sec 1). period_investment_gain itself is
 * computed once, server-side, in src/analytics/growth.py.
 */
export function BalanceDecompositionChart({ points, width, height }: BalanceDecompositionChartProps) {
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;

  const parsed = useMemo<Parsed[]>(() => points.map((p) => ({
    date: new Date(p.date),
    dateStr: p.date,
    value: p.portfolio_value === null ? null : Number(p.portfolio_value),
    netContrib: Number(p.net_contributions),
    investmentGain: p.investment_gain === null ? null : Number(p.investment_gain),
    periodGain: p.period_investment_gain === null || p.period_investment_gain === undefined
      ? null : Number(p.period_investment_gain),
    events: p.cash_flow_events ?? [],
    raw: p,
  })), [points]);

  const valued = useMemo(() => parsed.filter((d) => d.value !== null), [parsed]);
  const events = useMemo(() => parsed.filter((d) => d.events.length > 0), [parsed]);

  const xScale = useMemo(
    () => d3.scaleTime().domain(d3.extent(parsed, (d) => d.date) as [Date, Date]).range([0, innerWidth]),
    [parsed, innerWidth],
  );

  const yScale = useMemo(() => {
    const values = valued.flatMap((d) => [d.value as number, d.netContrib]);
    const [min, max] = d3.extent(values);
    const pad = ((max ?? 0) - (min ?? 0)) * 0.08 || 1;
    return d3.scaleLinear()
      .domain([Math.min(0, (min ?? 0) - pad), (max ?? 0) + pad])
      .nice()
      .range([innerHeight, 0]);
  }, [valued, innerHeight]);

  const balanceLine = useMemo(
    () => d3.line<Parsed>().defined((d) => d.value !== null)
      .x((d) => xScale(d.date)).y((d) => yScale(d.value as number)).curve(d3.curveMonotoneX),
    [xScale, yScale],
  );
  const contribLine = useMemo(
    () => d3.line<Parsed>().x((d) => xScale(d.date)).y((d) => yScale(d.netContrib)).curve(d3.curveMonotoneX),
    [xScale, yScale],
  );

  // Investment Gain / Investment Loss: this day's own gain or loss,
  // anchored to zero -- split into contiguous same-sign runs so each run
  // draws its own area (never one shape spanning a sign change). A run of
  // exactly one point (the common case for this dataset: gain/loss only
  // moves on an actual priced date, which can be quarters apart, with flat
  // zero-gain carried-forward days either side) has no second x-position
  // to build a real area from, so it renders as a narrow bar instead.
  const gainLossRuns = useMemo(() => {
    const runs: { sign: "gain" | "loss"; points: Parsed[]; lastIndex: number }[] = [];
    for (let i = 0; i < parsed.length; i++) {
      const d = parsed[i];
      if (d.periodGain === null || d.periodGain === 0) continue;
      const s: "gain" | "loss" = d.periodGain > 0 ? "gain" : "loss";
      const last = runs[runs.length - 1];
      if (last && last.sign === s && last.lastIndex === i - 1) {
        last.points.push(d);
        last.lastIndex = i;
      } else {
        runs.push({ sign: s, points: [d], lastIndex: i });
      }
    }
    const area = d3.area<Parsed>()
      .x((d) => xScale(d.date))
      .y0(() => yScale(0))
      .y1((d) => yScale(d.periodGain as number))
      .curve(d3.curveMonotoneX);
    return runs.map((r) => ({
      sign: r.sign,
      d: r.points.length >= 2 ? area(r.points) : null,
      bar: r.points.length === 1 ? r.points[0] : null,
    }));
  }, [parsed, xScale, yScale]);

  // Contributions & Withdrawals: always anchored to the zero baseline --
  // never the gap between two adjacent data points -- so a positive net
  // contribution visibly fills up from 0 and a negative one (more has been
  // withdrawn than contributed) fills down from 0. net_contributions is
  // never null, so this area has no gaps to define around.
  const contributionsArea = useMemo(
    () => d3.area<Parsed>()
      .x((d) => xScale(d.date))
      .y0(() => yScale(0))
      .y1((d) => yScale(d.netContrib))
      .curve(d3.curveMonotoneX),
    [xScale, yScale],
  );

  const { hovered, onPointerMove, onPointerLeave, onFocus, onBlur, onKeyDown } = useNearestPoint(
    valued, (d) => d.date, xScale,
  );

  return (
    <>
    <svg width={width} height={height} role="group" aria-label="Portfolio balance vs net contributions over time, interactive chart">
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        <Axis scale={yScale} orientation="left" tickCount={5} grid gridLength={innerWidth}
              tickFormat={(v) => formatMoneyCompact(String(v))} />
        <Axis scale={xScale} orientation="bottom" transform={`translate(0,${innerHeight})`} tickCount={6} />

        {/* Contributions & Withdrawals -- lowest layer, anchored to zero
            (sec 1/2/6): a subtle light-blue area, distinct from and less
            saturated than the Investment Returns fill above it, so it
            reads as "cash moved" rather than another balance-like series. */}
        <path data-role="contributions-area" d={contributionsArea(parsed) ?? undefined}
              fill="var(--color-accent-bg)" stroke="none" />

        {/* The zero baseline itself -- explicit and visually distinct from
            the regular gridlines, so positive/zero/negative net
            contributions are immediately apparent (sec 6). */}
        <line data-role="zero-baseline" x1={0} x2={innerWidth} y1={yScale(0)} y2={yScale(0)}
              stroke="var(--chart-axis)" strokeWidth={1} />

        {/* Investment Gain / Investment Loss -- this day's own gain or
            loss, anchored to zero, solid bright green above / solid
            bright red below (never muted, dashed or transparency-heavy):
            mutually exclusive at every point and never merged into one
            "Investment Gain/Loss" legend entry. */}
        {gainLossRuns.map((r, i) => {
          const color = r.sign === "gain" ? "var(--color-positive)" : "var(--color-negative)";
          if (r.d) {
            return (
              <path key={i} data-role={r.sign === "gain" ? "investment-gain-area" : "investment-loss-area"}
                    d={r.d} fill={color} fillOpacity={0.9} stroke="none" />
            );
          }
          // An isolated single day with no adjacent same-sign day either
          // side -- rendered as a narrow bar rather than vanishing (a
          // 2-point-minimum d3.area has nothing to draw for one point).
          const bar = r.bar!;
          const x = xScale(bar.date) - ISOLATED_BAR_WIDTH / 2;
          const yZero = yScale(0);
          const yValue = yScale(bar.periodGain as number);
          const y = Math.min(yZero, yValue);
          const h = Math.abs(yZero - yValue);
          return (
            <rect key={i} data-role={r.sign === "gain" ? "investment-gain-area" : "investment-loss-area"}
                  x={x} y={y} width={ISOLATED_BAR_WIDTH} height={h} fill={color} fillOpacity={0.9} />
          );
        })}

        {/* Reference series: Net Contributions -- solid, subtle, always
            visible, never behind a toggle (sec 6/15), visually subordinate
            to Balance (no dashed styling). */}
        <path data-role="net-contributions-line" d={contribLine(parsed) ?? undefined} fill="none"
              stroke="var(--color-text-muted)" strokeWidth={1.5} />

        {/* Primary series: Portfolio Balance -- most visually prominent,
            drawn last so it always sits on top of both fills. */}
        <path data-role="portfolio-balance-line" d={balanceLine(parsed) ?? undefined} fill="none"
              stroke="var(--color-accent)" strokeWidth={2.5} />

        {events.map((d, i) => {
          const x = xScale(d.date);
          const y = d.value !== null ? yScale(d.value) : yScale(d.netContrib);
          const isWithdrawal = d.events.some((e) => e.type === "WITHDRAWAL");
          return (
            <circle key={i} cx={x} cy={y} r={4}
                    fill={isWithdrawal ? "var(--color-negative)" : "var(--color-positive)"}
                    stroke="var(--color-surface)" strokeWidth={1.5} />
          );
        })}

        <rect
          className={styles.interactionLayer}
          width={innerWidth} height={innerHeight} fill="transparent"
          tabIndex={0}
          aria-label="Portfolio growth chart data points. Use the left and right arrow keys to move between dates."
          onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}
          onFocus={onFocus} onBlur={onBlur} onKeyDown={onKeyDown}
        />

        {hovered && (
          <Crosshair x={xScale(hovered.date)} height={innerHeight}
                     y={hovered.value !== null ? yScale(hovered.value) : yScale(hovered.netContrib)} />
        )}
      </g>

      {hovered && (
        <foreignObject x={0} y={0} width={width} height={height} style={{ overflow: "visible", pointerEvents: "none" }}>
          <ChartTooltip x={xScale(hovered.date) + MARGIN.left} y={MARGIN.top} containerWidth={width}>
            <GrowthTooltipContent point={hovered} />
          </ChartTooltip>
        </foreignObject>
      )}
    </svg>
    <p className={styles.srOnly} aria-live="polite">
      {hovered ? liveRegionText(hovered) : ""}
    </p>
    </>
  );
}

/** "Investment Gain" for a positive period_investment_gain, "Investment
 * Loss" for a negative one -- the same distinction the chart's own
 * green/red areas make, never a merged "Investment Gain/Loss" label. */
function periodGainLabel(periodGain: number): string {
  return periodGain >= 0 ? "Investment Gain" : "Investment Loss";
}

function liveRegionText(d: Parsed): string {
  const parts = [
    `${formatDate(d.dateStr)}:`,
    `Portfolio value ${d.value !== null ? formatMoney(String(d.value)) : "not available"}.`,
    `Net contributions ${formatMoney(String(d.netContrib))}.`,
    d.periodGain !== null ? `${periodGainLabel(d.periodGain)} ${formatMoneySigned(String(d.periodGain))}.` : "",
    d.investmentGain !== null ? `Cumulative investment gain ${formatMoneySigned(String(d.investmentGain))}.` : "",
  ];
  for (const e of d.events) {
    parts.push(`${e.type === "CONTRIBUTION" ? "Contribution" : "Withdrawal"} ${formatMoneySigned(e.amount)}.`);
  }
  return parts.filter(Boolean).join(" ");
}

function GrowthTooltipContent({ point }: { point: Parsed }) {
  return (
    <div>
      <div className={styles.date}>{formatDate(point.dateStr)}</div>
      {point.events.map((e, i) => (
        <div key={i} className={styles.eventRow} data-sign={e.type === "CONTRIBUTION" ? "positive" : "negative"}>
          {e.type === "CONTRIBUTION" ? "Contribution" : "Withdrawal"} {formatMoneySigned(e.amount)}
        </div>
      ))}
      <div className={styles.row}>
        <span>Portfolio value</span>
        <span className={styles.value}>{point.value !== null ? formatMoney(String(point.value)) : "—"}</span>
      </div>
      <div className={styles.row}>
        <span>Net contributions</span>
        <span className={styles.value}>{formatMoney(String(point.netContrib))}</span>
      </div>
      {point.periodGain !== null && (
        <div className={styles.row}>
          {/* Labelled Investment Gain or Investment Loss -- matching the
              chart's own green/red areas -- never a merged "Investment
              Gain/Loss" label the viewer would have to interpret. */}
          <span>{periodGainLabel(point.periodGain)}</span>
          <span className={styles.value} data-sign={point.periodGain >= 0 ? "positive" : "negative"}>
            {formatMoneySigned(String(point.periodGain))}
          </span>
        </div>
      )}
      <div className={styles.row}>
        <span>Cumulative investment gain</span>
        <span className={styles.value} data-sign={point.investmentGain !== null ? sign(String(point.investmentGain)) : "neutral"}>
          {point.investmentGain !== null ? formatMoneySigned(String(point.investmentGain)) : "—"}
        </span>
      </div>
    </div>
  );
}
