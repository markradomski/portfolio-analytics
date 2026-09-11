import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "../../../api/client";
import { Button } from "../../../design-system/Button/Button";
import { UnavailableMetric } from "../../data-quality/UnavailableMetric/UnavailableMetric";
import { ChartSkeleton } from "../Skeleton/Skeleton";
import styles from "./QueryBoundary.module.css";

export interface QueryBoundaryProps<T> {
  query: UseQueryResult<T>;
  loading?: ReactNode;
  /** Called only when data arrived and is non-empty by the caller's own
   * definition (isEmpty) -- distinct from an API error (sec 38: "No income
   * recorded" is not the same as "Income data unavailable"). */
  isEmpty?: (data: T) => boolean;
  emptyMessage?: string;
  children: (data: T) => ReactNode;
}

/**
 * The one place loading / error / empty / data states are composed for an
 * API-backed view (sec 37/38). A screen using this never writes its own
 * `if (isLoading) ...` branch -- keeping loading/error/empty presentation
 * consistent everywhere rather than reinvented per screen.
 *
 * Step 8 hardening (sec 9/29): a failed query now offers a local "Retry"
 * (React Query's own `refetch()`, not a full page reload -- the query
 * that actually failed is the only thing that runs again), and the
 * pending state carries a `role="status"` announcement so a screen-reader
 * user knows something is loading rather than hearing silence followed by
 * a sudden change in content.
 */
export function QueryBoundary<T>({ query, loading, isEmpty, emptyMessage, children }: QueryBoundaryProps<T>) {
  if (query.isPending) {
    return (
      <>
        <span className={styles.srOnly} role="status">Loading…</span>
        {loading ?? <ChartSkeleton />}
      </>
    );
  }

  if (query.isError) {
    const isApiError = query.error instanceof ApiError;
    return (
      <UnavailableMetric
        title="Couldn't load this"
        reason={
          isApiError
            ? (query.error as ApiError).detail
            : "The request failed. Check that the API server is running."
        }
        action={
          <Button size="small" onClick={() => query.refetch()} disabled={query.isFetching}>
            {query.isFetching ? "Retrying…" : "Retry"}
          </Button>
        }
      />
    );
  }

  if (isEmpty?.(query.data as T)) {
    return <UnavailableMetric title="No data" reason={emptyMessage ?? "Nothing recorded for this yet."} />;
  }

  return <>{children(query.data as T)}</>;
}
