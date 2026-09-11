import type { Meta, StoryObj } from "@storybook/react-vite";

import { ChartContainer } from "../ChartContainer/ChartContainer";
import { BarChart } from "./BarChart";

const meta: Meta<typeof BarChart> = { title: "Charts/BarChart", component: BarChart };
export default meta;
type Story = StoryObj<typeof BarChart>;

export const CalendarReturns: Story = {
  render: () => (
    <ChartContainer accessibleSummary="Annual returns from 2020 to 2026, ranging from -9.4% to +17.4%.">
      {({ width, height }) => (
        <BarChart
          valueLabel="Return"
          width={width}
          height={height}
          data={[
            { label: "2021", value: "0.174" },
            { label: "2022", value: "-0.094" },
            { label: "2023", value: "0.162" },
            { label: "2024", value: "0.122" },
            { label: "2025", value: "0.105" },
          ]}
        />
      )}
    </ChartContainer>
  ),
};

export const IncomeByYear: Story = {
  render: () => (
    <ChartContainer accessibleSummary="Annual income from 2020 to 2026, growing from $54 to $2,127.">
      {({ width, height }) => (
        <BarChart
          valueLabel="Income"
          width={width}
          height={height}
          data={[
            { label: "2021", value: "1072", tone: "neutral" },
            { label: "2022", value: "1232", tone: "neutral" },
            { label: "2023", value: "1154", tone: "neutral" },
            { label: "2024", value: "2127", tone: "neutral" },
          ]}
        />
      )}
    </ChartContainer>
  ),
};
