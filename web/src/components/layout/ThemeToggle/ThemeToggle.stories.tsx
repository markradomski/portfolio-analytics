import type { Meta, StoryObj } from "@storybook/react-vite";

import { ThemeProvider } from "../../../hooks/ThemeContext";
import { ThemeToggle } from "./ThemeToggle";

/**
 * The colour-theme switch. In the app it is `position: fixed` in the
 * top-right corner (rendered once by `AppShell`); here it is shown in a
 * relatively-positioned frame so it sits in view.
 */
const meta: Meta<typeof ThemeToggle> = {
  title: "Layout/ThemeToggle",
  component: ThemeToggle,
  decorators: [
    (Story) => (
      <ThemeProvider>
        <div style={{ position: "relative", height: 80 }}>
          <Story />
        </div>
      </ThemeProvider>
    ),
  ],
};
export default meta;
type Story = StoryObj<typeof ThemeToggle>;

export const Default: Story = {};
