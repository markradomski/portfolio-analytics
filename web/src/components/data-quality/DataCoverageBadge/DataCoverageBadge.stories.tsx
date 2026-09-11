import type { Meta, StoryObj } from "@storybook/react-vite";

import { DataCoverageBadge } from "./DataCoverageBadge";

const meta: Meta<typeof DataCoverageBadge> = { title: "Data Quality/DataCoverageBadge", component: DataCoverageBadge };
export default meta;
type Story = StoryObj<typeof DataCoverageBadge>;

export const QuarterlyCoverage: Story = {
  args: {
    coverage: {
      valuation_start: "2020-09-30", valuation_end: "2026-06-30", valuation_observation_count: 24,
      transaction_start: "2020-09-07", transaction_end: "2026-05-06", price_observation_count: 24,
      missing_valuation_count: 108, actual_observation_count: 19, carried_forward_observation_count: 1920,
      estimated_observation_count: 76, unavailable_observation_count: 108,
    },
  },
};
