# Portfolio Product Screen System

Step 7 of the Portfolio Design System programme: the remaining product
screens (Income, Gains, Contributions, Risk, Activity/History) built out
from the existing API and React architecture, plus documentation of
Security Detail (already implemented in Phase 5.7). This step made **no**
changes to the backend, the Figma file, or any design token/primitive
component — every screen composes existing patterns exactly as Overview,
Performance, and Holdings do.

---

## 1. Product information architecture

```
Overview (/)                    -- portfolio snapshot, entry point
├── Performance (/performance)  -- TWRR/XIRR, attribution, calendar
├── Holdings (/holdings)        -- current + historical positions
│   └── Security Detail (/holdings/:code)
├── Income (/income)            -- dividends/distributions/interest
├── Gains (/gains)              -- realised + unrealised capital gains
├── Contributions (/contributions) -- external flows in/out
├── Risk (/risk)                -- volatility, drawdowns, benchmark
└── Activity / History (/history) -- full transaction ledger
```

**Overview vs Performance (Step 9A, chart simplified 9A.2):** these two
screens deliberately do not blur. **Overview** is a *communication layer*
— its primary chart (`PortfolioGrowthChart`) says "blue = money in, green
= money made, red = money lost, line = what I've got" in a couple of
seconds, with $0 as a hard visual floor (nothing drawn below the axis, so
a heavily-withdrawn portfolio just shows the blue foundation falling to
zero — no negative-contribution geometry to explain). No analytics detail,
no explanatory paragraph. The complete signed decomposition lives on
Performance. **Performance** keeps *all* of its
existing analytics (summary, return-index history, return decomposition /
attribution, methodology, calendar, best/worst, drawdown, data coverage)
and additionally carries the *advanced balance-decomposition chart* — the
detailed time series (Total Balance, Contributions & Withdrawals area,
per-period Investment Gain / Loss, cash-flow markers) that lived on
Overview through Step 9 and moved here in Step 9A
(`PerformanceDecompositionChart` wrapping `BalanceDecompositionChart`,
"Balance decomposition" card, between "Performance history" and "Return
decomposition"), with a `Chart | Table` toggle to the authoritative period
bridge. Full contract: `docs/portfolio-wealth-chart.md`.

Overview is the hub; every other screen is a single-level child reachable
either from the top nav (`AppShell`) or via a `SectionHeader`'s
`viewAllHref` from a related screen (e.g. Performance's "Return
decomposition" section links to `/contributions`; its "Best/worst
periods" and "Drawdown" sections link to `/risk`).

## 2. Route inventory

| Route | Component | Status |
|---|---|---|
| `/` | `OverviewPage` | Phase 5.5 |
| `/performance` | `PerformancePage` | Phase 5.6 |
| `/holdings` | `HoldingsPage` | Phase 5.7 |
| `/holdings/:code` | `HoldingsPage` → `SecurityDetail` | Phase 5.7 |
| `/income` | `IncomePage` | **Step 7** |
| `/gains` | `GainsPage` | **Step 7** |
| `/contributions` | `ContributionsPage` | **Step 7** |
| `/risk` | `RiskPage` | **Step 7** |
| `/history` | `HistoryPage` | **Step 7** |

All 9 routes were already registered in `web/src/app/App.tsx` before this
step (a prior phase pre-wired routing ahead of screen content); Step 7 only
replaced the 5 placeholder components with real implementations.

## 3. Screen responsibilities

- **Income** — how much the portfolio has generated in dividends,
  distributions, and interest, and whether that income is growing.
  Trailing/forward yield (`getTrailingIncomeYield`/`getForwardIncomeYield`,
  bundled as `IncomeYieldResponse`), income by year (`getIncome`), and
  year-over-year income growth (`getIncomeGrowth`).
- **Gains** — capital gains, kept strictly separate from income and from
  each other: realised (`getRealisedGains`, positions actually sold,
  lifetime-to-date since no window is requested) and unrealised
  (`getUnrealisedGains`, paper gains on current holdings only).
- **Contributions** — money the investor moved into or out of the
  portfolio, distinct from investment return: lifetime summary
  (`getContributionsSummary`) and a yearly history table
  (`getContributionsHistory`).
- **Risk** — volatility and risk-adjusted return (`getRiskMetrics`),
  drawdown summary (`getDrawdowns`, the same `DrawdownAnalytics` shape
  Performance already renders), distance from the portfolio's own
  historical peak (`getHighWaterMark`), and a benchmark comparison
  (`getRiskBenchmark`).
- **Activity / History** — the full transaction ledger
  (`getActivity`), one chronological, sortable table.
- **Security Detail** (`/holdings/:code`) — already implemented in Phase
  5.7's `SecurityDetail.tsx`; documented here, not rebuilt. Shows a
  security's current snapshot (when still held) plus its full historical
  value/units/weight series (via `TimeSeriesChart`, `formatValue` swapped
  per view) regardless of whether it's currently held — a fully-divested
  security still has real history.

## 4. API capability dependencies

Every adapter function these 5 screens use already existed in
`web/src/api/portfolio.ts` before this step — **zero new backend or API
endpoints were added**:

| Screen | Adapter functions used |
|---|---|
| Income | `income`, `incomeYield`, `incomeGrowth` |
| Gains | `realisedGains`, `unrealisedGains` |
| Contributions | `contributions`, `contributionsHistory` |
| Risk | `risk` (via `useRiskMetrics`), `drawdowns`, `highWaterMark`, `riskBenchmark` |
| Activity/History | `activity` |

Six new React Query hooks were added to `usePortfolioApi.ts`
(`useIncomeGrowth`, `useContributionsSummary`, `useContributionsHistory`,
`useRealisedGains`, `useHighWaterMark`, `useRiskBenchmark`) — thin wrappers
matching the existing one-hook-per-adapter convention exactly (same
`STALE_TIME`, same query-key shape). No hook does anything beyond calling
its adapter function.

## 5. Screen hierarchy (per screen)

Every screen follows the template established by Overview/Performance/
Holdings:

```
<Page>
  <header>              -- h1 + one-line description
  <Card elevation="raised">  -- the headline summary section
    <SectionHeader />
    <QueryBoundary>...</QueryBoundary>
  <Card>                 -- secondary sections, same shape
    ...
  <footer>
    <SectionHeader title="Data coverage" />
    <QueryBoundary query={coverage}>{(c) => <DataCoverageBadge coverage={c} />}</QueryBoundary>
```

No screen introduces a new page-level layout primitive; all 5 use `Card`,
`SectionHeader`, `MetricValue`, `Table`, `QueryBoundary`,
`DataCoverageBadge`, `DataQualityBadge`, and `UnavailableMetric` exactly as
the three earlier screens do.

## 6. Shared patterns reused

| Pattern | Used by (Step 7) |
|---|---|
| Page Header | all 5 |
| Section (Card + SectionHeader) | all 5 |
| Metric Group (`MetricValue` rows) | Income, Gains, Contributions, Risk |
| Data Table | Income, Gains, Contributions, Risk, Activity/History |
| Loading / Empty / Unavailable (`QueryBoundary`) | all 5 |
| Coverage Footer (`DataCoverageBadge`) | all 5 |

No new pattern was created and no existing pattern was modified. The
**Chart + Period Selector** and **Chart + Table** patterns built in Step 5
were not needed here: none of the 5 screens' underlying data series carry
the `quality` field `TimeSeriesChart` requires (Contributions history is
the clearest case — see Known Implementation Gaps), so this step did not
force a chart onto data that cannot support one.

## 7. State model

Every screen composes states through `QueryBoundary`, never a bespoke
`if (isLoading)` branch:

- **Loading** — `ChartSkeleton`/`Skeleton` placeholder while `isPending`.
- **Error** — `UnavailableMetric` with the API's own `ApiError.detail`.
- **Empty** — `UnavailableMetric` with a screen-authored `emptyMessage`,
  shown only when data arrived and the screen's own `isEmpty` predicate
  says so (e.g. "No income recorded yet.", "No holdings to show
  unrealised gains for.") — distinct from an API error.
- **Metric-level unavailable** — for a single `Metric` envelope
  (`{available, reason, value}`, e.g. forward income yield, Sharpe/Sortino,
  benchmark comparison), `MetricValue`'s `unavailableReason` or a nested
  `UnavailableMetric` renders the backend's own `reason` string. Never a
  bare "N/A" and never a fabricated `0`/`0%`.
- **Zero vs unavailable** — kept distinct throughout: a real `$0.00` (e.g.
  Gains's realised loss when nothing was sold at a loss) renders as
  `$0.00`; an absent figure renders as "Not available"/the backend's
  reason. No code path substitutes one for the other.

## 8. Data-quality model

Where the API returns a `Metric` envelope (income yield, risk metrics),
its `data_quality` is shown via `DataQualityBadge` next to the value —
the same 5-value vocabulary (`actual`/`calculated`/`estimated`/`limited`/
`unavailable`) used everywhere else in the app. Plain numeric fields
(`IncomeRow`, `ContributionHistoryRow`, `ActivityRow`, gain snapshots) have
no quality dimension of their own and are rendered without a badge, same
as the equivalent tables on Holdings/Performance.

## 9. Period model

Income, Gains (lifetime), Contributions, and Activity/History all render
the API's default/lifetime window — none of these adapters expose a
period selector the way Performance's TWRR/XIRR periods do, so none of
these screens invented one. Risk's benchmark comparison uses a fixed `1Y`
period (the adapter's own default), matching how Performance defaults its
own period selector to `1Y` before user interaction; a period selector for
the benchmark comparison is listed below as a deferred enhancement, not
built speculatively.

## 10. Navigation

- Top-level nav (`AppShell`) already listed all 8 screens before this
  step; Step 7 changed no navigation code.
- Cross-screen links use the existing `SectionHeader viewAllHref` pattern
  only (Performance → Contributions/Risk/History, already existing;
  Income/Gains/Contributions/Risk do not currently link onward to each
  other, since no natural "drill-down" relationship exists between them
  the way Performance's return-decomposition naturally leads to
  Contributions).

## 11. Responsive rules

All 5 screens verified live at 1280px and 375px. `statRow`/`secondaryRow`
flex layouts wrap to a single column under narrow widths using the same
`flex: 1 1 200px; min-width: 0; overflow-wrap: break-word` rule
Performance/Holdings already use, so a long unavailable-reason sentence
wraps within its own column instead of forcing horizontal scroll. Every
`Table` renders inside the existing `Table` component's own horizontally
scrollable wrapper — no screen-specific table styling was added.

## 12. Accessibility

Each screen has exactly one `<h1>` and one or more `<h2>`s via
`SectionHeader`, matching the existing convention verified in
Overview/Performance/Holdings' own tests. No new interaction pattern
(no new keyboard shortcut, no new focus trap) was introduced; `Table`'s
existing sortable-column behavior is reused as-is on Income/Contributions/
Gains/Activity tables.

## 13. Per-screen contracts

### Income (`/income`)
- `useIncome("yearly")` → `IncomeRow[]` — dividends/distributions/interest/
  franking credits/tax withheld/net income by year.
- `useIncomeYield()` → `IncomeYieldResponse` — trailing/forward yield, each
  a `Metric`.
- `useIncomeGrowth()` → `IncomeGrowthRow[]` — year, gross income, growth %
  (nullable), decomposition basis (a plain string explaining why growth %
  is or isn't computable for that year).
- Coverage footer via `useDataCoverage()`.

### Gains (`/gains`)
- `useRealisedGains()` (no start/end → lifetime) → `RealisedGainSummary` —
  realised gain, realised loss, net realised gain, each a direct API
  field, never summed client-side.
- `useUnrealisedGains()` → `UnrealisedGainSnapshot[]` — per-holding market
  value, cost basis, unrealised gain ($ and %). Empty for the fully-
  divested state (0 current holdings) — verified live.
- Coverage footer via `useDataCoverage()`.

### Contributions (`/contributions`)
- `useContributionsSummary()` → `ContributionSummary` — total contributed/
  withdrawn/net, investment growth (nullable), income received, current
  value, as-at date.
- `useContributionsHistory("yearly")` → `ContributionHistoryRow[]` —
  contributions/withdrawals/net/cumulative figures by year.
- No chart: see Known Implementation Gaps below.
- Coverage footer via `useDataCoverage()`.

### Risk (`/risk`)
- `useRiskMetrics()` → `RiskMetrics` — volatility/Sharpe/Sortino, each a
  `Metric`. Sharpe/Sortino render as `UnavailableMetric` with the
  backend's own reason ("no risk_free_rate_annual configured...") — this
  is the real, currently-configured state of this portfolio, not a test
  fixture.
- `useDrawdowns()` → `DrawdownAnalytics` — the same shape/pattern
  Performance's "Drawdown" card already renders.
- `useHighWaterMark()` → `HighWaterMarkStatus` — current value, high-water
  mark, distance from high ($ and %), days since high.
- `useRiskBenchmark("1Y")` → `BenchmarkComparison` — renders as
  `UnavailableMetric` when `relative_return` is null (this portfolio has
  no benchmark registered); renders portfolio/benchmark/relative return
  plus a methodology-mismatch note when a benchmark is available.
- Coverage footer via `useDataCoverage()`.

### Activity / History (`/history`)
- `useActivity()` (no start/end → full ledger) → `ActivityRow[]` —
  transaction id, trade date, type, code (nullable), units (nullable),
  price (nullable), net amount (nullable), description.
- Confirmed no PII field exists on `ActivityRow`; the backend's own
  `description` field already redacts withdrawal recipients as
  `[redacted]` — verified live against real data.
- Coverage footer via `useDataCoverage()`.

### Security Detail (`/holdings/:code`) — already implemented, Phase 5.7
- `SecurityDetail.tsx` (111 lines), rendered from `HoldingsPage` when a
  `:code` param is present. Current snapshot (`HoldingRow`,
  `UnrealisedGainSnapshot`) when still held, full historical series via
  `useHoldingHistory(code)` and `TimeSeriesChart` with a value/units/weight
  view switch (`Tabs`). No changes made this step; documented here per the
  Step 7 spec's explicit instruction not to rebuild it.

## 14. Known API/backend gaps (not fixed — frontend cannot fix these)

- **High-water-mark distance appears to be `$0.00` / `0.0%` / `0 days`
  even though `current_value` ($118.42) is well below `high_water_mark`
  ($172.35)** for this portfolio's real data. `RiskPage` renders exactly
  what `getHighWaterMark()` returns (`distance_from_high: "0E-25"`,
  `distance_from_high_pct: "0"`, `days_since_high: 0`, confirmed via a
  direct `curl` against the running API) — this looks like a backend
  calculation defect, not a frontend rendering bug, and Step 7's rules
  prohibit any backend/analytics change. Flagged here for a follow-up
  investigation in `src/analytics`, not fixed.
- **No benchmark is registered** for this portfolio, so `/risk`'s
  benchmark comparison is genuinely `unavailable` for every period. This
  is expected, not a gap — flagged so it isn't mistaken for a bug when
  reviewing the live screen.
- **No `risk_free_rate_annual` is configured**, so Sharpe/Sortino are
  genuinely `unavailable`. Same as above — expected, not a bug.

## 15. Known implementation gaps

- **Contributions has no chart.** `ContributionHistoryRow` carries no
  `quality` field, and `TimeSeriesChart`'s data contract requires one per
  point (the same contract documented in `docs/figma-chart-library.md`).
  Rather than inventing a quality value the backend never supplied, this
  screen is table-only — matching the actual shape of the data, not a
  design-system violation.
- **No period selector on Risk's benchmark comparison.** `useRiskBenchmark`
  accepts a `period` argument; the screen currently fixes it to `"1Y"`
  rather than adding a new period-selector UI, since none of Overview/
  Performance/Holdings' period-selector components are directly reusable
  without a period-list adapter this endpoint doesn't expose the way
  `getReturns()` does. A future enhancement, not an open design decision.
- **Activity/History has no pagination or date filtering** despite a long
  real ledger (150+ rows for this account) — same "the whole table is the
  point" approach `CalendarPerformanceTable` and other existing tables
  take; sorting by date is available via the existing `Table` sortable-
  column mechanism.

No new open design-system decision (the #1-16 register in
`docs/design-system-decisions.md`) was created or resolved by this step.

---

## Final report

**Product architecture**: 5 new screens (Income, Gains, Contributions,
Risk, Activity/History) implemented; Security Detail confirmed already
complete from Phase 5.7 and documented, not rebuilt. Full IA in §1.

**Implemented**: `IncomePage`, `GainsPage`, `ContributionsPage`,
`RiskPage`, `HistoryPage` — each composing existing `Card`/`SectionHeader`/
`MetricValue`/`Table`/`QueryBoundary`/`DataCoverageBadge`/
`DataQualityBadge`/`UnavailableMetric` only. 6 new thin React Query hooks
in `usePortfolioApi.ts`.

**Deferred**: benchmark period selector on Risk (§15); Contributions
chart, deliberately not built (§15, data lacks a `quality` field);
Activity/History pagination (§15).

**API**: zero new endpoints; zero adapter changes. All 6 new hooks map
1:1 onto adapter functions that already existed in `portfolio.ts`.

**Financial logic**: none added to React. Every rendered figure traces to
one named API field; verified structurally by a `financial-integrity.test.ts`
per screen (no `.reduce(`, no arithmetic across two API fields, no
`src/engine`/`src/history` imports) — same convention as Performance/
Holdings.

**Design system**: no new component, token, or pattern. All 5 screens use
only components/patterns that existed before this step.

**Figma**: unchanged. The frozen Step 6 file remains the reference; no
new nodes created.

**Charts**: none added. Contributions deliberately has no chart (§15);
all other new screens use tables/metrics only, matching what their data
actually supports.

**States**: loading/error/empty/unavailable/zero kept distinct across all
5 screens, verified via unit tests and live browser checks (real
fully-divested-portfolio data: 0 current holdings on Gains, real
"unavailable" Sharpe/Sortino/benchmark on Risk).

**Responsive**: verified live at 1280px and 375px, light and dark, for
all 5 new screens — no horizontal overflow, correct wrapping.

**Accessibility**: single `<h1>` per screen, logical heading hierarchy,
no new interaction pattern introduced.

**Testing**: 31 new frontend tests (render + state coverage per screen)
plus 15 new financial-integrity structural tests (3 per screen × 5
screens), all passing. Full suite: 200/200 frontend (vitest), clean
`tsc -b`, clean `vite build`, clean `storybook build`, 333/333 backend
(pytest, unchanged/regression-checked).

**Documentation**: this file, `docs/product-screen-system.md`.

**Open decisions**: none added or resolved. One new backend-suspected
defect flagged for future investigation (§14, high-water-mark distance),
explicitly not fixed per this step's frontend-only scope.

READY FOR STEP 8
