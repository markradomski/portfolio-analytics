import { Card } from "../../design-system/Card/Card";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import { UnavailableMetric } from "../../components/data-quality/UnavailableMetric/UnavailableMetric";
import {
  useAttribution, useAttributionReconciliation, usePerformanceOverview, usePortfolioGrowth, usePortfolioHistory,
} from "../../hooks/api/usePortfolioApi";
import { useSelectedPeriod } from "../../hooks/useSelectedPeriod";
import { formatDate, formatPercentSigned } from "../../formatting/money";
import type { BestWorstPeriods, ExtremePeriod } from "../../api/types";
import { CalendarPerformanceTable } from "./CalendarPerformanceTable";
import { MethodologyPanel } from "./MethodologyPanel";
import { PerformanceChart } from "./PerformanceChart";
import { PerformanceDecompositionChart } from "./PerformanceDecompositionChart";
import { PerformanceSummary } from "./PerformanceSummary";
import { ReturnDecomposition } from "./ReturnDecomposition";
import { usePerformanceData } from "./usePerformanceData";
import styles from "./PerformancePage.module.css";

const PERIOD_LABELS = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "INCEPTION"];

/**
 * The Performance screen (Phase 5.6): why the headline return number says
 * what it says, how it decomposes into capital growth vs income, how TWRR
 * and XIRR differ, and how performance has varied across periods and years
 * -- entirely by visualising Phase 4's own analytics endpoints (sec 2). No
 * figure here is derived by anything other than formatting or selection.
 */
export function PerformancePage() {
  const data = usePerformanceData();
  const { selected, setSelected, activePeriod } = useSelectedPeriod(data.periods.data, PERIOD_LABELS, "1Y");
  const start = activePeriod?.start_date ?? undefined;
  const end = activePeriod?.end_date ?? undefined;

  const overview = usePerformanceOverview(start, end);
  const attribution = useAttribution(start, end);
  const reconciliation = useAttributionReconciliation(start, end);
  // Fully-divested portfolios (sec 23) still have a complete historical
  // return series -- this reads the same unbounded history the Overview
  // fetches (shared cache key, no extra request when it's already warm).
  const history = usePortfolioHistory();
  // The advanced "Balance decomposition" chart reads the same unbounded
  // growth series the Overview fetches (shared cache key -- no extra
  // request when it is already warm) and slices it to the selected window.
  const growth = usePortfolioGrowth();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <a href="/" className={styles.backLink}>← Back to Overview</a>
        <h1>Performance</h1>
        <p className={styles.description}>
          Portfolio returns across time, separated into capital growth and income and adjusted for external cash
          flows.
        </p>
      </header>

      <Card elevation="raised">
        <SectionHeader title="Performance summary" />
        <QueryBoundary query={overview} loading={<Skeleton height={120} />}>
          {(o) => <PerformanceSummary activePeriod={activePeriod} dollarOverview={o} periodLabel={selected} />}
        </QueryBoundary>
      </Card>

      <Card elevation="raised">
        <SectionHeader title="Performance history" subtitle="Return index, not portfolio value" />
        <QueryBoundary query={data.periods} loading={<Skeleton height={280} />}>
          {(periods) => (
            <QueryBoundary query={history} loading={<Skeleton height={280} />}>
              {(h) => <PerformanceChart periods={periods} history={h} selected={selected} onSelect={setSelected} />}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <Card elevation="raised">
        <SectionHeader
          title="Balance decomposition"
          subtitle="The total you contributed, and the investment gain or loss on top of it"
        />
        <QueryBoundary query={overview} loading={<Skeleton height={340} />}>
          {(o) => (
            <QueryBoundary
              query={growth}
              loading={<Skeleton height={340} />}
              isEmpty={(points) => points.length === 0}
              emptyMessage="No portfolio history available yet."
            >
              {(points) => (
                <PerformanceDecompositionChart
                  points={points}
                  overview={o}
                  windowStart={start}
                  windowEnd={end}
                  periodLabel={selected}
                />
              )}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader
          title="Return decomposition"
          subtitle="Where the change in this period came from"
          viewAllHref="/contributions"
          viewAllLabel="View contributions"
        />
        <QueryBoundary query={attribution} loading={<Skeleton height={160} />}>
          {(tree) => (
            <QueryBoundary query={reconciliation}>
              {(rec) => <ReturnDecomposition attribution={tree} reconciliation={rec} />}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Methodology" subtitle="TWRR and XIRR for the selected period" />
        <QueryBoundary query={data.methodology} loading={<Skeleton height={140} />}>
          {(methodology) => <MethodologyPanel activePeriod={activePeriod} twrrMethodology={methodology.twrr} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Calendar performance" viewAllHref="/history" viewAllLabel="View history" />
        <QueryBoundary
          query={data.calendar}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="No calendar-year performance available yet."
        >
          {(rows) => (
            <QueryBoundary query={data.overview}>
              {(o) => <CalendarPerformanceTable rows={rows} asAt={o.as_at ?? null} />}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <div className={styles.grid}>
        <Card>
          <SectionHeader title="Best / worst periods" viewAllHref="/risk" />
          <QueryBoundary query={data.bestWorst}>
            {(bestWorst) => <BestWorstSection bestWorst={bestWorst} />}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionHeader title="Drawdown" subtitle="Full detail on the Risk screen" viewAllHref="/risk" />
          <QueryBoundary query={data.drawdowns}>
            {(d) =>
              d.maximum_drawdown_pct == null ? (
                <UnavailableMetric title="Maximum drawdown" reason="No drawdown episodes recorded yet." />
              ) : (
                <div className={styles.secondaryRow}>
                  <MetricValue
                    label="Maximum drawdown"
                    value={formatPercentSigned(d.maximum_drawdown_pct)}
                    rawValue={d.maximum_drawdown_pct}
                  />
                  <MetricValue label="Episodes" value={String(d.episode_count)} />
                  {d.longest_underwater_days != null && (
                    <MetricValue label="Longest underwater" value={`${d.longest_underwater_days} days`} />
                  )}
                </div>
              )
            }
          </QueryBoundary>
        </Card>
      </div>

      <footer className={styles.header}>
        <SectionHeader title="Data coverage" viewAllHref="/history" viewAllLabel="View history" />
        <QueryBoundary query={data.overview}>
          {(o) => <DataCoverageBadge coverage={o.data_coverage} />}
        </QueryBoundary>
      </footer>
    </div>
  );
}

function BestWorstSection({ bestWorst }: { bestWorst: BestWorstPeriods }) {
  const entries = Object.entries(bestWorst).filter(
    (entry): entry is [string, ExtremePeriod[]] => Array.isArray(entry[1]) && entry[1].length > 0,
  );
  if (entries.length === 0) {
    return <UnavailableMetric title="Best / worst periods" reason="Not enough period history available yet." />;
  }
  return (
    <div className={styles.secondaryRow}>
      {entries.flatMap(([, periods]) =>
        periods.map((p) => (
          <MetricValue
            key={p.label}
            label={p.label.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())}
            value={formatPercentSigned(p.return_pct)}
            rawValue={p.return_pct}
            meta={<span>{formatDate(p.period_start)} – {formatDate(p.period_end)}</span>}
          />
        )),
      )}
    </div>
  );
}
