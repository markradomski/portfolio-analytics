import type { Meta, StoryObj } from "@storybook/react-vite";

import { ChartContainer } from "../ChartContainer/ChartContainer";
import { ChartLegend } from "../ChartLegend/ChartLegend";
import { BalanceDecompositionChart } from "./BalanceDecompositionChart";
import type { CashFlowEvent, PortfolioGrowthPoint } from "../../../api/types";

/**
 * All fixture data below is illustrative / test data only -- it is NOT a
 * real portfolio and the figures are hand-chosen to exercise a specific
 * geometry (event markers, per-period gain/loss, valuation gaps), not to
 * represent any actual account.
 */
interface Row {
  date: string;
  value: number | null;
  netContrib: number;
  cumGain: number | null;
  periodGain?: number | null;
  event?: "CONTRIBUTION" | "WITHDRAWAL";
  eventAmount?: string;
}

function build(rows: Row[]): PortfolioGrowthPoint[] {
  return rows.map((r) => {
    const events: CashFlowEvent[] = r.event
      ? [{
          transaction_id: `${r.date}-1`, date: r.date, type: r.event,
          amount: r.eventAmount ?? "0", account: "primary", source: "VANGUARD", description: null,
        }]
      : [];
    return {
      date: r.date,
      portfolio_value: r.value === null ? null : String(r.value),
      contributions: "0",
      withdrawals: "0",
      net_contributions: String(r.netContrib),
      investment_gain: r.cumGain === null ? null : String(r.cumGain),
      period_investment_gain: r.periodGain === undefined ? null : (r.periodGain === null ? null : String(r.periodGain)),
      cash_flow_events: events,
    };
  });
}

const LEGEND = (
  <ChartLegend
    items={[
      { label: "Total Balance", color: "var(--color-accent)", shape: "line" },
      { label: "Contributions & Withdrawals", color: "var(--color-accent-bg)", shape: "area" },
      { label: "Investment Gain", color: "var(--color-positive)", shape: "area", opacity: 0.9 },
      { label: "Investment Loss", color: "var(--color-negative)", shape: "area", opacity: 0.9 },
    ]}
  />
);

const meta: Meta<typeof BalanceDecompositionChart> = {
  title: "Charts/BalanceDecompositionChart",
  component: BalanceDecompositionChart,
};
export default meta;
type Story = StoryObj<typeof BalanceDecompositionChart>;

function Frame({ points, summary }: { points: PortfolioGrowthPoint[]; summary: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 820 }}>
      {LEGEND}
      <ChartContainer height={340} accessibleSummary={summary}>
        {({ width, height }) => <BalanceDecompositionChart points={points} width={width} height={height} />}
      </ChartContainer>
    </div>
  );
}

export const GrowthWithContributions: Story = {
  render: () => (
    <Frame
      summary="Illustrative: steady contributions and a portfolio that stays ahead of them -- contribution markers on the line, a green gain band."
      points={build([
        { date: "2023-01-01", value: 10000, netContrib: 10000, cumGain: 0 },
        { date: "2023-04-01", value: 16000, netContrib: 14000, cumGain: 2000, periodGain: 2000, event: "CONTRIBUTION", eventAmount: "4000" },
        { date: "2023-07-01", value: 19000, netContrib: 16000, cumGain: 3000, periodGain: 1000 },
        { date: "2023-10-01", value: 24000, netContrib: 20000, cumGain: 4000, periodGain: 1000, event: "CONTRIBUTION", eventAmount: "4000" },
        { date: "2024-01-01", value: 28000, netContrib: 22000, cumGain: 6000, periodGain: 2000 },
      ])}
    />
  ),
};

export const DrawdownBelowContributions: Story = {
  render: () => (
    <Frame
      summary="Illustrative: a market fall pulls the balance below net contributions -- a red investment-loss band under the contribution line."
      points={build([
        { date: "2023-01-01", value: 20000, netContrib: 18000, cumGain: 2000 },
        { date: "2023-04-01", value: 19000, netContrib: 19000, cumGain: 0, periodGain: -2000 },
        { date: "2023-07-01", value: 16500, netContrib: 20000, cumGain: -3500, periodGain: -3500 },
        { date: "2023-10-01", value: 18000, netContrib: 21000, cumGain: -3000, periodGain: 500 },
      ])}
    />
  ),
};

export const WithdrawalMarkers: Story = {
  render: () => (
    <Frame
      summary="Illustrative: partial withdrawals during the period -- distinct withdrawal markers, contributions area still above zero."
      points={build([
        { date: "2023-01-01", value: 40000, netContrib: 30000, cumGain: 10000 },
        { date: "2023-06-01", value: 34000, netContrib: 24000, cumGain: 10000, periodGain: 0, event: "WITHDRAWAL", eventAmount: "-6000" },
        { date: "2023-12-01", value: 26000, netContrib: 16000, cumGain: 10000, periodGain: 0, event: "WITHDRAWAL", eventAmount: "-8000" },
        { date: "2024-06-01", value: 28000, netContrib: 16000, cumGain: 12000, periodGain: 2000 },
      ])}
    />
  ),
};

export const NegativeNetContributions: Story = {
  render: () => (
    <Frame
      summary="Illustrative: cumulative withdrawals exceed cumulative contributions -- the contributions area drops below zero while a balance remains."
      points={build([
        { date: "2022-01-01", value: 50000, netContrib: 40000, cumGain: 10000 },
        { date: "2022-07-01", value: 30000, netContrib: 10000, cumGain: 20000, periodGain: 10000, event: "WITHDRAWAL", eventAmount: "-25000" },
        { date: "2023-01-01", value: 12000, netContrib: -8000, cumGain: 20000, periodGain: 0, event: "WITHDRAWAL", eventAmount: "-20000" },
        { date: "2023-07-01", value: 9000, netContrib: -15000, cumGain: 24000, periodGain: 4000 },
      ])}
    />
  ),
};

export const SparseHistoricalData: Story = {
  render: () => (
    <Frame
      summary="Illustrative: two priced observations with a long carried-forward stretch, then a valuation gap -- no fabricated points."
      points={build([
        { date: "2024-01-01", value: 20000, netContrib: 18000, cumGain: 2000 },
        { date: "2024-03-31", value: 20000, netContrib: 18000, cumGain: 2000, periodGain: 0 },
        { date: "2024-06-30", value: 23000, netContrib: 18000, cumGain: 5000, periodGain: 3000 },
        { date: "2024-09-30", value: null, netContrib: 18000, cumGain: null },
      ])}
    />
  ),
};
