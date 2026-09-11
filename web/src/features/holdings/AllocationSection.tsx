import { useState } from "react";

import { AllocationChart, type AllocationSegment } from "../../components/charts/AllocationChart/AllocationChart";
import { UnavailableMetric } from "../../components/data-quality/UnavailableMetric/UnavailableMetric";
import { Tabs } from "../../design-system/Tabs/Tabs";
import { Table, type Column } from "../../design-system/Table/Table";
import { formatMoney, formatPercentPlain } from "../../formatting/money";
import type { AllocationResult } from "../../api/types";
import styles from "./HoldingsPage.module.css";

const ASSET_CLASS_LABELS: Record<string, string> = {
  australian_equities: "Australian equities", international_equities: "International equities",
  bonds: "Bonds", property: "Property", cash: "Cash", other: "Other", unknown: "Unknown",
};

export interface AllocationSectionProps {
  bySecurity: AllocationResult;
  byAssetClass: AllocationResult;
}

interface Row {
  key: string;
  label: string;
  value: string;
  weight: string | null;
  unknown: boolean;
}

function toRows(result: AllocationResult, labels: Record<string, string>): Row[] {
  if (!result.weights) return [];
  return Object.entries(result.weights).map(([key, value]) => ({
    key, label: labels[key] ?? key, value, weight: result.allocation_pct?.[key] ?? null,
    unknown: key === "unknown",
  }));
}

/**
 * Sec 6-8: allocation by security and by asset class, using the exact
 * proportions the backend already computed. Cash is a first-class
 * component here (never folded into "missing") whenever the selected
 * dimension's response includes it; when the backend reports the whole
 * dimension unavailable (e.g. a fully-divested portfolio with nothing to
 * allocate), that is shown explicitly, never as a fabricated 0%.
 */
export function AllocationSection({ bySecurity, byAssetClass }: AllocationSectionProps) {
  const [dimension, setDimension] = useState<"security" | "asset_class">("asset_class");
  const active = dimension === "security" ? bySecurity : byAssetClass;
  const labels = dimension === "security" ? {} : ASSET_CLASS_LABELS;

  if (active.status === "unavailable" || !active.weights) {
    return (
      <div>
        <Tabs
          aria-label="Allocation dimension"
          value={dimension}
          onChange={(v) => setDimension(v as typeof dimension)}
          items={[{ value: "asset_class", label: "By asset class" }, { value: "security", label: "By security" }]}
        />
        <div className={styles.sectionBody}>
          <UnavailableMetric title="Allocation" reason={active.note ?? "No allocation computed for this date."} />
        </div>
      </div>
    );
  }

  const rows = toRows(active, labels).sort((a, b) => Number(b.value) - Number(a.value));
  const segments: AllocationSegment[] = rows.map((r) => ({
    key: r.key, label: r.label, value: r.value, weight: r.weight, kind: r.unknown ? "unknown" : "known",
  }));

  const columns: Column<Row>[] = [
    { key: "label", header: "Component", render: (r) => r.label },
    {
      key: "value", header: "Value", numeric: true, sortable: true,
      sortValue: (r) => Number(r.value), render: (r) => formatMoney(r.value),
    },
    {
      key: "weight", header: "Weight", numeric: true, sortable: true,
      sortValue: (r) => (r.weight ? Number(r.weight) : -1),
      render: (r) => (r.weight === null ? "Unavailable" : formatPercentPlain(r.weight)),
    },
  ];

  return (
    <div>
      <Tabs
        aria-label="Allocation dimension"
        value={dimension}
        onChange={(v) => setDimension(v as typeof dimension)}
        items={[{ value: "asset_class", label: "By asset class" }, { value: "security", label: "By security" }]}
      />
      <div className={styles.sectionBody}>
        <AllocationChart width={640} segments={segments} />
        <Table columns={columns} rows={rows} rowKey={(r) => r.key} caption={`Allocation ${dimension === "security" ? "by security" : "by asset class"}`} />
      </div>
    </div>
  );
}
