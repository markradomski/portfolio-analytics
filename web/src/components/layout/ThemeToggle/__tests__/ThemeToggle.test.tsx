import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ThemeToggle } from "../ThemeToggle";
import { ThemeProvider } from "../../../../hooks/ThemeContext";

function renderToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

function currentTheme() {
  return document.documentElement.getAttribute("data-theme");
}

function currentVanyardMode() {
  return document.documentElement.getAttribute("data-vanyard-mode");
}

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.removeAttribute("data-vanyard-mode");
});
afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.removeAttribute("data-vanyard-mode");
});

describe("ThemeToggle", () => {
  it("renders a labelled three-mark group with light, dark and vanyard options", () => {
    renderToggle();
    expect(screen.getByRole("group", { name: /colour theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /light theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dark theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /vanyard theme/i })).toBeInTheDocument();
  });

  it("with no explicit preference, defaults to Vanyard Dark, with the Vanyard mark pressed", () => {
    renderToggle();
    expect(currentTheme()).toBe("vanyard");
    expect(currentVanyardMode()).toBe("dark");
    expect(screen.getByRole("button", { name: /vanyard theme/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /light theme/i })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute("aria-pressed", "false");
  });

  it("switches to dark and persists the choice", async () => {
    renderToggle();
    await userEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    expect(currentTheme()).toBe("dark");
    expect(window.localStorage.getItem("theme")).toBe("dark");
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("switches back to light and persists", async () => {
    renderToggle();
    await userEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    await userEvent.click(screen.getByRole("button", { name: /light theme/i }));
    expect(currentTheme()).toBe("light");
    expect(window.localStorage.getItem("theme")).toBe("light");
  });

  it("clicking the already-explicit choice returns to the default (Vanyard Dark)", async () => {
    renderToggle();
    const dark = screen.getByRole("button", { name: /dark theme/i });
    await userEvent.click(dark);
    expect(currentTheme()).toBe("dark");
    await userEvent.click(dark);
    expect(currentTheme()).toBe("vanyard");
    expect(currentVanyardMode()).toBe("dark");
    expect(window.localStorage.getItem("theme")).toBeNull();
    expect(screen.getByRole("button", { name: /vanyard theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("restores a persisted preference on mount", () => {
    window.localStorage.setItem("theme", "dark");
    renderToggle();
    expect(currentTheme()).toBe("dark");
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("each mark carries a descriptive title", () => {
    renderToggle();
    expect(screen.getByRole("button", { name: /dark theme/i })).toHaveAttribute(
      "title",
      expect.stringMatching(/dark/i),
    );
  });

  it("switches to vanyard (light) and persists the choice, distinct from the Vanyard Dark default", async () => {
    renderToggle();
    await userEvent.click(screen.getByRole("button", { name: /vanyard theme/i }));
    expect(currentTheme()).toBe("vanyard");
    expect(currentVanyardMode()).toBeNull();
    expect(window.localStorage.getItem("theme")).toBe("vanyard");
    expect(screen.getByRole("button", { name: /vanyard theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("an invalid stored theme value falls back to the Vanyard Dark default", () => {
    window.localStorage.setItem("theme", "sepia");
    renderToggle();
    expect(currentTheme()).toBe("vanyard");
    expect(currentVanyardMode()).toBe("dark");
    expect(screen.getByRole("button", { name: /vanyard theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("a cleared preference falls back to the Vanyard Dark default on the next mount", async () => {
    const first = renderToggle();
    await userEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    expect(currentTheme()).toBe("dark");
    window.localStorage.clear();
    first.unmount();

    // A fresh mount simulates the next page load reading the now-cleared
    // storage -- the running instance's own React state doesn't
    // spontaneously re-read localStorage, exactly like a real reload.
    renderToggle();
    expect(currentTheme()).toBe("vanyard");
    expect(currentVanyardMode()).toBe("dark");
    expect(screen.getByRole("button", { name: /vanyard theme/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("a failed preference lookup (localStorage throwing) falls back to the Vanyard Dark default", () => {
    const original = window.localStorage.getItem.bind(window.localStorage);
    window.localStorage.getItem = () => {
      throw new Error("storage unavailable");
    };
    try {
      renderToggle();
      expect(currentTheme()).toBe("vanyard");
      expect(currentVanyardMode()).toBe("dark");
    } finally {
      window.localStorage.getItem = original;
    }
  });

  it("vanyard has no system equivalent -- clicking it again keeps vanyard selected, never reverting to system", async () => {
    renderToggle();
    const vanyard = screen.getByRole("button", { name: /vanyard theme/i });
    await userEvent.click(vanyard);
    expect(currentTheme()).toBe("vanyard");
    await userEvent.click(vanyard);
    expect(currentTheme()).toBe("vanyard");
    expect(window.localStorage.getItem("theme")).toBe("vanyard");
  });

  it("switches from vanyard back to light normally", async () => {
    renderToggle();
    await userEvent.click(screen.getByRole("button", { name: /vanyard theme/i }));
    await userEvent.click(screen.getByRole("button", { name: /light theme/i }));
    expect(currentTheme()).toBe("light");
  });
});
