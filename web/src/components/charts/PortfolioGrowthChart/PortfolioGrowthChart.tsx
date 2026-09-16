import { useMemo } from "react";
import * as d3 from "d3";

import { formatDate, formatMoney, formatMoneyCompact, formatMoneySigned } from "../../../formatting/money";
import type { PortfolioGrowthPoint } from "../../../api/types";
import { BREAKPOINT_NARROW_PHONE, BREAKPOINT_PHONE } from "../../../design-system/breakpoints";
import { Axis } from "../Axis/Axis";
import { ChartTooltip } from "../ChartTooltip/ChartTooltip";
import { Crosshair } from "../Crosshair/Crosshair";
import { useNearestPoint } from "../../../hooks/useNearestPoint";
import styles from "./PortfolioGrowthChart.module.css";

export interface PortfolioGrowthChartProps {
  /** Already sliced to the selected period by the caller -- the same
   * "fetch once, unbounded; slice client-side by period" convention every
   * other period-controlled chart in this app uses. */
  points: PortfolioGrowthPoint[];
  width: number;
  height: number;
}

/** The left margin exists for the Y-axis' own dollar labels ($0/$20K/...);
 * a fixed 72px is a small slice of a desktop-width chart but a large one of
 * a phone-width chart, so it -- and the X-axis tick count, which otherwise
 * overlaps at the same narrow widths -- scale down in two steps rather than
 * shrinking the tick text itself (formatMoneyCompact's labels stay legible
 * at every width; what changes is how many of them, and how much margin,
 * the axis needs). Values/scales/series are untouched -- this only affects
 * where the plot area's edges fall. */
function marginFor(width: number) {
  if (width <= BREAKPOINT_NARROW_PHONE) return { top: 16, right: 8, bottom: 24, left: 44 };
  if (width <= BREAKPOINT_PHONE) return { top: 16, right: 12, bottom: 26, left: 52 };
  return { top: 16, right: 16, bottom: 28, left: 72 };
}

function xTickCountFor(width: number): number {
  if (width <= BREAKPOINT_NARROW_PHONE) return 3;
  if (width <= BREAKPOINT_PHONE) return 4;
  return 6;
}

interface Parsed {
  date: Date;
  dateStr: string;
  value: number | null;
  /** The authoritative cumulative net contributions (external
   * contributions minus external withdrawals) exactly as the API returned
   * it -- may be negative when cumulative withdrawals exceed
   * contributions. Kept verbatim for the tooltip / screen-reader text;
   * NOT used directly as chart geometry (see `displayBaseline`). */
  netContrib: number;
  /** PRESENTATION geometry only: `max(netContrib, 0)`. The Overview chart
   * treats $0 as a hard visual floor -- the blue "money I put in" area is
   * drawn from $0 up to this value and never below $0, so a heavily
   * withdrawn portfolio simply shows the blue foundation falling to zero
   * rather than a confusing area below the axis. The authoritative
   * negative value is unchanged and still shown in the tooltip. */
  displayBaseline: number;
  /** Total Balance − Net Contributions at this date (authoritative
   * `investment_gain`, computed server-side in src/analytics/growth.py --
   * never re-derived here). Positive → Investment Gain, negative →
   * Investment Loss. Drives the label/colour; the green/red *area* is
   * drawn between `displayBaseline` and Total Balance, clamped to $0. */
  gainLoss: number | null;
}

/**
 * The Overview screen's simple wealth-snapshot chart (Step 9A Part A,
 * simplified in Step 9A.2). One glance, one mental model:
 *
 *     BLUE  = money I put in       GREEN = money I made
 *     RED   = money I lost         LINE  = what I've got
 *
 * A normal investor should not need to understand signed cumulative cash
 * flows, negative net contributions or wealth-decomposition mathematics to
 * read it -- that complexity lives on the Performance screen.
 *
 * $0 is a HARD VISUAL FLOOR here. Bottom to top:
 *
 * 1. Contributions -- a solid blue area from $0 up to
 *    `max(net contributions, 0)`. Withdrawals lower this foundation; once
 *    everything contributed has been withdrawn it rests at $0 and never
 *    goes below. The authoritative net-contribution figure may still be
 *    negative -- that value is untouched, just not drawn as geometry.
 * 2. Investment Gain / Investment Loss -- the band between that blue
 *    foundation and Total Balance: solid green above, solid red below,
 *    nothing where they meet. Never drawn below $0, so "Investment Gain"
 *    always looks like a gain.
 * 3. Total Balance -- a strong blue line, the authoritative portfolio
 *    value, drawn last and never clamped.
 *
 * The coloured areas are a communication aid, not a restatement of the
 * signed accounting identity (which, with withdrawals suppressed, they no
 * longer form -- see docs/portfolio-wealth-chart.md). No event markers, no
 * per-point dots. This component sorts, scales and draws; it performs no
 * financial calculation of its own -- `max(x, 0)` here is display
 * geometry, explicitly not an edit to any authoritative value.
 */
export function PortfolioGrowthChart({ points, width, height }: PortfolioGrowthChartProps) {
  const MARGIN = marginFor(width);
  const xTickCount = xTickCountFor(width);
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;

  const parsed = useMemo<Parsed[]>(() => points.map((p) => {
    const netContrib = Number(p.net_contributions);
    return {
      date: new Date(p.date),
      dateStr: p.date,
      value: p.portfolio_value === null ? null : Number(p.portfolio_value),
      netContrib,
      displayBaseline: Math.max(netContrib, 0), // PRESENTATION floor -- never mutates the API value
      gainLoss: p.investment_gain === null ? null : Number(p.investment_gain),
    };
  }), [points]);

  const valued = useMemo(() => parsed.filter((d) => d.value !== null), [parsed]);

  const xScale = useMemo(
    () => d3.scaleTime().domain(d3.extent(parsed, (d) => d.date) as [Date, Date]).range([0, innerWidth]),
    [parsed, innerWidth],
  );

  const yScale = useMemo(() => {
    // Every drawn quantity is >= $0 (the blue foundation and the green/red
    // bands are all clamped to the floor), so the domain is pinned at 0 at
    // the bottom -- $0 sits on the axis. Only a (real-world near-impossible)
    // negative Total Balance would push it lower, and that line is never
    // clamped, so allow for it.
    const tops = [0, ...valued.map((d) => d.value as number), ...parsed.map((d) => d.displayBaseline)];
    const min = Math.min(0, ...valued.map((d) => d.value as number));
    const max = d3.max(tops) ?? 0;
    const pad = (max - Math.min(0, min)) * 0.08 || 1;
    return d3.scaleLinear().domain([min, max + pad]).nice().range([innerHeight, 0]);
  }, [valued, parsed, innerHeight]);

  const balanceLine = useMemo(
    () => d3.line<Parsed>().defined((d) => d.value !== null)
      .x((d) => xScale(d.date)).y((d) => yScale(d.value as number)).curve(d3.curveMonotoneX),
    [xScale, yScale],
  );

  // Contributions: a solid blue area from the $0 floor up to the *display
  // baseline* (`max(net contributions, 0)`) -- never below the axis.
  const contributionsArea = useMemo(
    () => d3.area<Parsed>()
      .x((d) => xScale(d.date))
      .y0(() => yScale(0))
      .y1((d) => yScale(d.displayBaseline))
      .curve(d3.curveMonotoneX),
    [xScale, yScale],
  );

  // Investment Gain / Investment Loss: the band between the blue
  // foundation and Total Balance, split into contiguous same-sign runs so
  // each fills in its own colour -- green where Total Balance is above the
  // foundation, red where below. Both edges clamped to the $0 floor, so
  // neither colour is ever drawn beneath the axis. A run breaks wherever
  // Total Balance is unavailable or the two edges meet.
  const gainLossRuns = useMemo(() => {
    const EPS = 1e-6;
    const withBand = parsed.map((d) => {
      if (d.value === null) return null;
      const lo = Math.max(0, Math.min(d.value, d.displayBaseline));
      const hi = Math.max(0, Math.max(d.value, d.displayBaseline));
      if (hi - lo < EPS) return null;
      return { ...d, lo, hi, sign: (d.value >= d.displayBaseline ? "gain" : "loss") as "gain" | "loss" };
    });

    const runs: { sign: "gain" | "loss"; points: NonNullable<(typeof withBand)[number]>[]; lastIndex: number }[] = [];
    for (let i = 0; i < withBand.length; i++) {
      const d = withBand[i];
      if (!d) continue;
      const last = runs[runs.length - 1];
      if (last && last.sign === d.sign && last.lastIndex === i - 1) {
        last.points.push(d);
        last.lastIndex = i;
      } else {
        runs.push({ sign: d.sign, points: [d], lastIndex: i });
      }
    }

    const area = d3.area<{ date: Date; lo: number; hi: number }>()
      .x((d) => xScale(d.date))
      .y0((d) => yScale(d.lo))
      .y1((d) => yScale(d.hi))
      .curve(d3.curveMonotoneX);
    return runs
      .filter((r) => r.points.length >= 2)
      .map((r) => ({ sign: r.sign, d: area(r.points) }));
  }, [parsed, xScale, yScale]);

  const { hovered, onPointerMove, onPointerLeave, onFocus, onBlur, onKeyDown } = useNearestPoint(
    valued, (d) => d.date, xScale,
  );

  return (
    <>
    <svg width={width} height={height} role="group"
         aria-label="Portfolio wealth over time: total balance, the money contributed, and investment gain or loss">
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        <Axis scale={yScale} orientation="left" tickCount={5} grid gridLength={innerWidth}
              tickFormat={(v) => formatMoneyCompact(String(v))} />
        <Axis scale={xScale} orientation="bottom" transform={`translate(0,${innerHeight})`} tickCount={xTickCount} />

        {/* Investment Gain / Investment Loss -- drawn first so the blue
            Contributions foundation always sits crisply on top of it. */}
        {gainLossRuns.map((r, i) => (
          <path key={i}
                data-role={r.sign === "gain" ? "investment-gain-area" : "investment-loss-area"}
                d={r.d ?? undefined}
                fill={r.sign === "gain" ? "var(--color-positive)" : "var(--color-negative)"}
                fillOpacity={0.85} stroke="none" />
        ))}

        {/* Contributions -- solid blue area, floored at $0. Its own token
            (aliased to --color-accent in Light/Dark, distinct in Vanyard)
            so a brand-coloured theme can still tell "money you put in"
            apart from "the balance line" -- see tokens.css. */}
        <path data-role="contributions-area" d={contributionsArea(parsed) ?? undefined}
              fill="var(--color-contribution)" fillOpacity={0.28} stroke="none" />

        {/* The $0 baseline -- explicit and distinct from the gridlines: the
            hard visual floor every area rests on. */}
        <line data-role="zero-baseline" x1={0} x2={innerWidth} y1={yScale(0)} y2={yScale(0)}
              stroke="var(--chart-axis)" strokeWidth={1} />

        {/* Total Balance -- the strong line, on top of everything,
            authoritative and never clamped. */}
        <path data-role="portfolio-balance-line" d={balanceLine(parsed) ?? undefined} fill="none"
              stroke="var(--color-balance)" strokeWidth={2.5} />

        <rect
          className={styles.interactionLayer}
          width={innerWidth} height={innerHeight} fill="transparent"
          tabIndex={0}
          aria-label="Wealth chart data points. Use the left and right arrow keys to move between dates."
          onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}
          onFocus={onFocus} onBlur={onBlur} onKeyDown={onKeyDown}
        />

        {hovered && (
          <Crosshair x={xScale(hovered.date)} height={innerHeight}
                     y={hovered.value !== null ? yScale(hovered.value) : yScale(hovered.displayBaseline)} />
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

/** Plain investor language for the balance − contributions residual:
 * "Investment gain" when positive, "Investment loss" when negative,
 * "Investment gain or loss" only for an exact zero. Never "Investment gain
 * -$X". */
function gainLossLabel(gainLoss: number): string {
  if (gainLoss > 0) return "Investment gain";
  if (gainLoss < 0) return "Investment loss";
  return "Investment gain or loss";
}

/** The residual as plain text: "+$X" for a gain, "$X" (unsigned) for a
 * loss -- so a screen reader says "Investment loss $4,000", never
 * "Investment gain negative $4,000". */
function gainLossAmount(gainLoss: number): string {
  if (gainLoss < 0) return formatMoney(String(Math.abs(gainLoss)));
  if (gainLoss > 0) return formatMoneySigned(String(gainLoss));
  return formatMoney("0");
}

function liveRegionText(d: Parsed): string {
  const contributed = d.netContrib < 0
    ? `Net contributed ${formatMoneySigned(String(d.netContrib))}.`
    : `Contributions ${formatMoney(String(d.netContrib))}.`;
  const parts = [
    `${formatDate(d.dateStr)}:`,
    `Total balance ${d.value !== null ? formatMoney(String(d.value)) : "not available"}.`,
    contributed,
    d.gainLoss !== null ? `${gainLossLabel(d.gainLoss)} ${gainLossAmount(d.gainLoss)}.` : "",
  ];
  return parts.filter(Boolean).join(" ");
}

function GrowthTooltipContent({ point }: { point: Parsed }) {
  const negativeContrib = point.netContrib < 0;
  return (
    <div>
      <div className={styles.date}>{formatDate(point.dateStr)}</div>
      <div className={styles.row}>
        <span>Total balance</span>
        <span className={styles.value}>{point.value !== null ? formatMoney(String(point.value)) : "—"}</span>
      </div>
      <div className={styles.row}>
        {/* Plain "Contributions" for the normal case; the explicit "Net
            contributed" only when withdrawals have taken the authoritative
            figure below zero -- shown as a number, never implied to be a
            blue area beneath the axis. */}
        <span>{negativeContrib ? "Net contributed" : "Contributions"}</span>
        <span className={styles.value}>
          {negativeContrib
            ? formatMoneySigned(String(point.netContrib))
            : formatMoney(String(point.netContrib))}
        </span>
      </div>
      {point.gainLoss !== null && (
        <div className={styles.row}>
          <span>{gainLossLabel(point.gainLoss)}</span>
          <span className={styles.value} data-sign={point.gainLoss > 0 ? "positive" : point.gainLoss < 0 ? "negative" : undefined}>
            {gainLossAmount(point.gainLoss)}
          </span>
        </div>
      )}
    </div>
  );
}
