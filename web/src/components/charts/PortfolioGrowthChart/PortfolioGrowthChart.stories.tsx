import type { Meta, StoryObj } from "@storybook/react-vite";

import { ChartContainer } from "../ChartContainer/ChartContainer";
import { ChartLegend } from "../ChartLegend/ChartLegend";
import { PortfolioGrowthChart } from "./PortfolioGrowthChart";
import type { PortfolioGrowthPoint } from "../../../api/types";

/**
 * All fixture data below is illustrative / test data only -- it is NOT a
 * real portfolio and the figures are hand-chosen to exercise a specific
 * geometry, not to represent any actual account.
 *
 * Step 9A.2 mental model these stories demonstrate:
 *   BLUE  = money put in     GREEN = money made
 *   RED   = money lost       LINE  = current balance
 * $0 is a hard visual floor -- no blue / green / red fill is ever drawn
 * below the axis, however negative the authoritative net-contribution
 * figure gets.
 */
function build(rows: Array<[string, number | null, number]>): PortfolioGrowthPoint[] {
  return rows.map(([date, value, netContrib]) => ({
    date,
    portfolio_value: value === null ? null : String(value),
    contributions: "0",
    withdrawals: "0",
    net_contributions: String(netContrib),
    investment_gain: value === null ? null : String(value - netContrib),
    period_investment_gain: null,
    cash_flow_events: [],
  }));
}

const LEGEND = (
  <ChartLegend
    items={[
      { label: "Total Balance", color: "var(--color-accent)", shape: "line" },
      { label: "Contributions", color: "var(--color-accent)", shape: "area", opacity: 0.28 },
      { label: "Investment Gain", color: "var(--color-positive)", shape: "area", opacity: 0.85 },
      { label: "Investment Loss", color: "var(--color-negative)", shape: "area", opacity: 0.85 },
    ]}
  />
);

const meta: Meta<typeof PortfolioGrowthChart> = {
  title: "Charts/PortfolioGrowthChart",
  component: PortfolioGrowthChart,
};
export default meta;
type Story = StoryObj<typeof PortfolioGrowthChart>;

function Frame({ points, summary }: { points: PortfolioGrowthPoint[]; summary: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 720 }}>
      {LEGEND}
      <ChartContainer accessibleSummary={summary}>
        {({ width, height }) => <PortfolioGrowthChart points={points} width={width} height={height} />}
      </ChartContainer>
    </div>
  );
}

// 1. Positive contributions + investment gain.
export const ContributionsAndGain: Story = {
  render: () => (
    <Frame
      summary="Illustrative: steady contributions, balance always above them -- a green gain band up to the balance line."
      points={build([
        ["2023-01-01", 10000, 10000],
        ["2023-07-01", 14000, 12000],
        ["2024-01-01", 20000, 15000],
        ["2024-07-01", 26000, 18000],
      ])}
    />
  ),
};

// 2. Positive contributions + investment loss.
export const ContributionsAndLoss: Story = {
  render: () => (
    <Frame
      summary="Illustrative: balance stays below contributions -- a red loss band between the balance line and the blue foundation."
      points={build([
        ["2023-01-01", 10000, 10000],
        ["2023-07-01", 11000, 13000],
        ["2024-01-01", 12500, 16000],
        ["2024-07-01", 13000, 18000],
      ])}
    />
  ),
};

// 3. Gain -> loss crossover.
export const GainToLossCrossover: Story = {
  render: () => (
    <Frame
      summary="Illustrative: the portfolio moves from ahead of contributions to behind them -- green then red."
      points={build([
        ["2023-01-01", 12000, 10000],
        ["2023-07-01", 15000, 12000],
        ["2024-01-01", 12000, 14000],
        ["2024-07-01", 11000, 16000],
      ])}
    />
  ),
};

// 4. Zero investment gain/loss.
export const ZeroGainOrLoss: Story = {
  render: () => (
    <Frame
      summary="Illustrative: balance tracks contributions exactly -- no green or red band."
      points={build([
        ["2023-01-01", 10000, 10000],
        ["2024-01-01", 15000, 15000],
        ["2024-07-01", 18000, 18000],
      ])}
    />
  ),
};

// 5. Large withdrawal -- the blue foundation drops.
export const LargeWithdrawal: Story = {
  render: () => (
    <Frame
      summary="Illustrative: a large withdrawal partway through -- the blue contribution foundation falls, the balance line steps down with it."
      points={build([
        ["2023-01-01", 50000, 45000],
        ["2023-06-01", 58000, 45000],
        ["2023-07-01", 33000, 20000],
        ["2024-01-01", 37000, 20000],
      ])}
    />
  ),
};

// 6. Contributions reduced to zero.
export const ContributionsWithdrawnToZero: Story = {
  render: () => (
    <Frame
      summary="Illustrative: everything contributed is progressively withdrawn -- the blue foundation falls to $0 and stops there."
      points={build([
        ["2022-01-01", 40000, 40000],
        ["2022-07-01", 30000, 25000],
        ["2023-01-01", 12000, 8000],
        ["2023-07-01", 5000, 0],
      ])}
    />
  ),
};

// 7. Authoritative Net Contributions below zero -- the key case.
export const NetContributionsBelowZero: Story = {
  render: () => (
    <Frame
      summary="Illustrative: cumulative withdrawals exceed contributions, so authoritative net contributions is negative -- but NO blue, green or red fill is drawn below $0. The balance line stays authoritative."
      points={build([
        ["2023-01-01", 40000, 30000],
        ["2023-07-01", 25000, 10000],
        ["2024-01-01", 8000, -8000],
        ["2024-07-01", 4000, -15000],
      ])}
    />
  ),
};

// 8. Fully divested.
export const FullyDivested: Story = {
  render: () => (
    <Frame
      summary="Illustrative: the portfolio is fully divested to a small cash balance, authoritative net contributions deeply negative -- history still shown, nothing below $0."
      points={build([
        ["2022-01-01", 50000, 40000],
        ["2023-01-01", 60000, 30000],
        ["2024-01-01", 200, -16000],
        ["2024-07-01", 130, -16480],
      ])}
    />
  ),
};

// 9. Sparse history.
export const SparseHistoricalData: Story = {
  render: () => (
    <Frame
      summary="Illustrative: only two priced observations with a long carried-forward stretch, then a gap -- no fabricated points."
      points={[
        ...build([
          ["2024-01-01", 20000, 18000],
          ["2024-03-31", 20000, 18000],
          ["2024-06-30", 23000, 18000],
        ]),
        {
          date: "2024-09-30", portfolio_value: null, contributions: "0", withdrawals: "0",
          net_contributions: "18000", investment_gain: null, period_investment_gain: null,
          cash_flow_events: [],
        },
      ]}
    />
  ),
};
