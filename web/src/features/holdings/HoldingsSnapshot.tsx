import { MetricValue } from "../../design-system/MetricValue/MetricValue";
import { formatMoney, formatMoneySigned } from "../../formatting/money";
import type { ConcentrationSnapshot, PortfolioState } from "../../api/types";
import styles from "./HoldingsPage.module.css";

export interface HoldingsSnapshotProps {
  holdings: PortfolioState;
  concentration: ConcentrationSnapshot;
}

/**
 * Sec 3/5: the portfolio-level snapshot -- total value, holding count,
 * cash, and total unrealised gain. `unrealised_gain` here is the
 * portfolio-level figure PortfolioDailyPoint already carries (Phase 3's
 * own aggregate), never a frontend sum of the per-security unrealised
 * gains shown further down the page.
 */
export function HoldingsSnapshot({ holdings, concentration }: HoldingsSnapshotProps) {
  return (
    <div className={styles.summaryRow}>
      <MetricValue label="Total value" value={formatMoney(holdings.total_value)} size="large" />
      <MetricValue label="Holdings" value={String(concentration.holding_count)} />
      <MetricValue
        label="Cash"
        value={holdings.cash != null ? formatMoney(holdings.cash) : null}
        unavailableReason={holdings.cash == null ? "Not available for this date" : undefined}
      />
      <MetricValue
        label="Unrealised gain"
        value={holdings.unrealised_gain != null ? formatMoneySigned(holdings.unrealised_gain) : null}
        rawValue={holdings.unrealised_gain}
        unavailableReason={holdings.unrealised_gain == null ? "Not available for this date" : undefined}
      />
    </div>
  );
}
