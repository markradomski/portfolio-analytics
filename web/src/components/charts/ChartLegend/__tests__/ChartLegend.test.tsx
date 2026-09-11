import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChartLegend } from "../ChartLegend";

describe("ChartLegend", () => {
  it("renders every item's label, always visible (not inside a hover-only element)", () => {
    render(
      <ChartLegend
        items={[
          { label: "Total Balance", color: "var(--color-accent)", shape: "line" },
          { label: "Investment Returns", color: "var(--color-accent)", shape: "area", opacity: 0.18 },
          { label: "Contributions & Withdrawals", color: "var(--color-accent-bg)", shape: "area" },
        ]}
      />,
    );
    expect(screen.getByText("Total Balance")).toBeInTheDocument();
    expect(screen.getByText("Investment Returns")).toBeInTheDocument();
    expect(screen.getByText("Contributions & Withdrawals")).toBeInTheDocument();
  });

  it("renders a swatch coloured to match each item, not a generic default colour", () => {
    const { container } = render(
      <ChartLegend items={[{ label: "Total Balance", color: "var(--color-accent)", shape: "line" }]} />,
    );
    const swatch = container.querySelector("li span")!;
    expect(swatch.getAttribute("style")).toContain("var(--color-accent)");
  });
});
