import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell/AppShell";
import { ErrorBoundary } from "../components/common/ErrorBoundary/ErrorBoundary";
import { ContributionsPage } from "../features/contributions/ContributionsPage";
import { GainsPage } from "../features/gains/GainsPage";
import { HistoryPage } from "../features/history/HistoryPage";
import { HoldingsPage } from "../features/holdings/HoldingsPage";
import { IncomePage } from "../features/income/IncomePage";
import { NotFoundPage } from "../features/not-found/NotFoundPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { PerformancePage } from "../features/performance/PerformancePage";
import { RiskPage } from "../features/risk/RiskPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // Step 8 (sec 6/7): this application reads statement/analytics data
      // that changes at most quarterly, never a live feed -- reconnecting
      // the browser tab should not silently refire every query against an
      // API that has nothing new to say. Each hook in usePortfolioApi.ts
      // still sets its own staleTime explicitly; this is only the
      // fallback for a query that somehow didn't.
      refetchOnReconnect: false,
      // Step 8 (sec 8/24 -- discovered live, not theoretical): React
      // Query's default networkMode ("online") pauses a failing query
      // rather than settling it into an error the moment the browser's
      // online-manager believes the network is down -- and a paused query
      // only resumes on the DOM `online` event firing again. That event is
      // not guaranteed to fire in every environment (verified here: a
      // backend outage reproducibly left every query stuck at
      // `fetchStatus: "paused"` forever -- `query.isPending` true,
      // `isError` never true -- with the screen frozen on "Loading…" and
      // no way for a user to recover short of restarting the browser).
      // This app has nothing useful to serve from a service-worker cache
      // while offline, so there is no benefit to pausing; "always" attempt
      // the request and let a genuine failure surface through
      // QueryBoundary's error state (which now offers Retry) instead of
      // silently freezing.
      networkMode: "always",
    },
  },
});

/**
 * A route-scoped error boundary (Step 8 sec 9): keyed on the current
 * pathname, so navigating away from a screen that crashed always renders
 * the next screen fresh rather than staying stuck on the boundary's
 * fallback (a class component's caught-error state does not clear itself
 * just because its children changed -- only a key change forces that).
 * Placed inside AppShell rather than around it, so a page-level rendering
 * bug never takes the primary navigation down with it (sec 1: "page-level
 * errors do not destroy the entire application unnecessarily").
 */
function RoutedContent() {
  const location = useLocation();
  return (
    <ErrorBoundary key={location.pathname}>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="/holdings" element={<HoldingsPage />} />
        <Route path="/holdings/:code" element={<HoldingsPage />} />
        <Route path="/income" element={<IncomePage />} />
        <Route path="/gains" element={<GainsPage />} />
        <Route path="/contributions" element={<ContributionsPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ErrorBoundary>
  );
}

/**
 * The Phase 5 foundation (sec 5.1): routing, the API/state boundary
 * (QueryClientProvider wraps everything, so every screen's data flows
 * through the React Query hooks in hooks/api/), and a top-level error
 * boundary distinct from per-query error states.
 */
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* Outer boundary: a last resort for a crash in AppShell/routing
       * itself, outside any one page. The per-route boundary below is
       * expected to catch almost everything a page can throw. */}
      <ErrorBoundary>
        <BrowserRouter>
          <AppShell>
            <RoutedContent />
          </AppShell>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
