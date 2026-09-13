import { useSearchParams } from "react-router-dom";

import { Card } from "../../design-system/Card/Card";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { Table, type Column } from "../../design-system/Table/Table";
import { AllocationChart, type AllocationSegment } from "../../components/charts/AllocationChart/AllocationChart";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { UnavailableMetric } from "../../components/data-quality/UnavailableMetric/UnavailableMetric";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import {
  formatDate, formatMoney, formatMoneySigned, formatPercentPlain, formatPercentSigned,
} from "../../formatting/money";
import type { HoldingRow, UnrealisedGainSnapshot } from "../../api/types";
import { PortfolioGrowthSection } from "./PortfolioGrowthSection";
import { useOverviewData } from "./useOverview";
import styles from "./OverviewPage.module.css";

/**
 * The Portfolio Overview (Phase 5.5): the application's first genuinely
 * useful screen, answering at a glance what the portfolio is worth, how it
 * has performed, where it's invested, how much has been put in, and how
 * much income it has produced -- entirely by visualising the API's own
 * responses (sec 2). No figure here is derived by anything other than
 * formatting, sorting, filtering or mapping already-computed API data.
 */
export function OverviewPage() {
  const data = useOverviewData();
  const inception = data.periods.data?.find((p) => p.label === "INCEPTION");
  const lifetime = data.overview.data;
  const [searchParams] = useSearchParams();
  // The Performance screen reads/writes the same "period" param (via
  // useSelectedPeriod's url mapping, which translates this chart's "MAX"
  // to its own "INCEPTION" label) -- so the selected window carries
  // straight across the "View performance ->" link with no rename here.
  const performanceHref = `/performance?period=${searchParams.get("period") ?? "MAX"}`;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        {/* Step 8 hardening (sec 17): the page's one <h1> renders
         * unconditionally -- previously it lived only inside this
         * QueryBoundary's success branch, so the Overview screen had no
         * heading at all while loading or on a failed request. */}
        <h1 className={styles.eyebrow}>Portfolio</h1>
        <QueryBoundary query={data.overview}>
          {(overview) => (
            <>
            <div className={styles.headerRow}>
              <MetricValue
                label={`As at ${formatDate(overview.as_at)}`}
                value={formatMoney(overview.current_value)}
                size="large"
              />
              <div className={styles.headerStats}>
                <MetricValue
                  label="Total gain"
                  value={formatMoneySigned(overview.investment_growth)}
                  rawValue={overview.investment_growth}
                />
                <MetricValue
                  label="Total return"
                  value={inception?.total_return ? formatPercentSigned(inception.total_return) : null}
                  rawValue={inception?.total_return}
                  unavailableReason={!inception?.total_return ? "Not enough valuation history" : undefined}
                />
                <MetricValue label="Contributed" value={formatMoney(overview.total_contributed)} />
              </div>
            </div>
            <DataCoverageBadge coverage={overview.data_coverage} />
            </>
          )}
        </QueryBoundary>
      </header>

      <Card elevation="raised" className={styles.chartCard}>
        <SectionHeader title="Portfolio growth" viewAllHref={performanceHref} viewAllLabel="View performance" />
        <PortfolioGrowthSection
          rateOfReturn={inception?.total_return}
          contributed={lifetime?.total_contributed}
          withdrawn={lifetime?.total_withdrawn}
        />
      </Card>

      <div className={styles.grid}>
        <Card>
          <SectionHeader title="Contributions" viewAllHref="/contributions" />
          <QueryBoundary query={data.overview}>
            {(overview) => (
              <div className={styles.statRow}>
                <MetricValue label="Total contributions" value={formatMoney(overview.total_contributed)} />
                <MetricValue
                  label="Total withdrawals"
                  value={formatMoney(overview.total_withdrawn)}
                  rawValue={overview.total_withdrawn}
                />
                <MetricValue label="Net contributed" value={formatMoney(overview.net_contributed)} />
              </div>
            )}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionHeader title="Income" viewAllHref="/income" />
          <QueryBoundary
            query={data.income}
            isEmpty={(rows) => rows.length === 0}
            emptyMessage="No income recorded yet."
          >
            {(rows) => {
              const latest = rows[rows.length - 1];
              return (
                <>
                  <p className={styles.periodCaption}>Year to {formatDate(latest.period_end)}</p>
                  <div className={styles.statRow}>
                    <MetricValue label="Gross income" value={formatMoney(latest.gross_income)} />
                    <MetricValue label="Franking credits" value={formatMoney(latest.franking_credits)} />
                    <MetricValue label="Net income" value={formatMoney(latest.net_income)} />
                  </div>
                </>
              );
            }}
          </QueryBoundary>
        </Card>
      </div>

      <Card>
        <SectionHeader title="Allocation" subtitle="By asset class" viewAllHref="/holdings" viewAllLabel="View holdings" />
        <QueryBoundary query={data.allocation}>
          {(allocation) =>
            allocation.status === "unavailable" || !allocation.weights ? (
              <UnavailableMetric
                title="Allocation by asset class"
                reason={allocation.note ?? "Not available for this portfolio."}
              />
            ) : (
              <AllocationChart width={640} segments={toSegments(allocation.weights, allocation.allocation_pct)} />
            )
          }
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Top holdings" viewAllHref="/holdings" />
        <QueryBoundary
          query={data.holdings}
          isEmpty={(state) => state.holdings.length === 0}
          emptyMessage="No securities currently held."
        >
          {(state) => (
            <QueryBoundary query={data.unrealisedGains}>
              {(gains) => <TopHoldingsTable holdings={state.holdings} gains={gains} />}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <footer className={styles.footer}>
        <SectionHeader title="Data coverage" viewAllHref="/history" viewAllLabel="View history" />
        <QueryBoundary query={data.overview}>
          {(overview) => (
            <div className={styles.coverageDetail}>
              <DataCoverageBadge coverage={overview.data_coverage} />
              <p className={styles.coverageNote}>
                {overview.data_coverage.carried_forward_observation_count} carried-forward ·{" "}
                {overview.data_coverage.unavailable_observation_count} unavailable ·{" "}
                {overview.data_coverage.price_observation_count} priced observations
              </p>
            </div>
          )}
        </QueryBoundary>
      </footer>
    </div>
  );
}

function toSegments(
  weights: Record<string, string>,
  allocationPct: Record<string, string | null> | null | undefined,
): AllocationSegment[] {
  return Object.entries(weights).map(([key, value]) => ({
    key,
    label: LABELS[key] ?? key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()),
    value,
    weight: allocationPct?.[key] ?? null,
    kind: key === "unknown" ? "unknown" : "known",
  }));
}

const LABELS: Record<string, string> = {
  australian_equities: "Australian equities",
  international_equities: "International equities",
  bonds: "Bonds",
  property: "Property",
  cash: "Cash",
  other: "Other",
  unknown: "Unknown",
};

function TopHoldingsTable({ holdings, gains }: { holdings: HoldingRow[]; gains: UnrealisedGainSnapshot[] }) {
  if (holdings.length === 0) {
    return <p className={styles.periodCaption}>No securities currently held.</p>;
  }
  const gainByCode = new Map(gains.map((g) => [g.code, g]));
  const rows = [...holdings].sort((a, b) => Number(b.market_value ?? 0) - Number(a.market_value ?? 0)).slice(0, 5);

  const columns: Column<HoldingRow>[] = [
    { key: "code", header: "Holding", render: (r) => r.code },
    {
      key: "market_value", header: "Value", numeric: true, sortable: true,
      sortValue: (r) => Number(r.market_value ?? 0), render: (r) => formatMoney(r.market_value),
    },
    {
      key: "allocation_pct", header: "Weight", numeric: true, sortable: true,
      sortValue: (r) => Number(r.allocation_pct ?? 0), render: (r) => formatPercentPlain(r.allocation_pct),
    },
    {
      key: "unrealised_gain", header: "Unrealised gain", numeric: true,
      render: (r) => {
        const gain = gainByCode.get(r.code);
        return gain ? formatMoneySigned(gain.unrealised_gain) : formatMoneySigned(r.unrealised_gain);
      },
    },
    {
      key: "gain_pct", header: "Gain %", numeric: true,
      render: (r) => {
        const gain = gainByCode.get(r.code);
        return gain?.unrealised_gain_pct ? formatPercentSigned(gain.unrealised_gain_pct) : "—";
      },
    },
  ];

  return <Table columns={columns} rows={rows} rowKey={(r) => r.security_id} caption="Top 5 holdings by market value" />;
}
