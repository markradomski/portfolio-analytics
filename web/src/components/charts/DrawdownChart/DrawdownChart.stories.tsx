import type { Meta, StoryObj } from "@storybook/react-vite";

import { ChartContainer } from "../ChartContainer/ChartContainer";
import { DrawdownChart } from "./DrawdownChart";

function synthetic() {
  const points = [];
  const values = [0, -2, -5, -9, -14.4, -12, -8, -4, 0, 0];
  for (let i = 0; i < values.length; i++) {
    points.push({ date: new Date(2021, 11 + i, 31).toISOString().slice(0, 10), drawdownPct: String(values[i] / 100) });
  }
  return points;
}

const meta: Meta<typeof DrawdownChart> = { title: "Charts/DrawdownChart", component: DrawdownChart };
export default meta;
type Story = StoryObj<typeof DrawdownChart>;

export const Default: Story = {
  render: () => (
    <ChartContainer accessibleSummary="Portfolio drawdown from December 2021, reaching a maximum of -14.4% before recovering.">
      {({ width, height }) => (
        <DrawdownChart
          data={synthetic()}
          episodes={[{ peakDate: "2021-12-31", troughDate: "2022-09-30", recoveryDate: "2023-12-31" }]}
          width={width}
          height={height}
        />
      )}
    </ChartContainer>
  ),
};
