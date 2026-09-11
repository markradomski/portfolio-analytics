import { Card } from "../../design-system/Card/Card";
import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { SectionHeader } from "../../design-system/SectionHeader/SectionHeader";
import { DataCoverageBadge } from "../../components/data-quality/DataCoverageBadge/DataCoverageBadge";
import { DataQualityBadge } from "../../components/data-quality/DataQualityBadge/DataQualityBadge";
import { QueryBoundary } from "../../components/common/QueryBoundary/QueryBoundary";
import { Skeleton } from "../../components/common/Skeleton/Skeleton";
import { UnavailableMetric } from "../../components/data-quality/UnavailableMetric/UnavailableMetric";
import {
  useDataCoverage, useDrawdowns, useHighWaterMark, useRiskBenchmark, useRiskMetrics,
} from "../../hooks/api/usePortfolioApi";
import { formatDate, formatMoney, formatPercentSigned } from "../../formatting/money";
import type {
  BenchmarkComparison, DrawdownAnalytics, HighWaterMarkStatus, RiskMetrics as RiskMetricsType,
} from "../../api/types";
import styles from "./RiskPage.module.css";

/**
 * The Risk screen (Phase 5.7 remainder): volatility and risk-adjusted
 * return, drawdown history, distance from the portfolio's high-water mark,
 * and a benchmark comparison -- each a Metric the backend has already
 * decided is available or not (sec 26). Sharpe/Sortino are expected
 * unavailable without a configured risk-free rate, and benchmark
 * comparison is expected unavailable without a registered benchmark:
 * both render through UnavailableMetric with the backend's own reason,
 * never a fabricated zero.
 */
export function RiskPage() {
  const risk = useRiskMetrics();
  const drawdowns = useDrawdowns();
  const highWaterMark = useHighWaterMark();
  const benchmark = useRiskBenchmark("1Y");
  const coverage = useDataCoverage();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Risk</h1>
        <p className={styles.description}>
          Volatility, drawdowns, and how far the portfolio sits from its own historical peak.
        </p>
      </header>

      <Card elevation="raised">
        <SectionHeader title="Risk metrics" />
        <QueryBoundary query={risk} loading={<Skeleton height={100} />}>
          {(r) => <RiskMetricsRow risk={r} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Drawdowns" viewAllHref="/history" viewAllLabel="View history" />
        <QueryBoundary query={drawdowns} loading={<Skeleton height={100} />}>
          {(d) => <DrawdownRow drawdowns={d} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="High-water mark" />
        <QueryBoundary query={highWaterMark} loading={<Skeleton height={100} />}>
          {(h) => <HighWaterMarkRow status={h} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionHeader title="Benchmark comparison" subtitle="1 year" />
        <QueryBoundary query={benchmark} loading={<Skeleton height={80} />}>
          {(b) => <BenchmarkRow comparison={b} />}
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

function RiskMetricsRow({ risk }: { risk: RiskMetricsType }) {
  return (
    <div className={styles.statRow}>
      <MetricValue
        label="Volatility (annualised)"
        value={risk.volatility.available && risk.volatility.value != null ? formatPercentSigned(risk.volatility.value) : null}
        rawValue={risk.volatility.value}
        unavailableReason={!risk.volatility.available ? (risk.volatility.reason ?? "Not available") : undefined}
        meta={<DataQualityBadge quality={risk.volatility.data_quality} />}
      />
      <MetricValue
        label="Sharpe ratio"
        value={risk.sharpe_ratio.available && risk.sharpe_ratio.value != null ? risk.sharpe_ratio.value : null}
        rawValue={null}
        unavailableReason={!risk.sharpe_ratio.available ? (risk.sharpe_ratio.reason ?? "Not available") : undefined}
        meta={<DataQualityBadge quality={risk.sharpe_ratio.data_quality} />}
      />
      <MetricValue
        label="Sortino ratio"
        value={risk.sortino_ratio.available && risk.sortino_ratio.value != null ? risk.sortino_ratio.value : null}
        rawValue={null}
        unavailableReason={!risk.sortino_ratio.available ? (risk.sortino_ratio.reason ?? "Not available") : undefined}
        meta={<DataQualityBadge quality={risk.sortino_ratio.data_quality} />}
      />
    </div>
  );
}

function DrawdownRow({ drawdowns: d }: { drawdowns: DrawdownAnalytics }) {
  if (d.maximum_drawdown_pct == null) {
    return <UnavailableMetric title="Maximum drawdown" reason="No drawdown episodes recorded yet." />;
  }
  return (
    <div className={styles.statRow}>
      <MetricValue label="Maximum drawdown" value={formatPercentSigned(d.maximum_drawdown_pct)} rawValue={d.maximum_drawdown_pct} />
      <MetricValue
        label="Average drawdown"
        value={d.average_drawdown_pct == null ? null : formatPercentSigned(d.average_drawdown_pct)}
        rawValue={d.average_drawdown_pct}
        unavailableReason={d.average_drawdown_pct == null ? "Not available" : undefined}
      />
      <MetricValue label="Episodes" value={String(d.episode_count)} />
      {d.longest_underwater_days != null && (
        <MetricValue label="Longest underwater" value={`${d.longest_underwater_days} days`} />
      )}
      {d.fastest_recovery_days != null && (
        <MetricValue label="Fastest recovery" value={`${d.fastest_recovery_days} days`} />
      )}
    </div>
  );
}

function HighWaterMarkRow({ status }: { status: HighWaterMarkStatus }) {
  return (
    <div className={styles.statRow}>
      <MetricValue
        label="Current value"
        value={status.current_value == null ? null : formatMoney(status.current_value)}
        rawValue={status.current_value}
        unavailableReason={status.current_value == null ? "Not available" : undefined}
      />
      <MetricValue label="High-water mark" value={formatMoney(status.high_water_mark)} rawValue={status.high_water_mark} />
      <MetricValue
        label="Distance from high"
        value={status.distance_from_high == null ? null : formatMoney(status.distance_from_high)}
        rawValue={status.distance_from_high}
        unavailableReason={status.distance_from_high == null ? "Not available" : undefined}
      />
      <MetricValue
        label="Distance from high %"
        value={status.distance_from_high_pct == null ? null : formatPercentSigned(status.distance_from_high_pct)}
        rawValue={status.distance_from_high_pct}
        unavailableReason={status.distance_from_high_pct == null ? "Not available" : undefined}
      />
      {status.days_since_high != null && (
        <MetricValue label="Days since high" value={`${status.days_since_high} days`} />
      )}
      <MetricValue label="As at" value={formatDate(status.date)} />
    </div>
  );
}

function BenchmarkRow({ comparison }: { comparison: BenchmarkComparison }) {
  if (comparison.relative_return == null) {
    return (
      <UnavailableMetric
        title="Benchmark comparison"
        reason={comparison.note ?? "No benchmark registered."}
      />
    );
  }
  return (
    <div className={styles.statRow}>
      <MetricValue
        label="Portfolio return"
        value={comparison.portfolio_return == null ? null : formatPercentSigned(comparison.portfolio_return)}
        rawValue={comparison.portfolio_return}
        unavailableReason={comparison.portfolio_return == null ? "Not available" : undefined}
      />
      <MetricValue
        label={comparison.benchmark_name ? `${comparison.benchmark_name} return` : "Benchmark return"}
        value={comparison.benchmark_return == null ? null : formatPercentSigned(comparison.benchmark_return)}
        rawValue={comparison.benchmark_return}
        unavailableReason={comparison.benchmark_return == null ? "Not available" : undefined}
      />
      <MetricValue
        label="Relative return"
        value={formatPercentSigned(comparison.relative_return)}
        rawValue={comparison.relative_return}
        size="large"
      />
      {comparison.methodology_mismatch && (
        <p className={styles.note}>
          Portfolio and benchmark returns use different methodologies ({comparison.portfolio_methodology} vs{" "}
          {comparison.benchmark_methodology ?? "unknown"}); the relative figure should be read as indicative only.
        </p>
      )}
    </div>
  );
}
