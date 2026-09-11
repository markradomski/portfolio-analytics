import { Card } from "../../design-system/Card/Card";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { Table, type Column } from "../../design-system/Table/Table";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import { useActivity, useDataCoverage } from "../../hooks/api/usePortfolioApi";
import { formatDate, formatMoney, formatUnits } from "../../formatting/money";
import type { ActivityRow } from "../../api/types";
import styles from "./HistoryPage.module.css";

/**
 * The Activity / History screen (Phase 5.7 remainder): the portfolio's own
 * transaction ledger (sec 28) -- trades, income events, contributions,
 * whatever getActivity() returns -- shown as a single chronological table.
 * No PII field is present on ActivityRow (transaction_id/date/type/code/
 * units/price/net_amount/description are all portfolio-internal), so
 * nothing here needs redaction.
 */
export function HistoryPage() {
  // No start/end: the full lifetime ledger (sec 28 -- history is meant to
  // be complete, not windowed to whatever period another screen selected).
  const activity = useActivity();
  const coverage = useDataCoverage();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Activity</h1>
        <p className={styles.description}>The full transaction history behind this portfolio.</p>
      </header>

      <Card>
        <SectionHeader title="Transactions" />
        <QueryBoundary
          query={activity}
          loading={<Skeleton height={280} />}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="No transactions recorded yet."
        >
          {(rows) => <ActivityTable rows={rows} />}
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

function ActivityTable({ rows }: { rows: ActivityRow[] }) {
  const columns: Column<ActivityRow>[] = [
    {
      key: "trade_date", header: "Date", sortable: true,
      sortValue: (r) => new Date(r.trade_date).getTime(), render: (r) => formatDate(r.trade_date),
    },
    { key: "type", header: "Type", render: (r) => r.type },
    { key: "code", header: "Security", render: (r) => r.code ?? "—" },
    { key: "units", header: "Units", numeric: true, render: (r) => (r.units == null ? "—" : formatUnits(r.units)) },
    { key: "price", header: "Price", numeric: true, render: (r) => (r.price == null ? "—" : formatMoney(r.price)) },
    {
      key: "net_amount", header: "Net amount", numeric: true,
      render: (r) => (r.net_amount == null ? "—" : formatMoney(r.net_amount)),
    },
    { key: "description", header: "Description", render: (r) => r.description },
  ];
  return <Table columns={columns} rows={rows} rowKey={(r) => r.transaction_id} caption="Transaction history" />;
}
