import { Card } from "../../design-system/Card/Card";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { Table, type Column } from "../../design-system/Table/Table";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { DataQualityBadge } from "../../components/data-quality/DataQualityBadge/DataQualityBadge";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import {
  useDataCoverage, useIncome, useIncomeGrowth, useIncomeYield,
} from "../../hooks/api/usePortfolioApi";
import { formatMoney, formatPercentSigned } from "../../formatting/money";
import type { IncomeGrowthRow, IncomeRow } from "../../api/types";
import styles from "./IncomePage.module.css";

/**
 * The Income screen (Phase 5.7 remainder): how much the portfolio has
 * generated in dividends, distributions, and interest, and whether that
 * income is growing -- entirely from Phase 4's existing income analytics
 * (getIncome/getIncomeGrowth/getTrailingIncomeYield/getForwardIncomeYield).
 * No income figure here is summed or derived client-side; each yearly row
 * is one backend-computed record, and trailing/forward yield are each a
 * single Metric the backend already decided is available or not.
 */
export function IncomePage() {
  const income = useIncome("yearly");
  const growth = useIncomeGrowth();
  const yieldData = useIncomeYield();
  const coverage = useDataCoverage();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Income</h1>
        <p className={styles.description}>
          Dividends, distributions, and interest the portfolio has generated, by year.
        </p>
      </header>

      <Card elevation="raised">
        <SectionHeader title="Income yield" />
        <QueryBoundary query={yieldData} loading={<Skeleton height={80} />}>
          {(y) => (
            <div className={styles.statRow}>
              <MetricValue
                label="Trailing yield"
                value={y.trailing.available && y.trailing.value != null ? formatPercentSigned(y.trailing.value) : null}
                rawValue={y.trailing.value}
                unavailableReason={!y.trailing.available ? (y.trailing.reason ?? "Not available") : undefined}
                meta={<DataQualityBadge quality={y.trailing.data_quality} />}
              />
              <MetricValue
                label="Forward yield"
                value={y.forward.available && y.forward.value != null ? formatPercentSigned(y.forward.value) : null}
                rawValue={y.forward.value}
                unavailableReason={!y.forward.available ? (y.forward.reason ?? "Not available") : undefined}
                meta={<DataQualityBadge quality={y.forward.data_quality} />}
              />
            </div>
          )}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Income by year" />
        <QueryBoundary
          query={income}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="No income recorded yet."
        >
          {(rows) => <IncomeTable rows={rows} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Income growth" subtitle="Year-over-year change in gross income" />
        <QueryBoundary
          query={growth}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="Not enough years of income history to show growth yet."
        >
          {(rows) => <GrowthTable rows={rows} />}
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

function IncomeTable({ rows }: { rows: IncomeRow[] }) {
  const columns: Column<IncomeRow>[] = [
    { key: "period_end", header: "Year", render: (r) => r.period_end.slice(0, 4) },
    { key: "dividends", header: "Dividends", numeric: true, render: (r) => formatMoney(r.dividends) },
    { key: "distributions", header: "Distributions", numeric: true, render: (r) => formatMoney(r.distributions) },
    { key: "interests", header: "Interest", numeric: true, render: (r) => formatMoney(r.interests) },
    { key: "franking_credits", header: "Franking credits", numeric: true, render: (r) => formatMoney(r.franking_credits) },
    { key: "tax_withheld", header: "Tax withheld", numeric: true, render: (r) => formatMoney(r.tax_withheld) },
    { key: "net_income", header: "Net income", numeric: true, sortable: true, sortValue: (r) => Number(r.net_income), render: (r) => formatMoney(r.net_income) },
  ];
  return <Table columns={columns} rows={rows} rowKey={(r) => r.period_end} caption="Income by year" />;
}

function GrowthTable({ rows }: { rows: IncomeGrowthRow[] }) {
  const columns: Column<IncomeGrowthRow>[] = [
    { key: "year", header: "Year", render: (r) => r.year },
    { key: "gross_income", header: "Gross income", numeric: true, render: (r) => formatMoney(r.gross_income) },
    {
      key: "growth_pct", header: "Growth", numeric: true,
      render: (r) => (r.growth_pct == null ? "—" : formatPercentSigned(r.growth_pct)),
    },
    { key: "decomposition", header: "Basis", render: (r) => r.decomposition },
  ];
  return <Table columns={columns} rows={rows} rowKey={(r) => r.year} caption="Income growth by year" />;
}
