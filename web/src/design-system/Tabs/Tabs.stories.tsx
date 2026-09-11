import { useState } from "react";

import type { Meta, StoryObj } from "@storybook/react-vite";

import { Tabs } from "./Tabs";

const meta: Meta<typeof Tabs> = {
  title: "Design System/Tabs",
  component: Tabs,
};
export default meta;
type Story = StoryObj<typeof Tabs>;

export const PeriodSelector: Story = {
  render: () => {
    const [value, setValue] = useState("1Y");
    return (
      <Tabs
        aria-label="Performance period"
        value={value}
        onChange={setValue}
        items={[
          { value: "1D", label: "1D", disabled: true, disabledReason: "Consecutive valuations are 90 days apart; no daily data" },
          { value: "1M", label: "1M", disabled: true, disabledReason: "Insufficient daily observations" },
          { value: "1Y", label: "1Y" },
          { value: "3Y", label: "3Y" },
          { value: "5Y", label: "5Y" },
          { value: "MAX", label: "MAX" },
        ]}
      />
    );
  },
};
