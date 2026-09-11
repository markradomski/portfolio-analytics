import type { Meta, StoryObj } from "@storybook/react-vite";

import { Badge } from "./Badge";

const meta: Meta<typeof Badge> = {
  title: "Design System/Badge",
  component: Badge,
};
export default meta;
type Story = StoryObj<typeof Badge>;

export const Positive: Story = { args: { tone: "positive", children: "+18.4%" } };
export const Negative: Story = { args: { tone: "negative", children: "-4.2%" } };
export const Warning: Story = { args: { tone: "warning", children: "Limited" } };
export const Neutral: Story = { args: { tone: "neutral", children: "Neutral" } };
export const Accent: Story = { args: { tone: "accent", children: "New" } };

export const QualityActual: Story = { args: { tone: "quality-actual", children: "Actual" } };
export const QualityCalculated: Story = { args: { tone: "quality-calculated", children: "Calculated" } };
export const QualityEstimated: Story = { args: { tone: "quality-estimated", children: "Estimated" } };
export const QualityLimited: Story = { args: { tone: "quality-limited", children: "Limited sample" } };
export const QualityUnavailable: Story = { args: { tone: "quality-unavailable", children: "Unavailable" } };

export const AllDataQualityTones: Story = {
  render: () => (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <Badge tone="quality-actual">Actual</Badge>
      <Badge tone="quality-calculated">Calculated</Badge>
      <Badge tone="quality-estimated">Estimated</Badge>
      <Badge tone="quality-limited">Limited</Badge>
      <Badge tone="quality-unavailable">Unavailable</Badge>
    </div>
  ),
};
