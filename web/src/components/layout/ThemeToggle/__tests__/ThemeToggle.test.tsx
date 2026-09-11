import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ThemeToggle } from "../ThemeToggle";

function currentTheme() {
  return document.documentElement.getAttribute("data-theme");
}

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});
afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
});

describe("ThemeToggle", () => {
  it("renders a labelled two-mark group with light and dark options", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("group", { name: /colour theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /light theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dark theme/i })).toBeInTheDocument();
  });

  it("defaults to following the system (no data-theme attribute), with the system mark pressed", () => {
    render(<ThemeToggle />);
    expect(currentTheme()).toBeNull();
    // matchMedia stub -> light
    expect(screen.getByRole("button", { name: /light theme/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute("aria-pressed", "false");
  });

  it("switches to dark and persists the choice", async () => {
    render(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    expect(currentTheme()).toBe("dark");
    expect(window.localStorage.getItem("theme")).toBe("dark");
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("switches back to light and persists", async () => {
    render(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    await userEvent.click(screen.getByRole("button", { name: /light theme/i }));
    expect(currentTheme()).toBe("light");
    expect(window.localStorage.getItem("theme")).toBe("light");
  });

  it("clicking the already-explicit choice returns to following the system", async () => {
    render(<ThemeToggle />);
    const dark = screen.getByRole("button", { name: /dark theme/i });
    await userEvent.click(dark);
    expect(currentTheme()).toBe("dark");
    await userEvent.click(dark);
    expect(currentTheme()).toBeNull();
    expect(window.localStorage.getItem("theme")).toBeNull();
  });

  it("restores a persisted preference on mount", () => {
    window.localStorage.setItem("theme", "dark");
    render(<ThemeToggle />);
    expect(currentTheme()).toBe("dark");
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("each mark carries a descriptive title", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute(
      "title",
      expect.stringMatching(/dark/i),
    );
  });
});
