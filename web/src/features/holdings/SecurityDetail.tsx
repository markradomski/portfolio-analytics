import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ChartContainer } from "../../components/charts/ChartContainer/ChartContainer";
import { TimeSeriesChart, type TimeSeriesPoint } from "../../components/charts/TimeSeriesChart/TimeSeriesChart";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { Tabs } from "../../design-system/Tabs/Tabs";
import { useHoldingHistory } from "../../hooks/api/usePortfolioApi";
import { formatMoney, formatMoneySigned, formatPercentPlain, formatPercentSigned, formatUnits } from "../../formatting/money";
import type { HoldingRow, UnrealisedGainSnapshot } from "../../api/types";
import styles from "./HoldingsPage.module.css";

export interface SecurityDetailProps {
  code: string;
  /** The current holding row, if this security is still held today --
   * undefined for a fully-divested security, which is a legitimate state
   * (sec 15), not an error. */
  current: HoldingRow | undefined;
  currentGain: UnrealisedGainSnapshot | undefined;
}

const VIEWS = [
  { value: "value", label: "Value" },
  { value: "units", label: "Units" },
  { value: "weight", label: "Weight" },
] as const;

/**
 * Sec 11-12: the security detail view -- current snapshot where the
 * security is still held, plus its full historical value/units/weight
 * series regardless of whether it's currently held (sec 15/23: a
 * fully-divested security still has real history behind it). Reuses
 * TimeSeriesChart directly; a non-money series (units, weight) gets its
 * own formatter passed in rather than being labelled with a dollar sign.
 */
export function SecurityDetail({ code, current, currentGain }: SecurityDetailProps) {
  const [view, setView] = useState<(typeof VIEWS)[number]["value"]>("value");
  const history = useHoldingHistory(code);

  const points = useMemo<TimeSeriesPoint[] | undefined>(() => {
    if (!history.data) return undefined;
    const field = view === "value" ? "market_value" : view === "units" ? "units" : "allocation_pct";
    return history.data.map((row) => ({ date: row.date, value: row[field] ?? null, quality: row.valuation_status }));
  }, [history.data, view]);

  const formatValue = view === "value" ? formatMoney : view === "units" ? unitsOnly : (v: string) => formatPercentPlain(v);

  return (
    <div>
      <div className={styles.header}>
        <Link to="/holdings" className={styles.backLink}>← Back to holdings</Link>
        <h2 className={styles.securityTitle}>{code}</h2>
        {!current && (
          <p className={styles.periodPhrase}>No current holding — this security has been fully divested. Historical data below remains available.</p>
        )}
      </div>

      {current && (
        <div className={styles.summaryRow}>
          <MetricValue label="Units held" value={formatUnits(current.units)} />
          <MetricValue label="Market value" value={formatMoney(current.market_value)} />
          <MetricValue label="Portfolio weight" value={current.allocation_pct != null ? formatPercentPlain(current.allocation_pct) : null} unavailableReason={current.allocation_pct == null ? "Unavailable" : undefined} />
          <MetricValue label="Cost basis" value={formatMoney(current.cost_basis)} />
          <MetricValue
            label="Unrealised gain"
            value={(currentGain?.unrealised_gain ?? current.unrealised_gain) != null ? formatMoneySigned(currentGain?.unrealised_gain ?? current.unrealised_gain) : null}
            rawValue={currentGain?.unrealised_gain ?? current.unrealised_gain}
          />
          <MetricValue
            label="Gain %"
            value={currentGain?.unrealised_gain_pct != null ? formatPercentSigned(currentGain.unrealised_gain_pct) : null}
            rawValue={currentGain?.unrealised_gain_pct}
            unavailableReason={currentGain?.unrealised_gain_pct == null ? "Not available" : undefined}
          />
        </div>
      )}

      <Tabs items={VIEWS as unknown as { value: string; label: string }[]} value={view} onChange={(v) => setView(v as typeof view)} aria-label="Security history view" />

      <div className={styles.sectionBody}>
        <QueryBoundary
          query={history}
          loading={<Skeleton height={280} />}
          isEmpty={(rows) => rows.length === 0}
          emptyMessage="No historical data available for this security."
        >
          {() => (
            <ChartContainer
              height={280}
              accessibleSummary={`${code} ${view} history, ${points?.length ?? 0} observations.`}
            >
              {({ width, height }) => (
                <TimeSeriesChart
                  data={points ?? []} width={width} height={height}
                  valueLabel={VIEWS.find((v) => v.value === view)!.label}
                  formatValue={formatValue}
                />
              )}
            </ChartContainer>
          )}
        </QueryBoundary>
      </div>
    </div>
  );
}

function unitsOnly(value: string): string {
  return formatUnits(value).replace(/ units$/, "");
}
