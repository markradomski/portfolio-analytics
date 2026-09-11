import { Badge } from "../../design-system/Badge/Badge";
import { DataQualityBadge } from "../../components/data-quality/DataQualityBadge/DataQualityBadge";
import { Table, type Column } from "../../design-system/Table/Table";
import { formatPercentSigned } from "../../formatting/money";
import type { CalendarPerformanceRow } from "../../api/types";

export interface CalendarPerformanceTableProps {
  rows: CalendarPerformanceRow[];
  /** The most recent date the backend has actually valued the portfolio
   * as at -- used only to label the current, still-running year as
   * partial (a presentation label, not a return calculation). */
  asAt: string | null;
}

/**
 * Sec 17: yearly TWRR/XIRR, using only what calendar_performance() already
 * computed per period. A year that hasn't finished yet (its label matches
 * the year of the backend's own `as_at`) is visibly marked partial rather
 * than presented as a completed year's return.
 */
export function CalendarPerformanceTable({ rows, asAt }: CalendarPerformanceTableProps) {
  const currentYear = asAt ? asAt.slice(0, 4) : null;
  const isCompleteYear = (period: string) => period !== currentYear;

  const columns: Column<CalendarPerformanceRow>[] = [
    {
      key: "period", header: "Year",
      render: (r) => (
        <>
          {r.period}
          {!isCompleteYear(r.period) && (
            <Badge tone="neutral" withDot={false}> Year to date</Badge>
          )}
        </>
      ),
    },
    {
      key: "twrr", header: "TWRR", numeric: true,
      render: (r) =>
        r.twrr != null ? (
          <span data-sign={Number(r.twrr) >= 0 ? "positive" : "negative"}>{formatPercentSigned(r.twrr)}</span>
        ) : "—",
    },
    { key: "xirr", header: "XIRR", numeric: true, render: (r) => (r.xirr != null ? formatPercentSigned(r.xirr) : "—") },
    { key: "quality", header: "Data quality", render: (r) => <DataQualityBadge quality={r.valuation_status} /> },
  ];

  return <Table columns={columns} rows={rows} rowKey={(r) => r.period} caption="Calendar-year performance" />;
}
