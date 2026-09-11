import type { Meta, StoryObj } from "@storybook/react-vite";

import { AllocationChart } from "./AllocationChart";

const meta: Meta<typeof AllocationChart> = { title: "Charts/AllocationChart", component: AllocationChart };
export default meta;
type Story = StoryObj<typeof AllocationChart>;

export const AssetClass: Story = {
  args: {
    width: 640,
    segments: [
      { key: "aus", label: "Australian equities", value: "26396", weight: "0.3707", kind: "known" },
      { key: "intl", label: "International equities", value: "39688", weight: "0.5573", kind: "known" },
      { key: "bonds", label: "Bonds", value: "5104", weight: "0.0717", kind: "known" },
      { key: "cash", label: "Cash", value: "22", weight: "0.0003", kind: "known" },
    ],
  },
};

export const WithUnknownSecurity: Story = {
  args: {
    width: 640,
    segments: [
      { key: "aus", label: "Australian equities", value: "26396", weight: "0.85", kind: "known" },
      { key: "unknown", label: "Unknown", value: "4600", weight: "0.15", kind: "unknown" },
    ],
  },
};
