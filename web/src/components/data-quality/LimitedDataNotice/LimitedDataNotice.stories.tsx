import type { Meta, StoryObj } from "@storybook/react-vite";

import { LimitedDataNotice } from "./LimitedDataNotice";

const meta: Meta<typeof LimitedDataNotice> = { title: "Data Quality/LimitedDataNotice", component: LimitedDataNotice };
export default meta;
type Story = StoryObj<typeof LimitedDataNotice>;

export const Volatility: Story = {
  args: {
    title: "Volatility: 18.4%",
    explanation: "Calculated from 23 quarterly observations. Daily observations are not currently available, so treat this as indicative rather than statistically precise.",
  },
};
