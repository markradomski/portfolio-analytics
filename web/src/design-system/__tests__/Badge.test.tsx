import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "../Badge/Badge";

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge tone="positive">+18.4%</Badge>);
    expect(screen.getByText("+18.4%")).toBeInTheDocument();
  });

  it("renders a dot by default as a non-colour cue (sec 32)", () => {
    const { container } = render(<Badge tone="negative">-4.2%</Badge>);
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });

  it("can omit the dot", () => {
    const { container } = render(<Badge tone="negative" withDot={false}>-4.2%</Badge>);
    expect(container.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
  });
});
