import { Card } from "../../design-system/Card/Card";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { Table, type Column } from "../../design-system/Table/Table";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import {
  useDataCoverage, useRealisedGains, useUnrealisedGains,
} from "../../hooks/api/usePortfolioApi";
import { formatMoney, formatPercentSigned } from "../../formatting/money";
import type { RealisedGainSummary, UnrealisedGainSnapshot } from "../../api/types";
import styles from "./GainsPage.module.css";

/**
 * The Gains screen (Phase 5.7 remainder): capital gains, split explicitly
 * into realised (positions actually sold, sec 24) and unrealised (paper
 * gains on what's still held) -- two different questions the backend
 * already keeps separate (getRealisedGains/getUnrealisedGains), so this
 * screen never merges them into a single "total gain" figure.
 */
export function GainsPage() {
  // Lifetime realised gains: no start/end narrows the window (sec 24).
  const realised = useRealisedGains();
  const unrealised = useUnrealisedGains();
  const coverage = useDataCoverage();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Gains</h1>
        <p className={styles.description}>
          Capital gains, split between positions already sold (realised) and paper gains on current holdings
          (unrealised).
        </p>
      </header>

      <Card elevation="raised">
        <SectionHeader title="Realised gains" subtitle="From positions already sold, lifetime to date" />
        <QueryBoundary query={realised} loading={<Skeleton height={100} />}>
          {(r) => <RealisedSummary summary={r} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Unrealised gains" subtitle="Paper gains on securities still held" />
        <QueryBoundary
          query={unrealised}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="No holdings to show unrealised gains for."
        >
          {(rows) => <UnrealisedTable rows={rows} />}
        </QueryBoundary>
      </Card>

      <footer className={styles.footer}>
        <SectionHeader title="Data coverage" />
        <QueryBoundary query={coverage}>
          {(c) => <DataCoverageBadge coverage={c} />}
        </QueryBoundary>
      </footer>
    </div>
  );
}

function RealisedSummary({ summary }: { summary: RealisedGainSummary }) {
  return (
    <div className={styles.statRow}>
      <MetricValue label="Realised gain" value={formatMoney(summary.realised_gain)} rawValue={summary.realised_gain} />
      <MetricValue label="Realised loss" value={formatMoney(summary.realised_loss)} rawValue={summary.realised_loss} />
      <MetricValue
        label="Net realised"
        value={formatMoney(summary.net_realised_gain)}
        rawValue={summary.net_realised_gain}
        size="large"
      />
    </div>
  );
}

function UnrealisedTable({ rows }: { rows: UnrealisedGainSnapshot[] }) {
  const columns: Column<UnrealisedGainSnapshot>[] = [
    { key: "code", header: "Security", render: (r) => r.code },
    { key: "asset_class", header: "Asset class", render: (r) => r.asset_class },
    {
      key: "market_value", header: "Market value", numeric: true,
      render: (r) => (r.market_value == null ? "—" : formatMoney(r.market_value)),
    },
    { key: "cost_basis", header: "Cost basis", numeric: true, render: (r) => formatMoney(r.cost_basis) },
    {
      key: "unrealised_gain", header: "Unrealised gain", numeric: true, sortable: true,
      sortValue: (r) => Number(r.unrealised_gain ?? 0),
      render: (r) => (r.unrealised_gain == null ? "—" : formatMoney(r.unrealised_gain)),
    },
    {
      key: "unrealised_gain_pct", header: "Unrealised gain %", numeric: true,
      render: (r) => (r.unrealised_gain_pct == null ? "—" : formatPercentSigned(r.unrealised_gain_pct)),
    },
  ];
  return <Table columns={columns} rows={rows} rowKey={(r) => r.security_id} caption="Unrealised gains by holding" />;
}
