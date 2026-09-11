import { Card } from "../../design-system/Card/Card";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { Table, type Column } from "../../design-system/Table/Table";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import {
  useContributionsHistory, useContributionsSummary, useDataCoverage,
} from "../../hooks/api/usePortfolioApi";
import { formatMoney } from "../../formatting/money";
import type { ContributionHistoryRow, ContributionSummary } from "../../api/types";
import styles from "./ContributionsPage.module.css";

/**
 * The Contributions screen (Phase 5.7 remainder): money moved into or out
 * of the portfolio by the investor themselves, kept strictly separate from
 * investment return (sec 25 -- "external flow, not a return"). No history
 * chart here: ContributionHistoryRow carries no `quality` field, so it
 * cannot be plotted through TimeSeriesChart's data-quality contract: the
 * table is the whole picture, same as it is for the API.
 */
export function ContributionsPage() {
  const summary = useContributionsSummary();
  const history = useContributionsHistory("yearly");
  const coverage = useDataCoverage();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Contributions</h1>
        <p className={styles.description}>
          Money contributed to or withdrawn from the portfolio, separate from investment return.
        </p>
      </header>

      <Card elevation="raised">
        <SectionHeader title="Contributions summary" subtitle="Lifetime to date" />
        <QueryBoundary query={summary} loading={<Skeleton height={100} />}>
          {(s) => <SummaryRow summary={s} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Contributions by year" />
        <QueryBoundary
          query={history}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="No contribution history recorded yet."
        >
          {(rows) => <HistoryTable rows={rows} />}
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

function SummaryRow({ summary }: { summary: ContributionSummary }) {
  return (
    <div className={styles.statRow}>
      <MetricValue label="Total contributed" value={formatMoney(summary.total_contributed)} rawValue={summary.total_contributed} />
      <MetricValue label="Total withdrawn" value={formatMoney(summary.total_withdrawn)} rawValue={summary.total_withdrawn} />
      <MetricValue
        label="Net contributed"
        value={formatMoney(summary.net_contributed)}
        rawValue={summary.net_contributed}
        size="large"
      />
      <MetricValue label="Income received" value={formatMoney(summary.income_received)} rawValue={summary.income_received} />
      <MetricValue
        label="Investment growth"
        value={summary.investment_growth == null ? null : formatMoney(summary.investment_growth)}
        rawValue={summary.investment_growth}
        unavailableReason={summary.investment_growth == null ? "Not available" : undefined}
      />
    </div>
  );
}

function HistoryTable({ rows }: { rows: ContributionHistoryRow[] }) {
  const columns: Column<ContributionHistoryRow>[] = [
    { key: "period_end", header: "Year", render: (r) => r.period_end.slice(0, 4) },
    { key: "contributions", header: "Contributions", numeric: true, render: (r) => formatMoney(r.contributions) },
    { key: "withdrawals", header: "Withdrawals", numeric: true, render: (r) => formatMoney(r.withdrawals) },
    {
      key: "net_contributions", header: "Net", numeric: true, sortable: true,
      sortValue: (r) => Number(r.net_contributions), render: (r) => formatMoney(r.net_contributions),
    },
    { key: "cumulative_net", header: "Cumulative net", numeric: true, render: (r) => formatMoney(r.cumulative_net) },
  ];
  return <Table columns={columns} rows={rows} rowKey={(r) => r.period_end} caption="Contributions by year" />;
}
