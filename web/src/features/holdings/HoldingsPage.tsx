import { useParams } from "react-router-dom";

import { Card } from "../../design-system/Card/Card";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import { ChartContainer } from "../../components/charts/ChartContainer/ChartContainer";
import { AllocationHistoryChart } from "../../components/charts/AllocationHistoryChart/AllocationHistoryChart";
import { AllocationSection } from "./AllocationSection";
import { HoldingsSnapshot } from "./HoldingsSnapshot";
import { HoldingsTable } from "./HoldingsTable";
import { SecurityDetail } from "./SecurityDetail";
import { useHoldingsData } from "./useHoldingsData";
import styles from "./HoldingsPage.module.css";

const ASSET_CLASS_LABELS: Record<string, string> = {
  australian_equities: "Australian equities", international_equities: "International equities",
  bonds: "Bonds", property: "Property", cash: "Cash", other: "Other", unknown: "Unknown",
};

/**
 * The Holdings & Allocation screen (Phase 5.7): what the portfolio owns,
 * what it's worth, how it's allocated, and how that's changed over time --
 * entirely by visualising Phase 4's holdings/allocation endpoints. No
 * weight, gain or value here is ever derived from another API field; every
 * figure is read directly from the response that already computed it.
 */
export function HoldingsPage() {
  const { code } = useParams<{ code?: string }>();
  const data = useHoldingsData();

  if (code) {
    return (
      <div className={styles.page}>
        <QueryBoundary query={data.holdings} loading={<Skeleton height={120} />}>
          {(holdings) => (
            <QueryBoundary query={data.unrealisedGains}>
              {(gains) => (
                <SecurityDetail
                  code={code}
                  current={holdings.holdings.find((h) => h.code === code)}
                  currentGain={gains.find((g) => g.code === code)}
                />
              )}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Holdings</h1>
        <p className={styles.description}>
          What the portfolio owns, what it's worth, and how it's allocated across securities and cash.
        </p>
      </header>

      <Card elevation="raised">
        <SectionHeader title="Portfolio snapshot" />
        <QueryBoundary query={data.holdings} loading={<Skeleton height={80} />}>
          {(holdings) => (
            <QueryBoundary query={data.concentration}>
              {(concentration) => <HoldingsSnapshot holdings={holdings} concentration={concentration} />}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Allocation" subtitle="By security or by asset class, as reported by the portfolio engine" />
        <QueryBoundary query={data.allocationByAssetClass} loading={<Skeleton height={200} />}>
          {(byAssetClass) => (
            <QueryBoundary query={data.allocationBySecurity}>
              {(bySecurity) => <AllocationSection bySecurity={bySecurity} byAssetClass={byAssetClass} />}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Holdings" />
        <QueryBoundary
          query={data.holdings}
          isEmpty={(h) => h.holdings.length === 0}
          emptyMessage="No current holdings — this portfolio is fully divested to cash. Historical holdings remain available via allocation history and security detail below."
        >
          {(holdings) => (
            <QueryBoundary query={data.unrealisedGains}>
              {(gains) => <HoldingsTable holdings={holdings.holdings} gains={gains} />}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Allocation over time" subtitle="By asset class, including cash" />
        <QueryBoundary
          query={data.allocationHistory}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="No allocation history available yet."
        >
          {(rows) => (
            <ChartContainer
              height={260}
              accessibleSummary={`Allocation by asset class from ${rows[0]?.date} to ${rows[rows.length - 1]?.date}, ${rows.length} periods.`}
            >
              {({ width, height }) => (
                <AllocationHistoryChart data={rows} width={width} height={height} categoryLabels={ASSET_CLASS_LABELS} />
              )}
            </ChartContainer>
          )}
        </QueryBoundary>
      </Card>

      <footer className={styles.footer}>
        <SectionHeader title="Data coverage" viewAllHref="/history" viewAllLabel="View history" />
        <QueryBoundary query={data.overview}>
          {(overview) => <DataCoverageBadge coverage={overview.data_coverage} />}
        </QueryBoundary>
      </footer>
    </div>
  );
}
