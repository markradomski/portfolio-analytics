import type { Meta, StoryObj } from "@storybook/react-vite";

import { ChartContainer } from "../ChartContainer/ChartContainer";
import { TimeSeriesChart, type TimeSeriesPoint } from "./TimeSeriesChart";

function synthetic(): TimeSeriesPoint[] {
  // 2 real quarterly observations with a long carried-forward stretch in
  // between -- exactly this dataset's real shape (sec 9).
  const points: TimeSeriesPoint[] = [];
  let value = 55000;
  for (let i = 0; i < 90; i++) {
    const date = new Date(2024, 5, 30 + i);
    const isQuarterEnd = i === 0 || i === 89;
    if (isQuarterEnd) value += 6500;
    points.push({
      date: date.toISOString().slice(0, 10),
      value: String(value),
      quality: isQuarterEnd ? "calculated" : "estimated",
    });
  }
  return points;
}

const meta: Meta<typeof TimeSeriesChart> = {
  title: "Charts/TimeSeriesChart",
  component: TimeSeriesChart,
};
export default meta;
type Story = StoryObj<typeof TimeSeriesChart>;

export const PortfolioValue: Story = {
  render: () => (
    <ChartContainer accessibleSummary="Portfolio value from 30 June 2024 to 30 September 2024, rising from $55,000 to $61,500.">
      {({ width, height }) => (
        <TimeSeriesChart data={synthetic()} width={width} height={height} valueLabel="Portfolio value" />
      )}
    </ChartContainer>
  ),
};

export const WithContributionsAndWithdrawals: Story = {
  render: () => (
    <ChartContainer accessibleSummary="Portfolio value with a contribution marker and a withdrawal marker overlaid.">
      {({ width, height }) => (
        <TimeSeriesChart
          data={synthetic()}
          flows={[
            { date: "2024-07-20", amount: "5000" },
            { date: "2024-08-25", amount: "-2000" },
          ]}
          width={width}
          height={height}
          valueLabel="Portfolio value"
        />
      )}
    </ChartContainer>
  ),
};

export const WithUnavailableGap: Story = {
  render: () => {
    const data = synthetic();
    for (let i = 30; i < 45; i++) data[i] = { ...data[i], value: null, quality: "unavailable" };
    return (
      <ChartContainer accessibleSummary="Portfolio value with a genuine data gap in the middle -- no fabricated point.">
        {({ width, height }) => (
          <TimeSeriesChart data={data} width={width} height={height} valueLabel="Portfolio value" />
        )}
      </ChartContainer>
    );
  },
};
