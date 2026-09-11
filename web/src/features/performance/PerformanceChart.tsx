import { useMemo } from "react";

import { ChartContainer } from "../../components/charts/ChartContainer/ChartContainer";
import { TimeSeriesChart, type TimeSeriesPoint } from "../../components/charts/TimeSeriesChart/TimeSeriesChart";
import { Tabs } from "../../design-system/Tabs/Tabs";
import { usePeriodTabs } from "../../hooks/usePeriodTabs";
import { formatIndex } from "../../formatting/money";
import type { PerformancePeriod, PortfolioDailyPoint } from "../../api/types";
import styles from "./PerformanceChart.module.css";

const PERIOD_LABELS = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "INCEPTION"];
const PERIOD_DISPLAY: Record<string, string> = { INCEPTION: "MAX" };

export interface PerformanceChartProps {
  periods: PerformancePeriod[];
  history: PortfolioDailyPoint[];
  selected: string;
  onSelect: (value: string) => void;
}

/**
 * Sec 9-10's explicit distinction from the Overview's chart: this plots
 * `return_index` -- Phase 3's own chained performance index -- never
 * `total_value`. A dollar value curve and a return curve answer different
 * questions, and this dataset's return_index is the backend's authoritative
 * return series; nothing here derives a return from portfolio values.
 * `index_as_at` (also Phase 3's own field) marks whether a point was
 * actually computed that day or carried forward -- read directly into the
 * chart's quality channel, not re-derived.
 */
export function PerformanceChart({ periods, history, selected, onSelect }: PerformanceChartProps) {
  const tabs = usePeriodTabs(PERIOD_LABELS, periods).map((t) => ({ ...t, label: PERIOD_DISPLAY[t.label] ?? t.label }));
  const activePeriod = periods.find((p) => p.label === selected);
  const start = activePeriod?.start_date;
  const end = activePeriod?.end_date;

  const sliced = useMemo(
    () => (start && end ? history.filter((row) => row.date >= start && row.date <= end) : history),
    [history, start, end],
  );
  const points = useMemo<TimeSeriesPoint[]>(
    () =>
      sliced.map((row) => ({
        date: row.date,
        value: row.return_index ?? null,
        quality: row.index_as_at === row.date ? row.valuation_status : "estimated",
      })),
    [sliced],
  );

  return (
    <div>
      <Tabs items={tabs} value={selected} onChange={onSelect} aria-label="Performance history period" />
      <div className={styles.chartWrap}>
        {sliced.filter((r) => r.return_index !== null).length === 0 ? (
          <p className={styles.empty}>No return history available for this period yet.</p>
        ) : (
          <ChartContainer
            height={280}
            accessibleSummary={`Return index from ${sliced[0]?.date} to ${sliced[sliced.length - 1]?.date}. Dashed segments are carried-forward estimates, not newly-computed returns.`}
          >
            {({ width, height }) => (
              <TimeSeriesChart
                data={points} width={width} height={height}
                valueLabel="Return index" formatValue={formatIndex}
              />
            )}
          </ChartContainer>
        )}
      </div>
    </div>
  );
}
