import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { UnavailableMetric } from "../UnavailableMetric/UnavailableMetric";

describe("UnavailableMetric", () => {
  it("never renders a bare N/A -- always the API's own reason (sec 10)", () => {
    render(<UnavailableMetric title="Sharpe ratio" reason="A risk-free rate has not been configured." />);
    expect(screen.queryByText("N/A")).not.toBeInTheDocument();
    expect(screen.getByText(/risk-free rate has not been configured/)).toBeInTheDocument();
  });

  it("labels itself Unavailable, not silently blank", () => {
    render(<UnavailableMetric title="Beta" reason="No benchmark registered" />);
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });
});
