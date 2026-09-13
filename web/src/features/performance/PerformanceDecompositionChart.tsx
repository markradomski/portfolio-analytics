import { useMemo, useState } from "react";

import { BalanceDecompositionChart } from "../../components/charts/BalanceDecompositionChart/BalanceDecompositionChart";
import { ChartContainer } from "../../components/charts/ChartContainer/ChartContainer";
import { ChartLegend, type ChartLegendItem } from "../../components/charts/ChartLegend/ChartLegend";
import { Table, type Column } from "../../design-system/Table/Table";
import { Tabs } from "../../design-system/Tabs/Tabs";
import { UnavailableMetric } from "../../components/data-quality/UnavailableMetric/UnavailableMetric";
import { formatMoney, formatMoneySigned } from "../../formatting/money";
import type { PerformanceOverview, PortfolioGrowthPoint } from "../../api/types";
import styles from "./PerformanceDecompositionChart.module.css";

export interface PerformanceDecompositionChartProps {
  /** The authoritative unbounded growth series (/api/portfolio/growth),
   * passed straight through by PerformancePage. This component only
   * *slices* it to the selected window -- plain date filtering, never a
   * financial calculation -- and hands it to the chart primitive, which
   * plots figures the backend already computed. */
  points: PortfolioGrowthPoint[];
  /** getPerformance(start, end) for the same window -- drives the Table
   * view's period bridge (verbatim API figures only, no arithmetic on
   * two fields). */
  overview: PerformanceOverview;
  /** The selected period's authoritative date bounds, from the
   * performance-periods endpoint. An undefined bound is open-ended
   * (INCEPTION has no start date). */
  windowStart?: string;
  windowEnd?: string;
  periodLabel: string;
}

/** Must exactly match the colours BalanceDecompositionChart itself paints
 * each series in. Always visible, never behind a hover state. Investment
 * Gain and Investment Loss are two separate entries, never merged into one
 * "Investment Gain/Loss" -- gain must be tellable from loss without
 * hovering. These are financial-sign colours, deliberately unrelated to
 * the data-quality / capability / reconciliation colour vocabularies. */
const LEGEND_ITEMS: ChartLegendItem[] = [
  { label: "Total Balance", color: "var(--color-balance)", shape: "line" },
  { label: "Contributions & Withdrawals", color: "var(--color-accent-bg)", shape: "area" },
  { label: "Investment Gain", color: "var(--color-positive)", shape: "area", opacity: 0.9 },
  { label: "Investment Loss", color: "var(--color-negative)", shape: "area", opacity: 0.9 },
];

/**
 * The advanced Vanguard-style performance decomposition on the Performance
 * screen (Step 9A Part B). Additive -- it sits alongside every existing
 * Performance section, in place of none of them.
 *
 * The chart is the detailed balance decomposition that lived on Overview
 * through Step 9 and moved here in Step 9A: Total Balance, the cumulative
 * Contributions & Withdrawals area, the per-period Investment Gain / Loss
 * areas, contribution/withdrawal event markers and a rich hover/keyboard
 * tooltip -- BalanceDecompositionChart, wrapped here in the standard
 * legend + ResizeObserver container + Chart/Table toggle.
 *
 * The Table view is the authoritative period bridge
 * (beginning + contributions − withdrawals + investment return = ending),
 * every cell a verbatim /api/portfolio/performance field. No figure on
 * either view is derived from arithmetic on two API fields; this is a
 * *wealth* decomposition in dollars and never a rate of return -- TWRR and
 * XIRR remain authoritative in the existing Methodology section.
 *
 * The section stays visible in every data state (Step 9A.1): a period with
 * no valued history shows an explicit unavailable message in the Chart
 * view rather than collapsing, and a window missing a boundary valuation
 * shows one in the Table view.
 */
export function PerformanceDecompositionChart({
  points, overview, windowStart, windowEnd, periodLabel,
}: PerformanceDecompositionChartProps) {
  const [view, setView] = useState<"chart" | "table">("chart");

  const sliced = useMemo(
    () => points.filter((p) => (!windowStart || p.date >= windowStart) && (!windowEnd || p.date <= windowEnd)),
    [points, windowStart, windowEnd],
  );
  const valued = useMemo(() => sliced.filter((p) => p.portfolio_value !== null), [sliced]);

  const periodText = periodLabel === "INCEPTION" ? "since inception" : `over ${periodLabel}`;

  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <p className={styles.caption}>
          How the balance moved {periodText}: the total you contributed (net of withdrawals), and the
          investment gain or loss on top of it. A dollar decomposition, not a rate of return.
        </p>
        <Tabs
          items={[{ value: "chart", label: "Chart" }, { value: "table", label: "Table" }]}
          value={view}
          onChange={(v) => setView(v as "chart" | "table")}
          aria-label="Decomposition view"
        />
      </div>

      {view === "chart" && (
        <>
          <ChartLegend items={LEGEND_ITEMS} />
          {valued.length === 0 ? (
            <UnavailableMetric
              title="Balance decomposition"
              reason={
                "No valued portfolio history in this period yet. Try a longer period, or use the Table" +
                " view for this period's totals."
              }
            />
          ) : (
            <ChartContainer
              height={340}
              accessibleSummary={
                `Total balance, net contributions and investment gain or loss ${periodText}, ` +
                `${sliced.length} data point${sliced.length === 1 ? "" : "s"}.`
              }
            >
              {({ width, height }) => <BalanceDecompositionChart points={sliced} width={width} height={height} />}
            </ChartContainer>
          )}
        </>
      )}

      {view === "table" && <DecompositionTable overview={overview} />}
    </div>
  );
}

function DecompositionTable({ overview }: { overview: PerformanceOverview }) {
  const canBridge = overview.opening_value !== null && overview.closing_value !== null;
  if (!canBridge) {
    return (
      <UnavailableMetric
        title="Period decomposition"
        reason={
          "This window has no valuation on one of its boundary dates, so a beginning-to-ending balance" +
          " bridge can't be drawn. The percentage returns above are still available."
        }
      />
    );
  }

  interface Row { label: string; value: string }
  const rows: Row[] = [
    { label: "Beginning balance", value: formatMoney(overview.opening_value) },
    { label: "Contributions", value: formatMoneySigned(overview.contributions) },
    { label: "Withdrawals", value: formatMoneySigned(overview.withdrawals) },
    { label: "Net external flow", value: formatMoneySigned(overview.net_external_flow) },
    { label: "Investment return", value: formatMoneySigned(overview.investment_gain ?? "0") },
    { label: "Income (within investment return)", value: formatMoneySigned(overview.income) },
    { label: "Ending balance", value: formatMoney(overview.closing_value) },
  ];
  const columns: Column<Row>[] = [
    { key: "label", header: "Component", render: (r) => r.label },
    { key: "value", header: "Amount", numeric: true, render: (r) => r.value },
  ];
  return <Table columns={columns} rows={rows} rowKey={(r) => r.label} caption="Period balance decomposition" />;
}
