import type { Meta, StoryObj } from "@storybook/react-vite";

import { Button } from "../../../design-system/Button/Button";
import { UnavailableMetric } from "./UnavailableMetric";

const meta: Meta<typeof UnavailableMetric> = { title: "Data Quality/UnavailableMetric", component: UnavailableMetric };
export default meta;
type Story = StoryObj<typeof UnavailableMetric>;

export const SharpeRatio: Story = {
  args: { title: "Sharpe ratio", reason: "A risk-free rate has not been configured." },
};

export const BenchmarkComparison: Story = {
  args: {
    title: "Benchmark comparison",
    reason: "Compare your portfolio against a benchmark once one has been added.",
    action: <Button size="small">Add a benchmark</Button>,
  },
};

export const SectorAllocation: Story = {
  args: { title: "Sector allocation", reason: "Sector classifications aren't currently available for these holdings." },
};
