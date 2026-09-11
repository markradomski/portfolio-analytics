import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataQualityBadge } from "../DataQualityBadge/DataQualityBadge";
import type { DataQuality } from "../../../api/types";

describe("DataQualityBadge", () => {
  it.each<[DataQuality, string]>([
    ["actual", "Actual"], ["calculated", "Calculated"], ["estimated", "Estimated"],
    ["limited", "Limited"], ["unavailable", "Unavailable"],
  ])("renders the %s state with its default label", (quality, label) => {
    render(<DataQualityBadge quality={quality} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("accepts a custom label carrying more detail", () => {
    render(<DataQualityBadge quality="limited" label="Limited · 23 quarterly obs." />);
    expect(screen.getByText("Limited · 23 quarterly obs.")).toBeInTheDocument();
  });
});
