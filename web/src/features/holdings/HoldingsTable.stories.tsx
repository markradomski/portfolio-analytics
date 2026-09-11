import { MemoryRouter } from "react-router-dom";
import type { Meta, StoryObj } from "@storybook/react-vite";

import { HoldingsTable } from "./HoldingsTable";
import type { HoldingRow, UnrealisedGainSnapshot } from "../../api/types";

const meta: Meta<typeof HoldingsTable> = {
  title: "Holdings/HoldingsTable", component: HoldingsTable,
  decorators: [(Story) => <MemoryRouter><Story /></MemoryRouter>],
};
export default meta;
type Story = StoryObj<typeof HoldingsTable>;

function holding(overrides: Partial<HoldingRow>): HoldingRow {
  return {
    date: "2024-09-30", security_id: overrides.code ?? "sec", code: "VAS", units: "100.0000", price: "90.00",
    market_value: "9000.00", cost_basis: "8000.00", unrealised_gain: "1000.00", allocation_pct: "0.4",
    asset_class: "australian_equities", valuation_status: "actual", price_as_at: "2024-09-30", ...overrides,
  };
}
function gain(overrides: Partial<UnrealisedGainSnapshot>): UnrealisedGainSnapshot {
  return {
    security_id: overrides.code ?? "sec", code: "VAS", asset_class: "australian_equities",
    market_value: "9000.00", cost_basis: "8000.00", unrealised_gain: "1000.00", unrealised_gain_pct: "0.125",
    ...overrides,
  };
}

export const ManyHoldings: Story = {
  args: {
    holdings: [
      holding({ security_id: "1", code: "VAS", market_value: "26396.00", allocation_pct: "0.37" }),
      holding({ security_id: "2", code: "VGS", market_value: "39688.00", allocation_pct: "0.56" }),
      holding({ security_id: "3", code: "VAF", market_value: "5104.00", allocation_pct: "0.07" }),
    ],
    gains: [
      gain({ security_id: "1", code: "VAS", unrealised_gain: "4200.00", unrealised_gain_pct: "0.19" }),
      gain({ security_id: "2", code: "VGS", unrealised_gain: "-1100.00", unrealised_gain_pct: "-0.027" }),
      gain({ security_id: "3", code: "VAF", unrealised_gain: "0", unrealised_gain_pct: "0" }),
    ],
  },
};

export const SingleHolding: Story = {
  args: {
    holdings: [holding({ security_id: "1", code: "VAS", market_value: "118.42", allocation_pct: "1" })],
    gains: [gain({ security_id: "1", code: "VAS", unrealised_gain: "0", unrealised_gain_pct: "0" })],
  },
};

export const NegativeGain: Story = {
  args: {
    holdings: [holding({ security_id: "1", code: "VGE", market_value: "8000.00", allocation_pct: "0.2" })],
    gains: [gain({ security_id: "1", code: "VGE", unrealised_gain: "-1500.00", unrealised_gain_pct: "-0.158" })],
  },
};

export const MissingGainData: Story = {
  args: {
    holdings: [holding({ security_id: "1", code: "WTC", market_value: "608.32", allocation_pct: "0.19", unrealised_gain: null })],
    gains: [],
  },
};

export const Empty: Story = { args: { holdings: [], gains: [] } };
