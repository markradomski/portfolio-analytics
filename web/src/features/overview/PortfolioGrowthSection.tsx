import { useSearchParams } from "react-router-dom";

import { ChartContainer } from "../../components/charts/ChartContainer/ChartContainer";
import { ChartLegend, type ChartLegendItem } from "../../components/charts/ChartLegend/ChartLegend";
import { PortfolioGrowthChart } from "../../components/charts/PortfolioGrowthChart/PortfolioGrowthChart";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { Tabs, type TabItem } from "../../design-system/Tabs/Tabs";
import { usePortfolioGrowth, usePortfolioGrowthSummary } from "../../hooks/api/usePortfolioApi";
import { getStoredPeriod, setStoredPeriod } from "../../lib/periodStorage";
import { formatMoney, formatMoneySigned, formatPercentSigned } from "../../formatting/money";
import type { PortfolioGrowthPoint, PortfolioGrowthSummary } from "../../api/types";
import styles from "./PortfolioGrowthSection.module.css";

const PERIODS = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "MAX"] as const;
export type Period = (typeof PERIODS)[number];
const DEFAULT_PERIOD: Period = "MAX";

/**
 * The Overview screen's simple wealth-snapshot section (Step 9A Part A,
 * simplified in Step 9A.2): the period selector, the persistent
 * plain-language legend, and the headline metrics. The chart itself is
 * PortfolioGrowthChart -- deliberately with no explanatory paragraph
 * beneath it; the legend and ordinary-language labels carry the meaning.
 *
 * The growth series is fetched once, unbounded, and sliced client-side by
 * period -- the same "fetch once, slice locally" convention every other
 * period-controlled chart in this app already uses -- so switching between
 * 1M through MAX never re-fetches. Picking a cutoff date is plain date
 * arithmetic, never a financial calculation: the plotted figures are
 * untouched, only which of the API's own points are shown. Crucially, the
 * contribution baseline at the start of the visible window is the
 * authoritative *cumulative* net-contribution state (the API's own
 * `net_contributions` on that date), not a value re-based to zero -- a
 * point outside the visible window is simply not drawn, never zeroed.
 *
 * YTD is "1 January of the year containing the series' own latest
 * available date, through that latest date" -- never the browser's wall-
 * clock year, since the series can end well before "now" -- and not "the
 * last 12 months" either. Every period
 * gracefully clamps to the earliest date the series actually has, rather
 * than producing an empty chart when less history exists than the period
 * asks for (e.g. 5Y selected with only 4 years of data).
 */
export function sliceByPeriod(points: PortfolioGrowthPoint[], period: Period): PortfolioGrowthPoint[] {
  if (period === "MAX" || points.length === 0) return points;

  const earliest = new Date(points[0].date);
  const last = new Date(points[points.length - 1].date);
  let cutoff: Date;

  if (period === "YTD") {
    // Anchored to the dataset's own latest point, never the browser's wall-
    // clock date -- the series can (and for the demo dataset, does) end
    // before "now". No requirement that a Jan-1 point exists exactly: the
    // p.date >= cutoff filter below naturally picks the first point on or
    // after it.
    cutoff = new Date(last.getFullYear(), 0, 1);
  } else {
    cutoff = new Date(last);
    if (period === "1M") cutoff.setMonth(cutoff.getMonth() - 1);
    else if (period === "3M") cutoff.setMonth(cutoff.getMonth() - 3);
    else if (period === "6M") cutoff.setMonth(cutoff.getMonth() - 6);
    else if (period === "1Y") cutoff.setFullYear(cutoff.getFullYear() - 1);
    else if (period === "3Y") cutoff.setFullYear(cutoff.getFullYear() - 3);
    else if (period === "5Y") cutoff.setFullYear(cutoff.getFullYear() - 5);
  }

  if (cutoff < earliest) cutoff = earliest;
  return points.filter((p) => new Date(p.date) >= cutoff);
}

const PERIOD_ITEMS: TabItem[] = PERIODS.map((p) => ({ value: p, label: p }));

/** Must exactly match the colours PortfolioGrowthChart itself paints each
 * series in -- kept as one list here rather than duplicated. Always
 * visible, never behind a hover state. Investment Gain and Investment Loss
 * are two separate entries, never merged. These are *financial-sign*
 * colours (green = gain, red = loss); they are deliberately unrelated to
 * the data-quality / capability / reconciliation colour vocabularies. */
const LEGEND_ITEMS: ChartLegendItem[] = [
  { label: "Total Balance", color: "var(--color-balance)", shape: "line" },
  { label: "Contributions", color: "var(--color-contribution)", shape: "area", opacity: 0.28 },
  { label: "Investment Gain", color: "var(--color-positive)", shape: "area", opacity: 0.85 },
  { label: "Investment Loss", color: "var(--color-negative)", shape: "area", opacity: 0.85 },
];

export interface PortfolioGrowthSectionProps {
  /** The authoritative inception rate of return (TWRR, decimal fraction)
   * -- passed down from OverviewPage, which already reads it from the
   * performance-periods endpoint. Shown as a separate headline metric so
   * it is never confused with the dollar wealth decomposition. */
  rateOfReturn?: string | null;
  /** Authoritative lifetime `total_contributed` / `total_withdrawn` from
   * the portfolio-overview endpoint (already fetched by OverviewPage).
   * When both are present the headline uses the plainer "Contributed /
   * Withdrawn" pair; otherwise it falls back to the single "Net
   * contributions" figure the growth-summary endpoint exposes. Neither is
   * computed here -- see the API gap noted in
   * docs/portfolio-wealth-chart.md. */
  contributed?: string | null;
  withdrawn?: string | null;
}

export function PortfolioGrowthSection({ rateOfReturn, contributed, withdrawn }: PortfolioGrowthSectionProps) {
  const growth = usePortfolioGrowth();
  const summary = usePortfolioGrowthSummary();
  const [searchParams, setSearchParams] = useSearchParams();
  // "period" is the one query param every period-tab section (this chart,
  // the Performance screen) reads and writes, so the selected window
  // persists across the "View performance"/"Back to Overview" links --
  // never each section keeping its own independent selection. Falls back
  // to the last value persisted in localStorage when the URL has no
  // "period" param at all (a detour through a screen that doesn't carry
  // one, e.g. Holdings), so the selection survives that detour too.
  const requested = searchParams.get("period") ?? getStoredPeriod();
  const period: Period = (PERIODS as readonly string[]).includes(requested ?? "")
    ? (requested as Period) : DEFAULT_PERIOD;

  function setPeriod(value: string) {
    setStoredPeriod(value);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("period", value);
        return next;
      },
      { replace: true },
    );
  }

  return (
    <div className={styles.wrap}>
      <QueryBoundary query={summary} loading={<Skeleton height={80} />}>
        {(s) => (
          <SummaryRow summary={s} rateOfReturn={rateOfReturn} contributed={contributed} withdrawn={withdrawn} />
        )}
      </QueryBoundary>

      <Tabs items={PERIOD_ITEMS} value={period} onChange={setPeriod} aria-label="Portfolio growth period" />

      <ChartLegend items={LEGEND_ITEMS} />

      <QueryBoundary
        query={growth}
        loading={<Skeleton height={340} />}
        isEmpty={(points) => points.length === 0}
        emptyMessage="No portfolio history available yet."
      >
        {(points) => {
          const sliced = sliceByPeriod(points, period);
          return (
            <ChartContainer
              height={340}
              accessibleSummary={
                `Total balance, net contributions and investment gain or loss, ` +
                `${period === "MAX" ? "full history" : period}, ` +
                `${sliced.length} data point${sliced.length === 1 ? "" : "s"}.`
              }
            >
              {({ width, height }) => <PortfolioGrowthChart points={sliced} width={width} height={height} />}
            </ChartContainer>
          );
        }}
      </QueryBoundary>
    </div>
  );
}

/** Plain-language label + value for the investment residual: "Investment
 * gain" / "Investment loss" by actual sign, "Investment gain/loss" only
 * for an exact zero -- never "Investment gain/loss  -$X". */
function investmentResidual(raw: string | null | undefined): { label: string; value: string | null } {
  if (raw == null) return { label: "Investment gain/loss", value: null };
  const n = Number(raw);
  if (n > 0) return { label: "Investment gain", value: formatMoneySigned(raw) };
  if (n < 0) return { label: "Investment loss", value: formatMoneySigned(raw) };
  return { label: "Investment gain/loss", value: formatMoney(raw) };
}

function SummaryRow({
  summary, rateOfReturn, contributed, withdrawn,
}: {
  summary: PortfolioGrowthSummary;
  rateOfReturn?: string | null;
  contributed?: string | null;
  withdrawn?: string | null;
}) {
  const residual = investmentResidual(summary.investment_gain);
  // Withdrawals are stored signed-negative; the "Withdrawn" metric reads
  // as a plain positive amount ("$123,590.12 withdrawn"). Taking the
  // magnitude for display is not a financial calculation -- the
  // authoritative signed value is untouched.
  const withdrawnDisplay = withdrawn == null ? null : formatMoney(String(Math.abs(Number(withdrawn))));
  const hasSplit = contributed != null && withdrawn != null;

  return (
    <div className={styles.summaryRow}>
      {hasSplit ? (
        <>
          {/* Informational facts, not performance -- rendered in the
              neutral colour, never green/red (no `rawValue`). */}
          <MetricValue label="Contributed" value={formatMoney(contributed)} />
          <MetricValue label="Withdrawn" value={withdrawnDisplay} />
        </>
      ) : (
        <MetricValue
          label="Net contributions"
          value={formatMoney(summary.net_contributions)}
          rawValue={summary.net_contributions}
        />
      )}
      <MetricValue
        label={residual.label}
        value={residual.value}
        rawValue={summary.investment_gain}
        unavailableReason={summary.investment_gain == null ? "Not available" : undefined}
      />
      <MetricValue
        label="Total balance"
        value={summary.current_value == null ? null : formatMoney(summary.current_value)}
        rawValue={summary.current_value}
        unavailableReason={summary.current_value == null ? "Not available" : undefined}
        size="large"
      />
      <MetricValue
        label="Rate of return"
        value={rateOfReturn ? formatPercentSigned(rateOfReturn) : null}
        rawValue={rateOfReturn}
        unavailableReason={!rateOfReturn ? "Not enough valuation history" : undefined}
        meta={<span className={styles.rorNote}>time-weighted, since inception</span>}
      />
    </div>
  );
}
