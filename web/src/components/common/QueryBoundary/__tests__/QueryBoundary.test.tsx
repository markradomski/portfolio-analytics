/**
 * Step 8 hardening (sec 9/29/30): QueryBoundary is the one place every
 * screen's loading/error/empty/data state is composed, so its own
 * behaviour is tested directly rather than only indirectly through each
 * screen. Covers the two things Step 8 added -- a screen-reader loading
 * announcement and a local Retry action on a failed query -- plus the
 * pre-existing empty/data branches so a regression here would fail loudly.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "../../../../api/client";
import { QueryBoundary } from "../QueryBoundary";

function pending(): UseQueryResult<unknown> {
  return { isPending: true, isError: false, isFetching: true, data: undefined } as UseQueryResult<unknown>;
}
function ok<T>(data: T): UseQueryResult<T> {
  return { isPending: false, isError: false, isFetching: false, data } as UseQueryResult<T>;
}
function failed(error: Error, refetch = vi.fn()): UseQueryResult<unknown> {
  return {
    isPending: false, isError: true, isFetching: false, data: undefined, error, refetch,
  } as unknown as UseQueryResult<unknown>;
}

describe("QueryBoundary: loading", () => {
  it("announces loading to a screen reader while pending, distinct from empty/zero/unavailable", () => {
    render(<QueryBoundary query={pending()}>{() => <div>data</div>}</QueryBoundary>);
    expect(screen.getByRole("status")).toHaveTextContent("Loading…");
    expect(screen.queryByText("data")).not.toBeInTheDocument();
    expect(screen.queryByText(/Couldn't load this/)).not.toBeInTheDocument();
    expect(screen.queryByText(/No data/)).not.toBeInTheDocument();
  });

  it("renders a caller-supplied loading placeholder instead of the default skeleton", () => {
    render(
      <QueryBoundary query={pending()} loading={<div>custom skeleton</div>}>
        {() => <div>data</div>}
      </QueryBoundary>,
    );
    expect(screen.getByText("custom skeleton")).toBeInTheDocument();
  });
});

describe("QueryBoundary: error", () => {
  it("shows the API's own detail message for an ApiError, with a Retry action", async () => {
    const refetch = vi.fn();
    const error = new ApiError(503, "Portfolio database not built yet.", "/api/portfolio/income");
    render(<QueryBoundary query={failed(error, refetch)}>{() => <div>data</div>}</QueryBoundary>);
    expect(screen.getByText("Portfolio database not built yet.")).toBeInTheDocument();
    expect(screen.queryByText("data")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("shows a plain-language message, not a raw error/stack trace, for a non-API error (e.g. a network failure)", () => {
    const error = new TypeError("Failed to fetch");
    render(<QueryBoundary query={failed(error)}>{() => <div>data</div>}</QueryBoundary>);
    expect(screen.getByText("The request failed. Check that the API server is running.")).toBeInTheDocument();
    expect(screen.queryByText("Failed to fetch")).not.toBeInTheDocument();
  });

  it("labels the Retry button as retrying while a retry is in flight", () => {
    const query = failed(new TypeError("x"));
    (query as { isFetching: boolean }).isFetching = true;
    render(<QueryBoundary query={query}>{() => <div>data</div>}</QueryBoundary>);
    expect(screen.getByRole("button", { name: "Retrying…" })).toBeDisabled();
  });
});

describe("QueryBoundary: empty vs data vs error", () => {
  it("shows the caller's empty message only when data arrived and is empty by its own definition", () => {
    render(
      <QueryBoundary query={ok([])} isEmpty={(rows: unknown[]) => rows.length === 0} emptyMessage="Nothing here yet.">
        {() => <div>data</div>}
      </QueryBoundary>,
    );
    expect(screen.getByText("Nothing here yet.")).toBeInTheDocument();
    expect(screen.queryByText(/Couldn't load this/)).not.toBeInTheDocument();
  });

  it("renders the children with real data when the query succeeds and isEmpty says no", () => {
    render(
      <QueryBoundary query={ok([1, 2, 3])} isEmpty={(rows: number[]) => rows.length === 0}>
        {(rows) => <div>{rows.length} rows</div>}
      </QueryBoundary>,
    );
    expect(screen.getByText("3 rows")).toBeInTheDocument();
  });
});
