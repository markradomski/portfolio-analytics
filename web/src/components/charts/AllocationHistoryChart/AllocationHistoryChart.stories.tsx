import type { Meta, StoryObj } from "@storybook/react-vite";

import { AllocationHistoryChart } from "./AllocationHistoryChart";

const meta: Meta<typeof AllocationHistoryChart> = {
  title: "Charts/AllocationHistoryChart", component: AllocationHistoryChart,
};
export default meta;
type Story = StoryObj<typeof AllocationHistoryChart>;

const LABELS = {
  australian_equities: "Australian equities", international_equities: "International equities",
  bonds: "Bonds", cash: "Cash",
};

export const AssetClassOverTime: Story = {
  args: {
    width: 640, height: 280, categoryLabels: LABELS,
    data: [
      { date: "2021-12-31", total: "40000", weights: { australian_equities: "20000", bonds: "12000", cash: "8000" },
        allocation_pct: { australian_equities: "0.5", bonds: "0.3", cash: "0.2" } },
      { date: "2022-12-31", total: "36000", weights: { australian_equities: "18000", bonds: "10800", cash: "7200" },
        allocation_pct: { australian_equities: "0.5", bonds: "0.3", cash: "0.2" } },
      { date: "2023-12-31", total: "50000", weights: { australian_equities: "30000", international_equities: "10000", cash: "10000" },
        allocation_pct: { australian_equities: "0.6", international_equities: "0.2", cash: "0.2" } },
      { date: "2024-12-31", total: "58000", weights: { australian_equities: "34800", international_equities: "17400", cash: "5800" },
        allocation_pct: { australian_equities: "0.6", international_equities: "0.3", cash: "0.1" } },
    ],
  },
};

export const SingleObservation: Story = {
  args: {
    width: 640, height: 280, categoryLabels: LABELS,
    data: [
      { date: "2024-12-31", total: "1000", weights: { cash: "1000" }, allocation_pct: { cash: "1" } },
    ],
  },
};

export const Empty: Story = {
  args: { width: 640, height: 280, data: [] },
};
