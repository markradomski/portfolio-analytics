import type { Meta, StoryObj } from "@storybook/react-vite";

import { Tooltip } from "./Tooltip";

const meta: Meta<typeof Tooltip> = {
  title: "Design System/Tooltip",
  component: Tooltip,
};
export default meta;
type Story = StoryObj<typeof Tooltip>;

export const MethodologyInfo: Story = {
  args: {
    content: "TWRR: 23 quarterly return periods, 2020-09-30 → 2026-06-30.",
    children: <button aria-label="How is this calculated?" style={{ border: "none", background: "none", cursor: "pointer" }}>ⓘ</button>,
  },
};
