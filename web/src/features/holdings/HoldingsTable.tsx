import { Link } from "react-router-dom";

import { Table, type Column } from "../../design-system/Table/Table";
import { formatMoney, formatMoneySigned, formatPercentPlain, formatPercentSigned } from "../../formatting/money";
import type { HoldingRow, UnrealisedGainSnapshot } from "../../api/types";
import styles from "./HoldingsTable.module.css";

export interface HoldingsTableRow {
  code: string;
  security_id: string;
  market_value: string | null;
  allocation_pct: string | null;
  unrealised_gain: string | null;
  unrealised_gain_pct: string | null;
  data_quality: HoldingRow["valuation_status"];
}

export interface HoldingsTableProps {
  holdings: HoldingRow[];
  gains: UnrealisedGainSnapshot[];
}

/**
 * Sec 9-10: the primary holdings table. Gain % is read directly from
 * gains/unrealised (UnrealisedGainSnapshot.unrealised_gain_pct) -- never
 * derived from cost basis and market value client-side, even though both
 * are visible on the row; the backend's own figure is authoritative and
 * the two are joined by security code (a presentation join, not a
 * calculation). Sortable by value, weight, gain and gain % via the shared
 * Table component's native aria-sort semantics. A row links to
 * /holdings/:code for security detail.
 */
export function HoldingsTable({ holdings, gains }: HoldingsTableProps) {
  const gainByCode = new Map(gains.map((g) => [g.code, g]));
  const rows: HoldingsTableRow[] = holdings.map((h) => {
    const gain = gainByCode.get(h.code);
    return {
      code: h.code, security_id: h.security_id, market_value: h.market_value ?? null,
      allocation_pct: h.allocation_pct ?? null,
      unrealised_gain: gain?.unrealised_gain ?? h.unrealised_gain ?? null,
      unrealised_gain_pct: gain?.unrealised_gain_pct ?? null,
      data_quality: h.valuation_status,
    };
  });

  const columns: Column<HoldingsTableRow>[] = [
    {
      key: "code", header: "Security",
      render: (r) => <Link to={`/holdings/${r.code}`} className={styles.link}>{r.code}</Link>,
    },
    {
      key: "market_value", header: "Value", numeric: true, sortable: true,
      sortValue: (r) => Number(r.market_value ?? 0), render: (r) => formatMoney(r.market_value),
    },
    {
      key: "allocation_pct", header: "Weight", numeric: true, sortable: true,
      sortValue: (r) => Number(r.allocation_pct ?? 0),
      render: (r) => (r.allocation_pct === null ? "Unavailable" : formatPercentPlain(r.allocation_pct)),
    },
    {
      key: "unrealised_gain", header: "Gain", numeric: true, sortable: true,
      sortValue: (r) => Number(r.unrealised_gain ?? 0),
      render: (r) => (r.unrealised_gain === null ? "Unavailable" : formatMoneySigned(r.unrealised_gain)),
    },
    {
      key: "unrealised_gain_pct", header: "Gain %", numeric: true, sortable: true,
      sortValue: (r) => (r.unrealised_gain_pct ? Number(r.unrealised_gain_pct) : -Infinity),
      render: (r) => (r.unrealised_gain_pct === null ? "—" : formatPercentSigned(r.unrealised_gain_pct)),
    },
  ];

  return <Table columns={columns} rows={rows} rowKey={(r) => r.security_id} caption="Current holdings" />;
}
