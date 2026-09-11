import { MemoryRouter } from "react-router-dom";
import type { Meta, StoryObj } from "@storybook/react-vite";

import { Badge } from "../Badge/Badge";
import { SectionHeader } from "./SectionHeader";

const meta: Meta<typeof SectionHeader> = {
  title: "Design System/SectionHeader",
  component: SectionHeader,
  decorators: [(Story) => <MemoryRouter><Story /></MemoryRouter>],
};
export default meta;
type Story = StoryObj<typeof SectionHeader>;

export const Default: Story = {
  args: { title: "Contributions" },
};

export const WithSubtitle: Story = {
  args: { title: "Allocation", subtitle: "By asset class" },
};

export const WithViewAllLink: Story = {
  args: { title: "Top holdings", viewAllHref: "/holdings" },
};

export const WithCustomViewAllLabel: Story = {
  args: { title: "Historical value", viewAllHref: "/performance", viewAllLabel: "View performance" },
};

export const WithAction: Story = {
  args: {
    title: "Income",
    viewAllHref: "/income",
    action: <Badge tone="quality-limited" withDot={false}>Limited</Badge>,
  },
};

export const LongTitleOnNarrowLayout: Story = {
  args: {
    title: "A considerably longer section title than usual",
    subtitle: "To confirm wrapping stays legible at mobile widths",
    viewAllHref: "/history",
    viewAllLabel: "View full history",
  },
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
