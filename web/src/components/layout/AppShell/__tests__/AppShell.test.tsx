/**
 * The responsive nav (hamburger + overlay at <=860px, unchanged sidebar
 * above it) exercised through the real `App` -- real BrowserRouter, real
 * ThemeProvider -- the same convention src/app/__tests__/App.test.tsx
 * already uses, rather than mounting AppShell standalone with hand-rolled
 * providers. `fetch` is stubbed to reject so no test depends on a live
 * backend; each screen's own data states are already covered elsewhere.
 *
 * jsdom (vitest.config.ts runs it with `css: true`) applies the real CSS
 * Modules, but its computed-style engine does not evaluate `@media`
 * conditions against `window.innerWidth` -- .mobileHeader/.mobileNav's
 * unconditional `display: none` (AppShell.module.css) always "wins" here,
 * even though a real browser at a narrow width would show them. That's a
 * jsdom limitation, not a real hidden state, so role queries here pass
 * `{ hidden: true }` to see past it, and clicks use `fireEvent` (which,
 * unlike `userEvent`, doesn't refuse to act on an element it believes is
 * hidden) rather than `userEvent`. None of this tests the CSS/media query
 * itself -- that's verified visually, per this task's own instruction not
 * to write brittle pixel/CSS-position tests -- only the open/close state,
 * ARIA and focus behaviour once the overlay exists.
 */
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../../../../app/App";

const NAV_DESTINATIONS = [
  "Overview", "Performance", "Holdings", "Income", "Gains", "Contributions", "Risk", "History",
];

function renderAt(path: string) {
  window.history.pushState({}, "", path);
  return render(<App />);
}

function hamburger() {
  return screen.getByRole("button", { name: /(open|close) navigation/i, hidden: true });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.removeAttribute("data-vanyard-mode");
});
afterEach(() => {
  vi.unstubAllGlobals();
  document.body.style.overflow = "";
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.removeAttribute("data-vanyard-mode");
});

describe("AppShell: primary navigation", () => {
  it("keeps every destination present in the desktop sidebar", () => {
    renderAt("/");
    for (const label of NAV_DESTINATIONS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("keeps every destination present in the mobile overlay too", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    const overlay = document.getElementById("primary-nav-mobile")!;
    for (const label of NAV_DESTINATIONS) {
      expect(within(overlay).getByRole("link", { name: label, hidden: true })).toBeInTheDocument();
    }
  });

  it("marks the current route's link active (aria-current), not some other destination", () => {
    renderAt("/performance");
    const performanceLinks = screen.getAllByRole("link", { name: "Performance", hidden: true });
    for (const link of performanceLinks) expect(link).toHaveAttribute("aria-current", "page");
    const overviewLinks = screen.getAllByRole("link", { name: "Overview", hidden: true });
    for (const link of overviewLinks) expect(link).not.toHaveAttribute("aria-current");
  });

  it("defaults to Vanyard (dark) with no regression -- the brand mark is present, not the plain wordmark", () => {
    renderAt("/");
    expect(screen.getAllByAltText("Vanyard").length).toBeGreaterThan(0);
    expect(document.documentElement.getAttribute("data-theme")).toBe("vanyard");
    expect(document.documentElement.getAttribute("data-vanyard-mode")).toBe("dark");
  });
});

describe("AppShell: mobile menu", () => {
  it("starts closed", () => {
    renderAt("/");
    expect(hamburger()).toHaveAttribute("aria-expanded", "false");
    expect(hamburger()).toHaveAccessibleName(/open navigation/i);
    expect(document.getElementById("primary-nav-mobile")).not.toBeInTheDocument();
  });

  it("opens on click, with the accessible label and aria-expanded flipping", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    expect(hamburger()).toHaveAttribute("aria-expanded", "true");
    expect(hamburger()).toHaveAccessibleName(/close navigation/i);
    expect(document.getElementById("primary-nav-mobile")).toBeInTheDocument();
  });

  it("locks body scroll while open and restores it on close", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.click(hamburger());
    expect(document.body.style.overflow).toBe("");
  });

  it("closes on a second click of the same (now close) button", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    fireEvent.click(hamburger());
    expect(hamburger()).toHaveAttribute("aria-expanded", "false");
    expect(document.getElementById("primary-nav-mobile")).not.toBeInTheDocument();
  });

  it("closes on Escape", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    expect(hamburger()).toHaveAttribute("aria-expanded", "true");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(hamburger()).toHaveAttribute("aria-expanded", "false");
  });

  it("closes on a backdrop click", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    const backdrop = document.querySelector('[aria-hidden="true"][class*="backdrop"]');
    expect(backdrop).toBeTruthy();
    fireEvent.click(backdrop as Element);
    expect(hamburger()).toHaveAttribute("aria-expanded", "false");
  });

  it("closes when a destination inside the overlay is selected", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    const overlay = document.getElementById("primary-nav-mobile")!;
    fireEvent.click(within(overlay).getByRole("link", { name: "Performance", hidden: true }));
    expect(hamburger()).toHaveAttribute("aria-expanded", "false");
    expect(document.getElementById("primary-nav-mobile")).not.toBeInTheDocument();
  });

  it("does not remain open across a route change triggered another way (an ordinary in-page link, not the overlay)", () => {
    renderAt("/");
    fireEvent.click(hamburger());
    expect(hamburger()).toHaveAttribute("aria-expanded", "true");
    // "View performance" is a real react-router Link elsewhere on the
    // Overview page, nothing to do with the nav overlay -- proves the
    // close effect is generically tied to the route (useLocation), not
    // wired only into the overlay links' own onClick.
    fireEvent.click(screen.getByRole("link", { name: "View performance" }));
    expect(hamburger()).toHaveAttribute("aria-expanded", "false");
  });
});

describe("AppShell: theme controls still work alongside the nav changes", () => {
  it("the three-mark theme switch is present and switches theme", async () => {
    renderAt("/");
    await userEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
