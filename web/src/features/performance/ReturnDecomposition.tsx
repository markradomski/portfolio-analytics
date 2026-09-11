import { useState } from "react";

import { Badge } from "../../design-system/Badge/Badge";
import { formatMoneySigned } from "../../formatting/money";
import type { AttributionReconciliationPair, AttributionTree } from "../../api/types";
import styles from "./PerformancePage.module.css";

export interface ReturnDecompositionProps {
  attribution: AttributionTree;
  reconciliation?: AttributionReconciliationPair;
}

const STATUS_TONE = { PASS: "positive", FAIL: "negative", LIMITED: "warning" } as const;
const STATUS_LABEL = { PASS: "Explained", FAIL: "Discrepancy found", LIMITED: "Limited" } as const;

/**
 * Sec 11-12: where portfolio change actually came from, using only the
 * categories the attribution tree itself provides (never a category
 * invented to fill out the list), plus a compact, disclosable
 * reconciliation result using Phase 4's own exact vocabulary --
 * attributed_change/actual_change/residual/tolerance/reconciliation_status
 * -- never a re-terminologised version of it.
 */
export function ReturnDecomposition({ attribution, reconciliation }: ReturnDecompositionProps) {
  const [expanded, setExpanded] = useState(false);
  // Every row is a field the attribution tree already provides verbatim --
  // "Income" is never a frontend sum of dividends+distributions+interest,
  // since that would be a new calculation the backend didn't hand over;
  // each sub-line is shown separately instead (sec 11).
  const rows = [
    { label: "Capital growth", value: attribution.investment_return.capital_appreciation.total },
    { label: "Dividends", value: attribution.investment_return.income.dividends },
    { label: "Distributions", value: attribution.investment_return.income.distributions },
    { label: "Interest", value: attribution.investment_return.income.interest },
    { label: "External cash flows", value: attribution.external_cash_flows },
    { label: "Fees", value: attribution.fees, negative: true },
    { label: "Taxes", value: attribution.taxes, negative: true },
  ].filter((r) => r.value !== null && r.value !== undefined && Number(r.value) !== 0);

  return (
    <div>
      <dl className={styles.decompositionList}>
        {rows.map((row) => (
          <div key={row.label} className={styles.decompositionRow}>
            <dt>{row.label}</dt>
            <dd className={row.negative ? styles.negativeFigure : undefined}>
              {formatMoneySigned(row.negative && Number(row.value) > 0 ? `-${row.value}` : row.value)}
            </dd>
          </div>
        ))}
      </dl>

      {reconciliation && (
        <div className={styles.reconciliation}>
          <button
            type="button"
            className={styles.reconciliationTrigger}
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
          >
            <Badge tone={STATUS_TONE[reconciliation.attribution.reconciliation_status]} withDot={false}>
              {STATUS_LABEL[reconciliation.attribution.reconciliation_status]}
            </Badge>
            <span>Performance reconciliation</span>
          </button>
          {expanded && (
            <dl className={styles.reconciliationDetail}>
              <div>
                <dt>Attributed change</dt>
                <dd>{formatMoneySigned(reconciliation.attribution.attributed_change)}</dd>
              </div>
              <div>
                <dt>Actual change</dt>
                <dd>{formatMoneySigned(reconciliation.attribution.actual_change)}</dd>
              </div>
              <div>
                <dt>Residual</dt>
                <dd>{formatMoneySigned(reconciliation.attribution.residual)}</dd>
              </div>
              <div>
                <dt>Tolerance</dt>
                <dd>{formatMoneySigned(reconciliation.attribution.tolerance)}</dd>
              </div>
            </dl>
          )}
        </div>
      )}
    </div>
  );
}
