import type { Meta, StoryObj } from "@storybook/react-vite";

import { formatMoney, formatPercentPlain } from "../../formatting/money";
import { Table } from "./Table";

interface Row { code: string; units: string; marketValue: string; weight: string; }

const rows: Row[] = [
  { code: "VAS", units: "252.00", marketValue: "24386.04", weight: "0.371" },
  { code: "VGS", units: "204.00", marketValue: "25797.84", weight: "0.557" },
  { code: "VAF", units: "113.00", marketValue: "5104.21", weight: "0.072" },
];

const meta: Meta<typeof Table<Row>> = {
  title: "Design System/Table",
  component: Table<Row>,
};
export default meta;
type Story = StoryObj<typeof Table<Row>>;

export const Holdings: Story = {
  args: {
    caption: "Current holdings",
    rowKey: (r) => r.code,
    rows,
    columns: [
      { key: "code", header: "Security", render: (r) => r.code, sortable: true, sortValue: (r) => r.code },
      { key: "units", header: "Units", numeric: true, render: (r) => r.units },
      { key: "value", header: "Market value", numeric: true, sortable: true, sortValue: (r) => Number(r.marketValue), render: (r) => formatMoney(r.marketValue) },
      { key: "weight", header: "Weight", numeric: true, sortable: true, sortValue: (r) => Number(r.weight), render: (r) => formatPercentPlain(r.weight) },
    ],
  },
};
