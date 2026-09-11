# Production UX & Application Hardening (Step 8)

Step 8 is an engineering-hardening pass over the application built in Steps
1-7, not a redesign. Nothing in this document changes the financial model,
the design system, the Figma library, the chart visual language, or any
screen's visual design. Every fix below is either a genuine correctness/
resilience defect (documented with how it was found) or a safe, additive
accessibility improvement within the existing component contracts.

---

## 1. Hardening inventory

Audited before any change was made, against the real source (not assumed
from prior reports):

| Area | Current state | Risk | Action | Status |
|---|---|---|---|---|
| Routing | 9 registered routes, `BrowserRouter`, no catch-all | An unknown/mistyped URL rendered a silent blank `<main>` (indistinguishable from a stuck load) | Added `<Route path="*">` → `NotFoundPage` | **Fixed** |
| Error boundary | One top-level boundary wrapping `AppShell` + `Routes` | A crash on any one screen took the primary navigation down with it | Moved to a route-scoped boundary (`key={pathname}`) inside `AppShell`, kept an outer boundary as a last resort | **Fixed** |
| React Query network resilience | Default `networkMode: "online"`, `retry: 1` | **Reproduced live**: once the browser's online-manager reports offline, a failing query's retry *pauses* rather than settling to `isError` — and only resumes on the next `online` DOM event, which is not guaranteed to fire. The screen is then stuck on "Loading…" forever, no error, no way to recover | Set `networkMode: "always"` — verified by test to settle to `isError` even with the online-manager reporting offline | **Fixed** |
| Error recovery | `QueryBoundary`'s error state had no retry — a user had to reload the whole page | Poor recoverability for a routine, expected failure (API restarting, brief network blip) | Added a local **Retry** button (`query.refetch()`), labelled "Retrying…" and disabled mid-flight | **Fixed** |
| Loading states | `QueryBoundary`'s pending branch rendered a skeleton with no accessible signal | A screen-reader user got silence, then a sudden change in content, with no "this is loading" announcement | Added a visually-hidden `role="status"` "Loading…" text alongside the existing skeleton | **Fixed** |
| Empty/zero/unavailable/limited | Kept distinct per-screen since Phase 5.5 (re-verified, not re-audited from scratch) | None found | No change | **Confirmed correct** |
| Accessibility — heading hierarchy | Every screen has exactly one static `<h1>` **except** Overview, whose `<h1>` lived inside the success branch of a `QueryBoundary` — no heading at all while loading/erroring | Screen-reader users get no page landmark until data arrives | Hoisted the `<h1>` to render unconditionally, kept the data-dependent content inside the same `QueryBoundary` | **Fixed** |
| Chart keyboard accessibility | `TimeSeriesChart`/`AllocationHistoryChart`'s hover-driven tooltip was pointer-only (`role="img" aria-hidden="true"` on the whole chart) — a documented Step 6 gap | No way to read a single data point's value without a mouse | Extended the shared `useNearestPoint` hook with keyboard (arrow/Home/End) navigation; the interactive overlay is now `tabIndex={0}` with a visible focus ring and an `aria-live` text announcement mirroring the visual tooltip | **Fixed** (2 of 3 chart components; see Deferred) |
| Table row keyboard accessibility | `Table`'s `onRowClick` prop (currently unused by any screen — every screen navigates via a real `<Link>` in a cell instead) attached a bare `onClick` to a `<tr>`, reachable only by mouse | A future caller of `onRowClick` would ship an inaccessible row | Added `tabIndex`/`onKeyDown` (Enter/Space) and a focus-visible outline, only when `onRowClick` is passed | **Fixed** |
| Privacy | No `localStorage`/`sessionStorage` use anywhere; no PII fields on any API type; `ActivityRow.description` already redacts withdrawal recipients server-side | None found | No change | **Confirmed correct** |
| Security | No `dangerouslySetInnerHTML`, no `eval`, no external links, no `window.open`, single network boundary (`client.ts`) | None found in frontend code; `npm audit` flags 2 high-severity advisories, both in `js-yaml` via a **dev-only** transitive dependency of `@redocly/openapi-core` (pulled in by `openapi-typescript`, used only to regenerate `schema.generated.ts` at dev time — never shipped, never runs on user input) | Documented; not forced (`npm audit fix` needs `--force` and would risk breaking Storybook/Vitest peer resolution for a build-time-only tool) | **Documented, deferred (P3)** |
| Console/logging hygiene | One `console.error` in `ErrorBoundary` (message + component stack, standard React practice); no stray `console.log`/debug output | None found | No change | **Confirmed correct** |
| Configuration | `VITE_API_BASE_URL` env var with a `localhost:8000` dev fallback; backend CORS is a dev-only `localhost`/`127.0.0.1` regex | Both need real values for a production deployment (see §9) | Documented, not changed (backend is frozen this step) | **Documented** |
| Bundle/performance | Single ~407KB (126KB gzip) JS bundle, no route-level code-splitting; 5 runtime dependencies, no duplicates | Bundle is already small for a 9-route SPA; splitting it would add complexity for no measured benefit | No change | **Confirmed acceptable, no premature optimisation** |
| Rendering | Only 2 real `useEffect` uses in the whole app (D3 axis imperative render, `ResizeObserver`); every fetch goes through React Query, no effect-driven request loops | None found | No change | **Confirmed correct** |

---

## 2. Architecture

Production UX sits entirely inside the existing layers — nothing new was
introduced between them:

```
API (FastAPI, unchanged)
  ↓
src/api/client.ts (the one fetch() boundary, unchanged)
  ↓
src/hooks/api/usePortfolioApi.ts (React Query wrappers, unchanged this step)
  ↓
src/components/common/QueryBoundary  ← hardened: retry action, loading announcement
src/components/common/ErrorBoundary  ← hardened: route-scoped, resets on navigation
src/app/App.tsx                      ← hardened: catch-all route, networkMode
src/features/not-found/NotFoundPage  ← new (routing completeness, not a "feature")
src/hooks/useNearestPoint.ts         ← hardened: keyboard navigation, additive
src/design-system/Table              ← hardened: onRowClick keyboard support, additive
```

No new network boundary, no new state-management library, no new routing
library.

## 3. Routing

All 9 routes (`/`, `/performance`, `/holdings`, `/holdings/:code`,
`/income`, `/gains`, `/contributions`, `/risk`, `/history`) resolve
correctly; verified via `App.test.tsx` rendering the real `App` (real
`BrowserRouter`, real `QueryClient`) at each path, plus live browser
navigation, refresh, and direct-URL entry during this step. An unknown
path (`/nonexistent-route` and others) now renders `NotFoundPage`, live-
verified, with primary navigation still present and functional (confirming
the route-scoped error/not-found handling does not take down `AppShell`).
Active nav-link state (`NavLink`'s `isActive`) is unchanged from Steps
5.1-5.7 and was not touched.

## 4. URL state

Re-reviewed, not changed: `useSelectedPeriod` already puts the selected
period in the URL (`?period=`) for Overview/Performance, which is the one
piece of UI state in the app that materially benefits from being
shareable/refreshable (sec 5 of the Step 8 brief). No other screen has a
tab, filter, or sort worth promoting to the URL — Table's client-side sort
is presentation-only re-ordering of already-fetched rows, not a query
parameter a link should carry, and every other tab (Holdings'
allocation-by view, Risk's benchmark period) is a fixed default with no
existing deep-linking requirement. Nothing new was added here; this was a
confirm-not-invent pass.

## 5. Data fetching / React Query strategy

Every screen's composite data hook (`useOverviewData`, `usePerformanceData`,
`useHoldingsData`, and each Step-7 screen's inline `useX` calls) issues its
queries as independent, parallel `useQuery` calls in the same render —
verified there is no sequential/waterfall fetching anywhere (each hook is
called unconditionally at the top of its composite hook; React Query
dedupes and parallelises automatically). `overview`/`capabilities` are
intentionally shared cache keys across Overview/Performance/Holdings, so
navigating between them costs zero extra requests when the cache is warm
(a Step 5.5-5.7 design decision, re-verified rather than re-invented).
Live network inspection during this step (Income, Gains, Contributions,
Risk, History, Overview, Holdings, Performance) showed no duplicate or
unnecessary requests, and no request fired for data a capability had
already marked unavailable.

### Caching policy (documented, not changed)

| Query category | staleTime | Reasoning |
|---|---|---|
| Overview/coverage/capabilities/history/holdings/income/gains/contributions/risk/activity (all portfolio data) | 5 minutes (`STALE_TIME` in `usePortfolioApi.ts`) | This application reads statement-derived analytics, "changes at most quarterly" (existing code comment) — 5 minutes is already a conservative, correct choice; every endpoint uses the same value because every endpoint has the same real-world update cadence. There is no "hot" vs "cold" data split to invent here (sec 7 explicitly warns against fabricating a real-time tier the API doesn't support). |
| `gcTime` | React Query v5 default (5 minutes unused-cache retention) | Never overridden; no query in this app is large or numerous enough to warrant tuning it. |
| `retry` | 1 (global default) | A single retry absorbs a transient blip without hammering a backend that's genuinely down; `QueryBoundary`'s new Retry button covers the rest. |
| `retryDelay` | React Query default (exponential, capped at 30s) | Unchanged; reasonable for a local single-user tool. |
| `refetchOnWindowFocus` | `false` (unchanged) | This data does not change while the tab is in the background — refetching on every alt-tab back would be pure waste for a quarterly-cadence dataset. |
| `refetchOnReconnect` | `false` (Step 8, newly explicit) | Same reasoning as above, made explicit as the global default rather than left to React Query's own default (`true`), which would refire every warm query the instant the network reconnects. |
| `networkMode` | `"always"` (Step 8, changed — see §8) | See the network-resilience finding below; this is the one behavioural change to the caching/fetching strategy this step made. |

No invalidation logic exists or was added (the app has no mutations —
every request is a `GET`), so there is nothing to document there beyond
"there is none, correctly."

## 6. Error handling

- **`ErrorBoundary`** (rendering exceptions only, never an API error state
  — those are QueryBoundary's job): now instantiated per-route
  (`key={location.pathname}` inside `AppShell`), so navigating away from a
  screen that crashed always renders the next screen fresh. An outer,
  app-level `ErrorBoundary` remains as a last-resort catch for a failure in
  `AppShell`/routing itself. Shows only `error.message` (never a stack
  trace) plus a "Try again" button that resets local boundary state —
  verified this both catches and recovers via a new test suite
  (`ErrorBoundary.test.tsx`).
- **`QueryBoundary`** (the API/data state machine): a failed query now
  shows the backend's own `ApiError.detail` (unchanged) plus a **Retry**
  button wired to `query.refetch()` — a local retry of only the failed
  request, never a full page reload. A non-`ApiError` (e.g. a genuine
  network failure) still shows the existing plain-language fallback
  message, never the raw `TypeError`.
- **The `networkMode: "always"` fix** (§1, §8) means a real network outage
  now reliably reaches this Retry button instead of freezing on "Loading…"
  forever.

## 7. State model

Re-verified across all 9 screens (the 3 pre-existing plus the 5 built in
Step 7, plus Security Detail) that these remain visually and semantically
distinct, per the existing `QueryBoundary`/`MetricValue`/`UnavailableMetric`
contract:

```
LOADING      -- skeleton + role="status" "Loading…" (Step 8: the
                announcement is new; the skeleton itself is unchanged)
ERROR        -- UnavailableMetric with the API's own reason + Retry (Step 8: Retry is new)
EMPTY        -- UnavailableMetric with a screen-authored emptyMessage
ZERO         -- the real figure (e.g. $0.00 realised loss), never conflated with UNAVAILABLE
UNAVAILABLE  -- UnavailableMetric / MetricValue's unavailableReason, never a fabricated 0
LIMITED      -- DataQualityBadge "Limited" + the backend's own reason text
```

Live-verified again this step against the real, fully-divested-portfolio
dataset: Gains' unrealised-gains table (0 current holdings → EMPTY, not an
error), Risk's Sharpe/Sortino/benchmark (genuinely UNAVAILABLE with the
backend's real reason, not 0%), Overview/Performance/Holdings unchanged.

## 8. API failure resilience (the central finding this step)

Tested by actually stopping the backend process mid-session (not simulated
in the abstract) and observing the running app:

1. **Backend unreachable, browser reports itself online**: retries once,
   then settles to the error state with Retry — this always worked.
2. **Backend unreachable, browser's online-manager reports offline**
   (reproduced live, then isolated and proven with a unit test using
   React Query's own `onlineManager.setOnline(false)`): with the library
   default (`networkMode: "online"`), the query's retry **pauses**
   indefinitely — `isPending` stays `true`, `isError` never becomes `true`,
   and the screen is stuck on "Loading…" with no error, no Retry button,
   and no way to recover short of reloading the page. This is a genuine
   defect class (documented failure mode of React Query's default network
   mode in any environment where the online/offline browser events are
   unreliable), not a hypothetical. Fixed by `networkMode: "always"` —
   confirmed by test that the same offline condition now settles to
   `isError` and lets Retry work.
3. **HTTP 4xx/5xx** (e.g. the existing 503 "Portfolio database not built
   yet"): already surfaced correctly via `ApiError.detail` before this
   step; unaffected by the `networkMode` change (that only affects the
   *retry pause* mechanism, not what a failure displays).
4. **Slow response**: the existing skeleton/loading state already covers
   this; nothing changed here.
5. **Partial capability** (Sharpe/Sortino/benchmark unavailable for this
   real portfolio): already correct (§7); re-verified, not changed.
6. **Malformed/missing optional fields**: every API type already models
   optional fields as `| null`, and every consumer already branches on
   that (`unavailableReason` patterns throughout); no gap found.

No fabricated financial value is ever shown as a fallback in any of the
above — confirmed by the existing `financial-integrity.test.ts` suite
(unchanged, still passing) plus this step's own new tests.

## 9. Accessibility

**Keyboard**: full keyboard pass across all 9 screens. Tabs (period
selectors), buttons, methodology disclosures (`MethodologyPopover`,
`Tooltip`) were already keyboard-operable (native `<button>`s, `Escape` to
close) — re-verified, not re-built. `Table`'s sortable headers already had
`tabIndex`/`onKeyDown`/`aria-sort` — re-verified. Two real gaps closed this
step:
  - `TimeSeriesChart` and `AllocationHistoryChart` were pointer-only
    (`role="img" aria-hidden="true"` on the whole chart). Both now expose a
    focusable overlay (arrow keys step through data points, Home/End jump
    to the ends) with a visible focus ring and an `aria-live` announcement
    of the focused point's date/value/quality — live-verified in the
    browser (screenshots confirm the tooltip appears and advances
    correctly under keyboard control alone).
  - `Table`'s `onRowClick` (currently unused, but a real, exposed part of
    the component's contract) is now keyboard-operable (Enter/Space,
    focus-visible outline) should a future screen use it.

**Screen-reader semantics**: every screen has exactly one meaningful,
*unconditionally rendered* `<h1>` — Overview's was the one exception (its
`<h1>` previously lived only inside a `QueryBoundary`'s success branch, so
it did not exist during loading or on error) and is now fixed. `AppShell`'s
nav landmark (`<nav aria-label="Primary">`), skip link, and `<main
id="main">` were already correct and unchanged. Loading now announces via
`role="status"`; errors/empty/unavailable states already used
`UnavailableMetric`'s plain-language content (unchanged).

**Not changed** (working native patterns, not "over-ARIA'd" per the
brief's explicit instruction): `Tabs` uses real `<button>`s with
`role="tab"`/`aria-selected` but no roving-tabindex/arrow-key pattern from
the full ARIA APG tablist spec — each tab is still independently reachable
and operable via Tab+Enter, which satisfies keyboard operability even
though it deviates from the "manual activation" authoring pattern. Left
as-is: replacing working native buttons with a hand-rolled roving-tabindex
implementation would be exactly the kind of unnecessary abstraction the
brief prohibits, for a component that already works with a keyboard.

**Remaining, explicitly deferred (documented, not fixed)**:
- `AllocationChart` (the donut/bar allocation-by-category chart) still has
  no keyboard interaction of its own — but unlike the two time-series
  charts, it already renders a full accessible `<ul>` legend (every
  segment's label/weight/value as real, readable DOM text, not only an
  SVG), which is itself a working textual alternative. Adding hover/focus
  parity here was judged lower-value than the two time-series charts
  (which had *no* textual alternative at all pointer-free) given the
  effort budget; documented as a P2 follow-up, not fixed this step.
- `BarChart` and `DrawdownChart` remain built, story'd, and **unconsumed by
  any screen** (a Step 6 finding, re-confirmed, not changed this step) —
  no keyboard work was done on either, since no live screen exercises
  them.
- `Tabs`' lack of ARIA-APG roving-tabindex (above) — deliberately not
  "fixed," since it isn't broken.

## 10. Responsive

All 9 screens re-verified this step at 1280px and 375px (plus the existing
mobile nav breakpoint at 900px, unchanged) in the live browser: no
page-level horizontal scroll anywhere, `Table`'s own `overflow-x: auto`
wrapper contains every wide table, `statRow`/`secondaryRow` flex layouts
correctly wrap to a single column at narrow widths (pre-existing pattern,
re-verified on the Step 7 screens too). No layout change was made; this
was confirmation, not remediation.

## 11. Dark mode

Re-verified in the live browser (Income, Risk, Overview, Holdings) in both
light and dark: correct contrast on positive/negative figures, borders,
skeletons, the new Retry button, the new keyboard focus outlines (which
use the existing `var(--color-accent)` token, so they render correctly in
both themes automatically), and the not-found page. No new color was
introduced anywhere in this step — every new visual (focus rings, the
status/retry affordances) reuses existing design tokens
(`--color-accent`, `--color-border`, existing `Button`/`UnavailableMetric`
components).

## 12. Performance

- **Bundle**: 407KB JS / 126KB gzip, single chunk, unchanged in shape by
  this step's additions (a few KB from the new hook logic and
  `NotFoundPage`). Not split by route — at this size, for a 9-route
  internal tool, code-splitting would add complexity (suspense boundaries,
  chunk-loading states) without a measurable user-facing benefit. Not
  done, per the brief's explicit instruction not to prematurely optimise.
- **Rendering**: audited for effect-driven loops and unstable-prop
  re-renders; found none (§1). No `useMemo`/`useCallback` was added except
  where `useNearestPoint` already used them for the pre-existing pointer
  logic (unchanged) and the same pattern was extended for the new keyboard
  handlers (`useCallback` with a stable dependency array, consistent with
  the surrounding code, not a blanket optimisation pass).
- **Chart redraw frequency**: unchanged — D3 geometry is already memoised
  per the existing `useMemo` calls in every chart; the new keyboard state
  (`focusedIndex`) only adds one more piece of state feeding the same
  existing `hovered` value charts already re-rendered on.

## 13. Privacy

Confirmed (not changed): zero `localStorage`/`sessionStorage` usage
anywhere in the app; no analytics/tracking library; the one
`console.error` (in `ErrorBoundary`) logs only the JS error message and
React's component-stack string, never portfolio data; `ActivityRow`'s
transaction descriptions already redact withdrawal recipients as
`[redacted]` server-side (re-verified against live data during Step 7 and
again this step); no PII field exists on any API type consumed by the
frontend. Nothing was added that persists sensitive data browser-side.

## 14. Security

Confirmed (not changed): no `dangerouslySetInnerHTML` anywhere; no
external links (`target="_blank"` or otherwise) exist in the app, so there
is no `rel="noopener"` gap to close; no `eval`/`new Function`; the single
network boundary (`client.ts`) builds every URL via the `URL`/
`searchParams` API rather than string concatenation, so there is no
injectable query-string construction; `NotFoundPage`'s display of the
mistyped path is rendered as React text content (auto-escaped), not
`dangerouslySetInnerHTML`. `npm audit` found 2 high-severity advisories,
both in `js-yaml`, both only reachable through a **dev-only** transitive
dependency (`@redocly/openapi-core`, pulled in by `openapi-typescript`)
used solely to regenerate the OpenAPI-derived types at development time —
never bundled, never executed against user input, never shipped. Not
forced-fixed this step (would require `--force` and risks breaking the
Storybook/Vitest devDependency graph) — documented as P3.

## 15. Configuration (production requirements)

Documented, not implemented (no deployment platform is assumed):

- **`VITE_API_BASE_URL`** — required at build time (or via the hosting
  platform's env-injection) to point the frontend at the real API origin;
  currently falls back to `http://localhost:8000` for local development
  only (`src/api/client.ts`).
- **Backend CORS** (`src/api/app.py`, unchanged/frozen this step): the
  current `allow_origin_regex` matches any `localhost`/`127.0.0.1` port —
  correct for local development, but **must** be replaced with the real
  production frontend origin(s) before deployment. This is a backend
  change and out of this step's scope; flagged here as a production
  blocker to track, not fixed.
- **SPA history-mode routing**: `BrowserRouter` requires the production
  host to rewrite unknown paths to `index.html` (a standard static-host
  rewrite rule) so a direct navigation or refresh on e.g. `/income`
  resolves correctly server-side too, not only via Vite's dev-server
  fallback. No specific hosting platform is assumed or recommended here,
  per the brief.
- No secrets, API keys, or credentials exist in frontend code to audit or
  rotate.

## 16. Application architecture confirmation

- **No financial logic added to React**: every fix this step is
  presentation, state-machine, or accessibility wiring — no screen's
  rendered figure changed, and no new arithmetic across API fields was
  introduced (the pre-existing `financial-integrity.test.ts` suite for
  every screen still passes unchanged).
- **No API contracts changed, no backend touched**: `git status` confirms
  zero files under `src/` (the Python backend) were modified this step.
- **No new frontend network boundary**: `client.ts` remains the only place
  `fetch()` is called; `QueryBoundary`'s new Retry button calls React
  Query's own `refetch()`, which re-invokes the existing `queryFn`, not a
  new request path.
- **Figma: unchanged.** No Figma tool was invoked this step.

## 17. Known remaining issues (explicitly deferred)

- **P2** — `AllocationChart` has no keyboard-driven hover parity with its
  own accessible legend (the legend itself already covers the same
  information as text, so this is a polish gap, not a missing alternative;
  see §9).
- **P2** — `BarChart`/`DrawdownChart` remain unconsumed by any screen
  (pre-existing, Step 6 finding, re-confirmed); no accessibility or other
  work was done on either since nothing renders them.
- **P3** — `npm audit`'s 2 high-severity advisories in a dev-only
  `js-yaml` transitive dependency of the OpenAPI codegen tooling (§14);
  never shipped, never run against user input.
- **P3** — Backend CORS origin regex is dev-only and must be replaced
  before a real deployment (§15); a backend change, out of this step's
  scope.
- **P3** — `Tabs` does not implement the full ARIA APG roving-tabindex tab
  pattern (§9); every tab is independently keyboard-operable regardless,
  so this is a style deviation, not a functional gap.
- **P3** — Bundle is not code-split by route; not a measured problem at
  126KB gzip, so not addressed (§12).
- **P0/P1** — none found or introduced.

---

## Validation gates run this step

- Frontend: `npx vitest run` — **223/223 passed** (was 200 before this
  step; +23 new: `QueryBoundary`, `ErrorBoundary`, `NotFoundPage`, `App`
  routing, `Table` keyboard, `TimeSeriesChart` keyboard).
- `npx tsc -b --force` — clean.
- `npm run build` — clean production build.
- `npx storybook build` — clean.
- `npx oxlint` — zero new findings in any file this step touched (2
  pre-existing findings elsewhere, untouched by this step, not
  introduced here).
- Backend: `pytest` — **333/333 passed**, unchanged (confirms zero
  regression from a step that touched zero backend files).
- Live browser verification: all 9 routes at 1280px and 375px, light and
  dark; navigation, refresh, direct URL entry, back/forward; a real
  backend outage (process killed, not simulated) and recovery; keyboard-
  only interaction on `TimeSeriesChart` (Overview) and
  `AllocationHistoryChart` (Holdings); console inspected on every screen
  visited — zero unexplained errors or warnings once the backend was
  restored (all console errors seen during this step trace directly to
  the deliberate backend-outage test).

READY FOR STEP 9
