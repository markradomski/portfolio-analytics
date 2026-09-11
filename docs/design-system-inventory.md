# Design System Inventory

Step 1 of the Figma + Storybook Foundation phase: a complete, factual
inventory of the design system that already exists in `web/src`, built
across Phases 5.1–5.7. Nothing here is invented — every item below is a
component, token, or pattern that is actually implemented and (unless
flagged otherwise) actually used by a real screen. Where something exists
but isn't yet consumed by a page, that is stated explicitly rather than
implied.

This document is the reference Steps 3 onward (Figma structure) will be
built from. It changes only when the implementation changes.

## How the system is put together

```
API (FastAPI)
  ↓ HTTP, Decimal-as-string
src/api/client.ts + portfolio.ts + analytics.ts   -- the only place fetch() is called
  ↓
src/hooks/api/                                     -- React Query wrappers
  ↓
src/features/*                                     -- screens (Overview, Performance, Holdings)
  ↓
src/design-system/ + src/components/charts/ + src/components/data-quality/
```

- **Styling**: CSS Modules only (`*.module.css`, one per component), plus
  one global stylesheet, `src/design-system/tokens.css`, imported once in
  `main.tsx`. No Tailwind, no CSS-in-JS, no utility-class framework.
- **Components**: plain function components, TypeScript, no class
  components except `ErrorBoundary` (React requires a class for
  `getDerivedStateFromError`).
- **Charts**: hand-built on D3 (`d3` + `@types/d3`), not a charting library
  — each chart owns its own scales/geometry; React owns state and when the
  D3 effect re-runs.
- **Data**: React Query (`@tanstack/react-query`) is the only place a
  network request is cached; `QueryBoundary` is the only place a
  loading/error/empty state is branched.
- **Testing**: Vitest + Testing Library for unit/component tests,
  Storybook (`@storybook/react-vite` 10.6, with `addon-a11y`,
  `addon-vitest`, `addon-docs`) for the component library. Storybook
  currently has **18 story files**, listed under each component below.
- **Routing**: `react-router-dom`, one `<Route>` per feature under
  `src/app/App.tsx`.

## Foundations

All foundation values live in one file: `src/design-system/tokens.css`. See
`docs/design-tokens.md` for the full token-by-token catalogue; this
section only names the categories that exist.

| Foundation | Exists? | Notes |
|---|---|---|
| Typography | Yes | 3 font families, 9 named type styles (`--text-*`) |
| Colour | Yes | Semantic tokens only — no raw hex in any component |
| Spacing | Yes | An 8-step, 4px-based scale (`--space-1`…`--space-8`) |
| Sizing | Partial | No dedicated sizing scale; component dimensions are set ad hoc per component (chart heights, table cell padding) rather than tokenized |
| Radius | Yes | 4-step scale (`--radius-none/small/medium/large`) |
| Border | Partial | No dedicated border-width token (`1px` is hard-coded everywhere it's used); border *colour* is tokenized |
| Shadow | Yes | 2-step scale (`--shadow-low/medium`), used sparingly by design |
| Breakpoints | **No token exists** | Media query widths (`860px`, `900px`) are hard-coded per component — see gap below |
| Motion | Yes | 3 named durations/easings (`--motion-hover/transition/chart`) |
| Icons | **No icon system** | The one icon-like glyph in the app (`ⓘ` in `MethodologyPopover`) is a literal Unicode character, not an icon component or font |
| Dark mode | Yes | Every colour token is redefined once under `prefers-color-scheme: dark`, plus an explicit `[data-theme="dark"]` override — components never branch on theme themselves |

**Gap to flag for Figma**: breakpoints are not tokenized in code (`860px`
in `OverviewPage.module.css`/`PerformancePage.module.css`, `900px` in
`AppShell.module.css`). Step 4 (Figma foundations) should decide whether to
formalise `768px`/`1024px`-style breakpoint tokens as part of the token
vocabulary, or intentionally keep breakpoints per-component. Not decided in
this phase — flagged, not resolved.

## Components (`src/design-system/`)

The genuinely reusable, page-agnostic primitives. Every one has a
Storybook story.

### Badge
- **Location**: `design-system/Badge/Badge.tsx`
- **Purpose**: The one place any status/tag is rendered — gain/loss tone,
  data-quality tone, or a neutral label.
- **Variants (prop `tone`)**: `positive`, `negative`, `warning`, `neutral`,
  `accent`, `quality-actual`, `quality-calculated`, `quality-estimated`,
  `quality-limited`, `quality-unavailable`.
- **States**: `withDot` (boolean) — a small coloured dot alongside the
  text, so tone is never colour-only.
- **Props**: `tone?`, `children`, `withDot?`.
- **Responsive**: none needed (inline, intrinsic size).
- **Accessibility**: the dot is `aria-hidden`; the text itself is the
  accessible content.
- **Token dependencies**: `--color-{positive,negative,warning,accent}` and
  `-bg` variants, `--color-quality-*`, `--color-border`, `--color-text-muted`,
  `--text-meta`, `--space-1/2`, `--radius-small`.
- **Used by**: `DataQualityBadge`, `UnavailableMetric`, directly in
  `PerformanceSummary`, `CalendarPerformanceTable`, `ReturnDecomposition`.
- **Storybook**: `Badge.stories.tsx`.

### Button
- **Location**: `design-system/Button/Button.tsx`
- **Purpose**: The single button implementation; nothing reaches for a
  raw `<button>`.
- **Variants (prop `variant`)**: `primary`, `secondary` (default), `ghost`.
- **Sizes**: `default`, `small`.
- **States**: `disabled` (native), `:hover`, `:focus-visible`.
- **Props**: all native `<button>` attributes, plus `variant?`, `size?`.
- **Responsive**: none (inline-flex, intrinsic size).
- **Accessibility**: native `<button>` semantics preserved; visible focus
  ring via `:focus-visible`.
- **Token dependencies**: `--text-body-strong`, `--space-*`,
  `--radius-small`, `--color-text`, `--color-surface`,
  `--color-border-strong`, `--motion-hover`.
- **Used by**: `ErrorBoundary` ("Try again"). Not yet used elsewhere —
  most of the app's interactive elements are `<Tabs>` tabs or plain
  `<Link>`s, not buttons.
- **Storybook**: `Button.stories.tsx`.

### Card
- **Location**: `design-system/Card/Card.tsx`
- **Purpose**: The one section-container shape every screen uses.
- **Variants (prop `elevation`)**: `flat` (default), `raised`.
- **Slots**: `title?`, `subtitle?`, `action?` (header row), `children`.
- **Props**: `title?`, `subtitle?`, `action?`, `elevation?`, `children`,
  `className?`.
- **Responsive**: none of its own; children control reflow.
- **Accessibility**: renders a `<section>`; `title` renders as `<h3>` —
  callers are responsible for correct heading nesting (a page's own `<h1>`
  plus `SectionHeader`'s `<h2>` sit above it).
- **Token dependencies**: `--color-surface`, `--color-border`,
  `--radius-medium`, `--space-5`, `--shadow-low`, `--text-h3`,
  `--text-meta`.
- **Used by**: every feature page (`OverviewPage`, `PerformancePage`,
  `HoldingsPage`) as the primary section wrapper.
- **Storybook**: `Card.stories.tsx`.

### MetricValue
- **Location**: `design-system/MetricValue/MetricValue.tsx`
- **Purpose**: The one place a labelled figure (a return, a gain, a
  count) is displayed — formatting happens before this component, it only
  presents an already-formatted string.
- **Sizes**: `default`, `large`.
- **States**: normal, `unavailableReason` set (renders an italic message
  instead of a value — never a bare "N/A"), sign-coloured via `rawValue`
  (positive/negative/neutral, using the same classification
  `formatting/money.ts`'s `sign()` applies).
- **Slots**: `meta?` (arbitrary content below the value — a badge, a
  caption).
- **Props**: `label`, `value`, `rawValue?`, `size?`, `meta?`,
  `unavailableReason?`.
- **Responsive**: `large` uses a `clamp()` font size that scales with
  viewport width.
- **Accessibility**: plain text content; colour is paired with the sign
  already present in the formatted string (`+`/`-`), never colour-alone.
- **Token dependencies**: `--text-meta`, `--text-figure-lg`, `--font-mono`
  (via `--text-figure*`), `--color-{positive,negative,text-muted,
  text-faint}`, `--space-1/2`.
- **Used by**: `OverviewPage`, `PerformanceSummary`, `MethodologyPanel`,
  `HoldingsSnapshot`, `SecurityDetail`, `PerformancePage`'s best/worst and
  drawdown sections.
- **Storybook**: `MetricValue.stories.tsx`.

### SectionHeader
- **Location**: `design-system/SectionHeader/SectionHeader.tsx`
- **Purpose**: The recurring "small-caps title + optional subtitle +
  understated 'View X →' link" shape every section on every screen repeats.
- **Variants**: none currently (no `Compact` variant exists in code,
  despite being mentioned as a likely example in the phase spec — flagged
  as a gap, not fabricated).
- **Slots**: `title`, `subtitle?`, `action?`, `viewAllHref?` +
  `viewAllLabel?`.
- **Props**: `title`, `subtitle?`, `viewAllHref?`, `viewAllLabel?`,
  `action?`.
- **Responsive**: `flex-wrap` on its own row; no distinct mobile layout.
- **Accessibility**: `title` renders as `<h2>` — the one place every
  screen's section-heading hierarchy is established.
- **Token dependencies**: `--text-meta`, `--color-text-muted`,
  `--color-text-faint`, `--color-accent`, `--color-border`, `--space-2/3/4`.
- **Used by**: every `Card` section in `OverviewPage`, `PerformancePage`,
  `HoldingsPage`.
- **Storybook**: `SectionHeader.stories.tsx` (6 stories: default, with
  subtitle, with view-all link, custom label, with action, long
  title/mobile).

### Table
- **Location**: `design-system/Table/Table.tsx`
- **Purpose**: The one data-table implementation — every holdings/
  allocation/calendar table in the app is this component, never a
  hand-rolled `<table>`.
- **Variants**: none (single implementation); per-column `numeric` and
  `sortable` flags change behaviour, not variant identity.
- **States**: sorted (`aria-sort`: `ascending`/`descending`/`none`),
  hover (`.row:hover`).
- **Props**: `columns` (array of `{key, header, numeric?, sortable?,
  render, sortValue?}`), `rows`, `rowKey`, `caption`, `onRowClick?`.
- **Responsive**: the table wrapper is `overflow-x: auto` — a table wider
  than its container scrolls within its own box rather than overflowing
  the page.
- **Accessibility**: native `<table>`/`<thead>`/`<tbody>` semantics
  throughout; a visually-hidden `<caption>`; `aria-sort` on sortable
  `<th>` (never `role="button"`, which would erase the native
  `columnheader` role — this was a real regression caught and fixed in
  Phase 5.1–5.4); sortable headers are keyboard-operable
  (`tabIndex`/`onKeyDown` for Enter/Space) without changing their
  semantic role.
- **Token dependencies**: `--text-body`, `--text-meta`, `--color-border`,
  `--color-text-muted`, `--space-3/4`, `--font-mono` (numeric columns).
- **Used by**: `HoldingsTable`, `AllocationSection`, `CalendarPerformanceTable`
  (Performance), the Overview's inline top-holdings table.
- **Storybook**: `Table.stories.tsx`.

### Tabs
- **Location**: `design-system/Tabs/Tabs.tsx`
- **Purpose**: The one tab-list implementation — every period selector
  (1M…MAX) and every in-page toggle (e.g. Holdings' "By security"/"By
  asset class") is this component.
- **States**: selected (`aria-selected`), disabled (`aria-disabled` +
  native `disabled` + a `title` tooltip carrying the backend's own
  disabled reason).
- **Props**: `items` (`{value, label, disabled?, disabledReason?}[]`),
  `value`, `onChange`, `aria-label`.
- **Responsive**: `overflow-x: auto` on the tab list itself (added in
  Phase 5.6 after a real horizontal-overflow bug was found at 375px) —
  a tab strip that doesn't fit scrolls within its own row rather than
  widening the page.
- **Accessibility**: `role="tablist"`/`role="tab"`, `aria-selected`,
  `aria-disabled`, disabled reason surfaced via native `title` (not just
  colour/opacity), keyboard-operable (native `<button>`).
- **Token dependencies**: `--text-body-strong`, `--color-text`,
  `--color-text-muted`, `--color-text-faint`, `--color-border`,
  `--space-1/3`, `--motion-hover`.
- **Used by**: `usePeriodTabs`/`useCapabilityTabs` (period and capability
  selectors), `OverviewChart`, `PerformanceChart`, `AllocationSection`,
  `SecurityDetail`.
- **Storybook**: `Tabs.stories.tsx`.

### Tooltip
- **Location**: `design-system/Tooltip/Tooltip.tsx`
- **Purpose**: A generic hover/focus tooltip for a static trigger (an info
  icon, a methodology disclosure) — distinct from `ChartTooltip`, which is
  a position-tracking component built for pointer-driven chart crosshair
  interaction, not a general-purpose tooltip.
- **States**: open/closed, triggered by hover *or* focus (keyboard
  parity).
- **Props**: `content`, `children`.
- **Responsive**: `position: fixed`, placed relative to the trigger's own
  bounding box.
- **Accessibility**: `role="tooltip"`, `aria-describedby` linking trigger
  to content, shown on `onFocus`/`onBlur` as well as
  `onMouseEnter`/`onMouseLeave`.
- **Token dependencies**: `--color-text`, `--color-surface`, `--text-meta`,
  `--space-2/3`, `--radius-small`, `--shadow-medium`.
- **Used by**: not currently consumed by any feature page — `Tooltip` is
  built and has a story, but every actual disclosure in the app
  (`MethodologyPanel`'s TWRR/XIRR notes) uses the data-quality-specific
  `MethodologyPopover` instead (see below). Flagged as an unused-in-
  production primitive, not removed.
- **Storybook**: `Tooltip.stories.tsx`.

## Data-quality components (`src/components/data-quality/`)

A distinct family from `design-system/` because these encode the app's
specific financial-data semantics (data quality, coverage, unavailability)
rather than generic UI shapes.

### DataQualityBadge
- **Location**: `data-quality/DataQualityBadge/DataQualityBadge.tsx`
- **Purpose**: The one place a `DataQuality` enum value becomes a visible
  badge — thin wrapper over `Badge` with a fixed tone/label map.
- **States (prop `quality`)**: `actual`, `calculated`, `estimated`,
  `limited`, `unavailable`.
- **Props**: `quality`, `label?` (override the default label text).
- **Token dependencies**: inherits `Badge`'s quality tones.
- **Used by**: `CalendarPerformanceTable`, `PerformanceSummary`.
- **Storybook**: `DataQualityBadge.stories.tsx`.

### DataCoverageBadge
- **Location**: `data-quality/DataCoverageBadge/DataCoverageBadge.tsx`
- **Purpose**: The compact "30 Sept 2020 – 30 June 2026 · 24 valuation
  observations · quarterly source data" line every screen's footer uses —
  reads entirely from `getDataCoverage()`'s response, including inferring
  the frequency label (quarterly/monthly/weekly/daily) from the actual gap
  between observations rather than a hard-coded claim.
- **States**: populated, or "No valuation history available yet" when
  `valuation_observation_count` is 0.
- **Props**: `coverage` (a `DataCoverage` API object).
- **Used by**: `OverviewPage`, `PerformancePage`, `HoldingsPage` footers.
- **Storybook**: `DataCoverageBadge.stories.tsx`.

### UnavailableMetric
- **Location**: `data-quality/UnavailableMetric/UnavailableMetric.tsx`
- **Purpose**: The one "this can't be shown, and here's why" shape — never
  a bare "N/A". Also doubles as the generic empty-state renderer inside
  `QueryBoundary` (a dashed-border card, an "Unavailable" badge, a title,
  a plain-language reason, an optional action).
- **Slots**: `action?` (a call-to-action when the gap is user-resolvable).
- **Props**: `title`, `reason`, `action?`.
- **Token dependencies**: `--color-border-strong` (dashed border),
  `--radius-medium`, `--text-h3`, `--text-body`, `--space-3/4`.
- **Used by**: `QueryBoundary` (error and empty states), `PerformancePage`
  (drawdown/best-worst unavailable), `HoldingsPage` (allocation
  unavailable, no current holdings).
- **Storybook**: `UnavailableMetric.stories.tsx`.

### LimitedDataNotice
- **Location**: `data-quality/LimitedDataNotice/LimitedDataNotice.tsx`
- **Purpose**: "Limited is a feature, not an error" — a value shown
  alongside a plain-language reason, for any metric whose `data_quality`
  is `limited`.
- **Props**: `title`, `explanation`.
- **Token dependencies**: `--color-warning-bg`, `--text-body-strong`,
  `--text-meta`, `--space-3`, `--radius-medium`.
- **Used by**: **not currently consumed by any feature page** — built with
  a story in Phase 5.1–5.4, but no screen built since (Overview,
  Performance, Holdings) has hit a `limited`-quality metric in the real
  dataset in a way that reached for this component specifically; those
  screens instead show `limited` via `DataQualityBadge` inline. Flagged as
  a built-but-unconsumed primitive.
- **Storybook**: `LimitedDataNotice.stories.tsx`.

### MethodologyPopover
- **Location**: `data-quality/MethodologyPopover/MethodologyPopover.tsx`
- **Purpose**: "How is this calculated?" — an inline, keyboard-operable
  disclosure (click to open, click again or Escape to close), not a modal.
- **Props**: `summary` (the compact trigger text), `detail` (the full
  explanation, revealed on demand).
- **Accessibility**: `aria-expanded`, `aria-controls`, `role="note"` on the
  revealed panel, closes on Escape.
- **Used by**: `MethodologyPanel` (Performance screen's TWRR/XIRR
  methodology disclosure).
- **Storybook**: `MethodologyPopover.stories.tsx`.

## Common/layout components (`src/components/common/`, `src/components/layout/`)

### QueryBoundary
- **Location**: `common/QueryBoundary/QueryBoundary.tsx`
- **Purpose**: The one place loading/error/empty/data states are composed
  for any API-backed view. A screen using this never writes its own
  `if (isLoading)` branch.
- **States**: `isPending` → loading (default: `ChartSkeleton`, or a
  caller-supplied `loading` node); `isError` → `UnavailableMetric` with the
  `ApiError`'s own detail message, or a generic "check the API server"
  message for a non-API error; `isEmpty(data)` true → `UnavailableMetric`
  with a caller-supplied `emptyMessage`; otherwise renders `children(data)`.
- **Props**: `query` (a React Query result — or, in every current test
  suite, a plain object shaped like one), `loading?`, `isEmpty?`,
  `emptyMessage?`, `children` (render-prop).
- **Used by**: every data-bearing section on every feature page — the
  single most-used component in the app after `Card`/`SectionHeader`.
- **No Storybook story** (a data-fetching wrapper, not a visual
  component — nothing to render in isolation without a live/mocked query).

### Skeleton / ChartSkeleton
- **Location**: `common/Skeleton/Skeleton.tsx`
- **Purpose**: A deliberate loading placeholder — shape only, never a
  fake financial figure shown while loading.
- **States**: shimmering (animated gradient), or static under
  `prefers-reduced-motion: reduce`.
- **Props**: `Skeleton`: `width?`, `height?`, `radius?`. `ChartSkeleton`:
  `height?` (wraps `Skeleton` at `height: 100%`).
- **Used by**: `QueryBoundary`'s default loading state, and explicit
  `loading={<Skeleton .../>}` overrides throughout Overview/Performance/
  Holdings.
- **No Storybook story.**

### ErrorBoundary
- **Location**: `common/ErrorBoundary/ErrorBoundary.tsx`
- **Purpose**: Catches a genuine rendering exception (a bug), distinct
  from the API/data states `QueryBoundary` already handles (a 503, an
  empty response — normal, expected conditions, not exceptions).
- **States**: normal (renders children), errored (`role="alert"`, error
  message, a `Button` to reset and retry).
- **Used by**: wraps the entire routed app once, in `App.tsx`.
- **No Storybook story** (a class component wrapping arbitrary children,
  not a visual primitive with meaningful isolated states).

### AppShell
- **Location**: `layout/AppShell/AppShell.tsx`
- **Purpose**: The one page chrome — a skip link, the primary navigation,
  and the routed page content.
- **Navigation items**: Overview, Performance, Holdings, Income, Gains,
  Contributions, Risk, History (`Holdings` is already present — no nav
  change was needed for Phase 5.7).
- **Responsive**: a two-column CSS Grid (220px nav + fluid content) above
  900px; below 900px the nav becomes a horizontally-scrolling row above
  the content (`min-width: 0` on both grid items — a real overflow bug
  found and fixed in Phase 5.6, where a grid item's default `min-width:
  auto` let the nav's un-scrolled content stretch the whole page wider
  than the viewport despite its own `overflow-x: auto`).
- **Accessibility**: a "Skip to content" link (visible on focus only),
  `<nav aria-label="Primary">`, active link styling in addition to
  `aria-current` (via `NavLink`'s own active-class mechanism).
- **No Storybook story** (page chrome, not a component with meaningful
  isolated variants).

## Charts (`src/components/charts/`)

Only the primitives that actually exist are listed. `ChartHeader` and
`ChartLegend`, named as possibilities in the phase brief, **do not exist**
as separate components — a chart's title/subtitle is handled by the
`SectionHeader` wrapping it in the page, and `AllocationChart` builds its
own inline legend rather than a shared `ChartLegend` primitive. `LineChart`
and `AreaChart` also don't exist as separate components —
`TimeSeriesChart` renders both a line and a filled area for the same
series in one component, and there is no standalone `StackedBar` (the
closest is `AllocationHistoryChart`'s stacked-area treatment, which is
time-based, not bar-based).

### ChartContainer
- **Location**: `charts/ChartContainer/ChartContainer.tsx`
- **Purpose**: Owns exactly one thing — measuring available width via
  `ResizeObserver` and handing `{width, height}` to the chart body via a
  render-prop. The one place every chart gets its responsive sizing from.
- **Props**: `height?` (default 320), `title?`, `accessibleSummary`
  (required — a plain-language summary read by screen readers,
  independent of whether the chart itself can be seen), `children`
  (render-prop receiving `{width, height}`).
- **Accessibility**: renders a `<figure>`/`<figcaption>` (when `title` is
  given) and a visually-hidden `<p>` carrying `accessibleSummary` — every
  chart's meaning is available to a screen reader regardless of visual
  rendering.
- **Used by**: every chart-bearing section in Overview, Performance, and
  Holdings.
- **No Storybook story** (a sizing wrapper, not a visual primitive with
  states of its own).

### ChartTooltip
- **Location**: `charts/ChartTooltip/ChartTooltip.tsx`
- **Purpose**: The one tooltip shape every chart uses — positioned
  relative to the hovered point, flipped to stay inside the container near
  the right edge.
- **Props**: `x`, `y`, `containerWidth`, `children` (caller supplies the
  actual date/value/quality content).
- **Used by**: `TimeSeriesChart`, `BarChart`, `DrawdownChart`,
  `AllocationHistoryChart`.
- **No Storybook story** (only meaningful composed inside a chart's hover
  state, not standalone).

### Crosshair
- **Location**: `charts/Crosshair/Crosshair.tsx`
- **Purpose**: The vertical line + optional dot marking the hovered x
  position — the shared visual convention every time-series-shaped chart
  uses on hover.
- **Props**: `x`, `height`, `y?`.
- **Used by**: `TimeSeriesChart`, `AllocationHistoryChart` (not
  `DrawdownChart`, `BarChart` — see per-chart notes below).
- **No Storybook story.**

### Axis
- **Location**: `charts/Axis/Axis.tsx`
- **Purpose**: A thin, imperative React wrapper around `d3-axis` — the one
  sanctioned place a D3 selection touches the DOM directly, since d3-axis
  has no declarative React equivalent worth reinventing. Generic over the
  scale's own domain type (`number`/`Date`/`string`) since d3's
  `scaleLinear`/`scaleTime`/`scaleBand` are mutually type-incompatible.
- **Props**: `scale`, `orientation` (`bottom`/`left`), `transform?`,
  `tickCount?`, `tickFormat?`, `grid?`, `gridLength?`.
- **Used by**: every chart primitive.
- **No Storybook story** (a low-level D3 wrapper, meaningless without a
  real scale from a parent chart).

### useNearestPoint (hook, not a component)
- **Location**: `src/hooks/useNearestPoint.ts`
- **Purpose**: The shared hover/crosshair convention every time-series
  chart uses: move the pointer, find the nearest data point by x position
  via `d3.bisector`, expose it as React state.
- **Used by**: `TimeSeriesChart`, `DrawdownChart`, `AllocationHistoryChart`.

### TimeSeriesChart
- **Location**: `charts/TimeSeriesChart/TimeSeriesChart.tsx`
- **Purpose**: The primary historical-series chart — plots a value series
  with the data-quality distinction visible in the line itself. Used for
  two conceptually distinct things depending on the caller: a **dollar
  value** curve (Overview's portfolio-value chart) and a unitless **return
  index** curve (Performance's chart, Holdings' security-detail
  value/units/weight tabs) — the two are visually and semantically
  distinguished via the `formatValue` prop (added in Phase 5.6
  specifically so a return index is never labelled with a `$` sign).
- **States/visual treatment**:
  - A null value breaks the line (a gap), never plotted as zero.
  - Each contiguous run of the same `quality` value renders as its own
    segment: `estimated` (carried-forward) renders lighter (55% opacity)
    and dashed; `actual`/`calculated` render solid.
  - A single-point segment (one day of a given quality between gaps or
    quality changes) renders as a dot rather than being silently dropped.
  - Contributions/withdrawals overlay as small coloured tick marks above/
    below the line (green up, red down) — visually distinct from the line
    itself, so a cash-flow event is never confused with the portfolio's
    own performance.
  - Hover: crosshair + `ChartTooltip` showing date, formatted value (via
    `formatValue`), and a plain-language quality sentence ("Vanguard
    reported" / "Priced this date" / "Carried forward from last known
    price" / "No price available").
- **Props**: `data` (`TimeSeriesPoint[]`), `flows?`, `width`, `height`,
  `valueLabel?`, `formatValue?` (defaults to currency formatting).
- **Responsive**: sized entirely by its `ChartContainer` parent.
- **Accessibility**: `role="img" aria-hidden="true"` on the SVG itself —
  the real accessible summary is the sibling `<p>` `ChartContainer`
  renders, not the chart's own ARIA.
- **Token dependencies**: `--color-accent`, `--color-positive`,
  `--color-negative`, `--chart-grid`, `--chart-axis`, `--text-meta`,
  `--text-body-strong`, `--text-figure`.
- **Used by**: `OverviewChart`, `PerformanceChart`, `SecurityDetail`.
- **Storybook**: `TimeSeriesChart.stories.tsx`.

### AllocationChart
- **Location**: `charts/AllocationChart/AllocationChart.tsx`
- **Purpose**: A single proportional stacked *bar* (not a pie — chosen for
  information density) plus an inline legend/table, for a point-in-time
  allocation breakdown.
- **States**: hover (dims all segments/legend rows except the hovered
  one), `kind: "unknown"` (a genuinely unclassified security renders in a
  distinct grey tone, never silently folded into a generic "Other"),
  `weight: null` (renders "Unavailable" in the legend rather than a
  fabricated 0%).
- **Props**: `segments` (`AllocationSegment[]`: `key`, `label`, `value`,
  `weight`, `kind?`), `width` (fixed, not `ChartContainer`-driven — see gap
  below).
- **Accessibility**: `role="img"` with a descriptive `aria-label` directly
  on the SVG (the one chart that puts its accessible summary on the chart
  itself rather than via `ChartContainer`, since it isn't wrapped in one).
- **Gap to note**: `AllocationChart` takes a fixed pixel `width` prop
  directly, rather than being composed inside a `ChartContainer` render-
  prop the way every other chart is — every current caller
  (`OverviewPage`, `AllocationSection`) passes a hard-coded `640`. This is
  a real inconsistency in the chart family worth deciding on in a later
  phase (not resolved here).
- **Used by**: `OverviewPage`, `AllocationSection` (Holdings).
- **Storybook**: `AllocationChart.stories.tsx`.

### AllocationHistoryChart
- **Location**: `charts/AllocationHistoryChart/AllocationHistoryChart.tsx`
- **Purpose**: A 100%-stacked area chart of allocation proportions over
  time — built in Phase 5.7 because nothing existing plotted a set of
  proportions through time. Uses `d3.stack` purely to lay out already-
  computed proportions; it never derives a weight itself.
- **States**: a category absent from a given date's `allocation_pct` is
  simply absent from that date's stack (never filled in as zero); hover
  shows every category's proportion at the hovered date, including
  "Unavailable" for a null entry.
- **Props**: `data` (`AllocationHistoryPoint[]`), `width`, `height`,
  `categoryLabels?`.
- **Used by**: `HoldingsPage`'s "Allocation over time" section.
- **Storybook**: `AllocationHistoryChart.stories.tsx` (asset-class-over-
  time, single observation, empty).

### BarChart
- **Location**: `charts/BarChart/BarChart.tsx`
- **Purpose**: One bar per period, coloured by sign when the caller
  supplies a `tone` (e.g. positive/negative annual return) or a single
  accent colour when it doesn't (e.g. income, which has no "negative"
  side).
- **Props**: `data` (`BarDatum[]`: `label`, `value`, `tone?`), `width`,
  `height`, `valueLabel?`.
- **States**: hover (dims all bars except the hovered one), tone defaults
  to sign-of-value when `tone` isn't explicitly given.
- **Built, not yet consumed**: **no feature page currently uses
  `BarChart`** — it exists with a full implementation and a Storybook
  story from Phase 5.1–5.4, but Performance's calendar-year section uses
  `Table` instead, and no screen built through Phase 5.7 has reached for
  it. Likely candidate for a future income-by-year or calendar-bar view.
- **Storybook**: `BarChart.stories.tsx`.

### DrawdownChart
- **Location**: `charts/DrawdownChart/DrawdownChart.tsx`
- **Purpose**: Plots the flow-neutral drawdown-from-high-water-mark series
  Phase 4 already computed, shading the peak-to-recovery window for each
  drawdown episode Phase 4 identified. Draws only the numbers it's given —
  never calculates a high-water mark itself.
- **Props**: `data` (`DrawdownPoint[]`: `date`, `drawdownPct`),
  `episodes?` (`DrawdownEpisodeMarker[]`: `peakDate`, `troughDate`,
  `recoveryDate`), `width`, `height`.
- **States**: hover (crosshair + tooltip, via `useNearestPoint`), episode
  shading (a tinted rectangle per identified drawdown episode).
- **Built, not yet consumed**: **no feature page currently uses
  `DrawdownChart`** either. Performance's drawdown section (sec 19 of the
  5.6 spec) deliberately shows a compact *summary* (`DrawdownAnalytics`'s
  own stats — max drawdown %, episode count, longest underwater days)
  rather than the full episode-by-episode chart, since the backend has no
  endpoint exposing the underlying per-day drawdown series or episode list
  yet (`DrawdownEpisode` exists as a Pydantic model but nothing routes to
  it — documented in `docs/api.md`). `DrawdownChart` is a complete,
  tested, story'd primitive waiting for that endpoint, likely for the
  future dedicated Risk screen.
- **Storybook**: `DrawdownChart.stories.tsx`.

## Application patterns

Recurring structural patterns observed across Overview, Performance, and
Holdings — not separate components, but a consistent composition of the
components above that every screen repeats. This is the raw material
Step 7 (Figma patterns) will formalise.

| Pattern | Composed from | Where it appears |
|---|---|---|
| **Page header** | `<h1>` + a one-sentence description paragraph, optionally an understated `← Back to X` link above it | Top of every feature page; `SecurityDetail`'s "← Back to holdings" |
| **Section** | `Card` + `SectionHeader` + content, wrapped in one or more `QueryBoundary`s | Every named section on every screen |
| **Metric group** | A `flex-wrap` row of `MetricValue`s, each with `min-width: 0` + `flex: 1 1 140px` so a long unavailable-reason sentence wraps in its own column instead of forcing the row wider than the viewport (a real mobile-overflow bug found and fixed in Phase 5.6) | Overview header, Performance summary, Holdings snapshot, Security detail |
| **Chart + tabs** | A period/dimension `Tabs` row above a `ChartContainer`-wrapped chart, sharing one selection state (`useSelectedPeriod` for URL-addressable period selection) | `OverviewChart`, `PerformanceChart`, `SecurityDetail`, `AllocationSection` |
| **Chart + table** | An `AllocationChart` (or similar) directly followed by a `Table` presenting the same data in row form | `AllocationSection` |
| **Data table** | `Table` with a caption, numeric right-aligned columns, sortable headers defaulting to a financially-sensible sort (value descending) | `HoldingsTable`, `CalendarPerformanceTable`, Overview's top-holdings table |
| **Empty state** | `QueryBoundary`'s `isEmpty`/`emptyMessage`, rendered via `UnavailableMetric` | Holdings (no current holdings), Overview (no holdings) |
| **Unavailable state** | `UnavailableMetric` with the backend's own `reason`/`note` string, never a bare "N/A" or a fabricated 0 | Allocation-unavailable, TWRR/XIRR-unavailable, benchmark-unavailable |
| **Loading state** | `QueryBoundary`'s default (`ChartSkeleton`) or an explicit `<Skeleton height={n} />` matching the eventual content's shape | Every `QueryBoundary` usage |
| **Data-quality indicator** | `DataQualityBadge` or a quality-toned `Badge`, always paired with text (never colour alone) | Performance summary, calendar table |
| **Coverage footer** | A `Card`-less `<footer>` with `SectionHeader` + `DataCoverageBadge`, at the bottom of every screen | Overview, Performance, Holdings |
| **Reconciliation disclosure** | A `Badge` (status) + a clickable summary line that expands (via local `useState`, not `MethodologyPopover`) into a `<dl>` of the underlying figures | `ReturnDecomposition` (Performance) |
| **Methodology disclosure** | `MethodologyPopover` (click-to-expand, not hover) | `MethodologyPanel` (Performance) |
| **Security-level join** | Two API responses (e.g. `holdings` + `gains/unrealised`) joined client-side by security `code` to build one table row — a presentation join, never a recalculation | `HoldingsTable`, Overview's top-holdings table |
| **Fully-divested / historical-still-available** | A screen's *current* section shows an explicit empty/unavailable state while a *historical* section on the same page continues to render real data, with an explicit note ("Historical data below remains available") preventing the two from being confused | Holdings (current holdings empty, allocation history and security detail still populated) |
| **Date/period selector** | `Tabs` fed by `usePeriodTabs`/`useCapabilityTabs`, whose disabled state and reason come entirely from a backend-reported status — never a frontend rule like `if (years < 1)` | Overview, Performance, Holdings' security detail (Value/Units/Weight, not period-based) |

No **filter** pattern exists yet (no screen offers filtering beyond period/
dimension selection), and no **date-range picker** exists — every date
range in the app comes from a backend-resolved period boundary
(`PerformancePeriod.start_date`/`end_date`), never a user-typed date.

## Summary counts

- Design-system primitives: **8** (`Badge`, `Button`, `Card`,
  `MetricValue`, `SectionHeader`, `Table`, `Tabs`, `Tooltip`)
- Data-quality components: **5** (`DataQualityBadge`, `DataCoverageBadge`,
  `UnavailableMetric`, `LimitedDataNotice`, `MethodologyPopover`)
- Common/layout components: **4** (`QueryBoundary`, `Skeleton`/
  `ChartSkeleton`, `ErrorBoundary`, `AppShell`)
- Chart primitives: **9** (`ChartContainer`, `ChartTooltip`, `Crosshair`,
  `Axis`, `TimeSeriesChart`, `AllocationChart`, `AllocationHistoryChart`,
  `BarChart`, `DrawdownChart`) — of which **2** (`BarChart`,
  `DrawdownChart`) are built and story'd but not yet consumed by any
  feature page.
- Storybook story files: **18**.
- Feature screens: **3** implemented (`Overview`, `Performance`,
  `Holdings`), **5** routed placeholders (`Income`, `Gains`,
  `Contributions`, `Risk`, `History`).
