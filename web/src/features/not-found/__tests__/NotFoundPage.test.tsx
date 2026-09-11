import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { NotFoundPage } from "../NotFoundPage";

describe("NotFoundPage", () => {
  it("names the mistyped path and offers a way back to Overview", () => {
    render(
      <MemoryRouter initialEntries={["/definitely-not-a-real-route"]}>
        <Routes>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("Page not found")).toBeInTheDocument();
    expect(screen.getByText("/definitely-not-a-real-route")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Back to Overview/ })).toHaveAttribute("href", "/");
  });
});
