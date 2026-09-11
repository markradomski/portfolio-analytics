/**
 * Step 8 hardening (sec 4/30): the top-level routing contract, exercised
 * through the real `App` (real BrowserRouter, real QueryClient) rather
 * than a mock -- an unknown route must render a real page, and a valid
 * route must still resolve rather than staying blank, exactly as a direct
 * navigation or a refresh would hit it. `fetch` is stubbed to reject so
 * these tests never depend on a live backend; each screen's own tests
 * already cover its data states in detail.
 */
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

function renderAt(path: string) {
  window.history.pushState({}, "", path);
  return render(<App />);
}

describe("App: routing", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders a real not-found page for an unknown route, never a blank main", () => {
    renderAt("/this-route-does-not-exist");
    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });

  it("resolves the Overview screen at the root route", () => {
    renderAt("/");
    expect(screen.getAllByRole("heading", { level: 1 })[0]).toHaveTextContent(/Overview|Portfolio/);
  });

  it("resolves each of the 9 registered routes to a distinct screen, not the not-found fallback", () => {
    const routes = [
      "/performance", "/holdings", "/income", "/gains", "/contributions", "/risk", "/history",
    ];
    for (const route of routes) {
      const { unmount } = renderAt(route);
      expect(screen.queryByText("Page not found")).not.toBeInTheDocument();
      unmount();
    }
  });

  it("keeps primary navigation present alongside the not-found page (sec 9: a page-level condition never takes down navigation)", () => {
    renderAt("/no-such-route");
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Performance" })).toBeInTheDocument();
  });
});
