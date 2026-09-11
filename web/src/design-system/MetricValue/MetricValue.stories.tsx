import type { Meta, StoryObj } from "@storybook/react-vite";

import { Badge } from "../Badge/Badge";
import { MetricValue } from "./MetricValue";

const meta: Meta<typeof MetricValue> = {
  title: "Design System/MetricValue",
  component: MetricValue,
};
export default meta;
type Story = StoryObj<typeof MetricValue>;

export const PortfolioValue: Story = {
  args: { label: "Portfolio value", value: "$118.42", size: "large" },
};

export const PositiveReturn: Story = {
  args: {
    label: "Total return", value: "+18.4%", rawValue: "0.184",
    meta: <Badge tone="quality-calculated" withDot={false}>23 quarterly observations</Badge>,
  },
};

export const NegativeReturn: Story = {
  args: { label: "2022 return", value: "-9.4%", rawValue: "-0.094" },
};

export const Unavailable: Story = {
  args: {
    label: "Sharpe ratio", value: null,
    unavailableReason: "A risk-free rate has not been configured.",
  },
};
