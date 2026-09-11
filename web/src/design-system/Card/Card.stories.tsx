import type { Meta, StoryObj } from "@storybook/react-vite";

import { Card } from "./Card";

const meta: Meta<typeof Card> = {
  title: "Design System/Card",
  component: Card,
};
export default meta;
type Story = StoryObj<typeof Card>;

export const Default: Story = {
  args: {
    title: "Portfolio value",
    subtitle: "As at 30 Jun 2026",
    children: <p style={{ margin: 0 }}>$126.88</p>,
  },
};

export const Raised: Story = {
  args: { ...Default.args, elevation: "raised" },
};
