import type { Meta, StoryObj } from "@storybook/react-vite";

import { DataQualityBadge } from "./DataQualityBadge";

const meta: Meta<typeof DataQualityBadge> = { title: "Data Quality/DataQualityBadge", component: DataQualityBadge };
export default meta;
type Story = StoryObj<typeof DataQualityBadge>;

export const AllStates: Story = {
  render: () => (
    <div style={{ display: "flex", gap: 8 }}>
      <DataQualityBadge quality="actual" />
      <DataQualityBadge quality="calculated" />
      <DataQualityBadge quality="estimated" />
      <DataQualityBadge quality="limited" label="Limited · 23 obs." />
      <DataQualityBadge quality="unavailable" />
    </div>
  ),
};
