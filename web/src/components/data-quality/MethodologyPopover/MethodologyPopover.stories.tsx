import type { Meta, StoryObj } from "@storybook/react-vite";

import { MethodologyPopover } from "./MethodologyPopover";

const meta: Meta<typeof MethodologyPopover> = { title: "Data Quality/MethodologyPopover", component: MethodologyPopover };
export default meta;
type Story = StoryObj<typeof MethodologyPopover>;

export const Twrr: Story = {
  args: {
    summary: "23 quarterly return periods",
    detail: "TWRR: chained Modified Dietz between consecutive real valuations, 2020-09-30 → 2026-06-30. Not true TWRR, which would revalue at every cash-flow date -- this data source only supports revaluation at the dates Vanguard itself priced the portfolio.",
  },
};
