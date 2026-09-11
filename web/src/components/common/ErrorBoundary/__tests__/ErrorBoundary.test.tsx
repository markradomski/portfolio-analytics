/**
 * Step 8 hardening (sec 9): a rendering exception must not take down the
 * whole application, must show a plain user-facing message rather than a
 * stack trace, and must be recoverable -- either via its own "Try again"
 * or (the pattern App.tsx actually uses) by changing the boundary's `key`
 * when the route changes, so navigating to a different screen after a
 * crash always renders that screen fresh rather than staying stuck on the
 * old fallback.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ErrorBoundary } from "../ErrorBoundary";

function Boom(): never {
  throw new Error("a component crashed");
}

describe("ErrorBoundary", () => {
  it("catches a rendering error and shows a plain message, not the raw stack", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong displaying this.")).toBeInTheDocument();
    expect(screen.getByText("a component crashed")).toBeInTheDocument();
    expect(screen.queryByText(/at Boom/)).not.toBeInTheDocument();
    spy.mockRestore();
  });

  it("recovers via its own Try again action once the underlying problem is gone", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    let shouldThrow = true;
    function Flaky() {
      if (shouldThrow) throw new Error("transient");
      return <div>recovered content</div>;
    }
    render(
      <ErrorBoundary>
        <Flaky />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong displaying this.")).toBeInTheDocument();
    shouldThrow = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByText("recovered content")).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it("resets when its key changes (the route-change convention App.tsx relies on), even without Try again", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { rerender } = render(
      <ErrorBoundary key="/a">
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong displaying this.")).toBeInTheDocument();

    rerender(
      <ErrorBoundary key="/b">
        <div>a different, working screen</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText("a different, working screen")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong displaying this.")).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
