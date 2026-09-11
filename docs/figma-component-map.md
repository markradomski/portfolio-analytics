# Figma Component Map

Task E of the pre-Step-3 hardening pass: classification only. Nothing in
this document creates a Figma file, a new component, or a new pattern —
it sorts what already exists (per `docs/design-system-inventory.md` and
the Task A audit) into the seven tiers Step 3 will build the Figma file
structure from.

## 1. Foundations

Typography, colour, spacing, radius, shadow, motion, theme — see
`docs/design-tokens.md` for the full catalogue. Figma candidate: `01 —
Foundations` + `02 — Tokens` pages (per the original phase brief's page
list).

## 2. Primitives

`Badge`, `Button`, `Card`, `MetricValue`, `SectionHeader`, `Table`,
`Tabs`, `Tooltip`. Component contracts below.

## 3. Domain components

`DataQualityBadge`, `DataCoverageBadge`, `UnavailableMetric`,
`LimitedDataNotice`, `MethodologyPopover`. Component contracts below.
See open decision #13 (`docs/design-system-decisions.md`) on whether
these get their own Figma page/subsection or sit alongside Primitives.

## 4. Composition patterns

Not components — recurring compositions of Primitives/Domain components,
confirmed present across Overview, Performance, and Holdings (see
`docs/design-system-inventory.md`'s "Application patterns" table for the
full list with "composed from"/"where it appears" detail):

Page Header · Section · Metric Group · Chart + Tabs · Chart + Table ·
Data Table · Empty State · Unavailable State · Loading State · Data
Quality Indicator · Coverage Footer · Reconciliation Disclosure ·
Methodology Disclosure · Security-level Join · Fully-divested/
historical-still-available · Date/period selector.

No pattern in this list was invented for this document — each maps to at
least one real, currently-shipping screen composition. "Metric Group" is
currently three copy-pasted CSS implementations rather than one shared
one (open decision #14) — the pattern is real even though its code isn't
unified yet.

## 5. Charts

`ChartContainer`, `ChartTooltip`, `Crosshair`, `Axis`, `TimeSeriesChart`,
`AllocationChart`, `AllocationHistoryChart`, `BarChart`, `DrawdownChart`.
Documented in full in `docs/design-system-inventory.md`'s Charts section
and the Task A audit — not repeated as contracts here, since the
component-contract format (variants/slots/states) fits UI primitives more
naturally than chart primitives, whose meaningful surface is visual
structure (axes, hover treatment, data-quality treatment), already
catalogued.

`BarChart` and `DrawdownChart` are built and story'd but not consumed by
any feature page — see Future Candidates below and open decision #12.

## 6. Infrastructure

`QueryBoundary`, `Skeleton`/`ChartSkeleton`, `ErrorBoundary`, `AppShell`,
`useNearestPoint`. These are *not* Figma-representable in the usual
sense — `QueryBoundary` is pure branching logic, `useNearestPoint` is a
hook with no visual form of its own (it drives `TimeSeriesChart`/
`DrawdownChart`/`AllocationHistoryChart`'s hover behaviour). `Skeleton`,
`ErrorBoundary`, and `AppShell` do have visual form and should appear
somewhere in Figma (Skeleton as a loading-state pattern under Composition
Patterns; ErrorBoundary's error card under the same; `AppShell` as the
one page-chrome frame every screen composition sits inside), but none of
the three is a reusable *design-system component* the way a `Badge` or
`Table` is — each exists exactly once in the app.

## 7. Future candidates

Explicitly **not created** in this phase — classification only:

- `BarChart` — built, story'd, unused by any screen (candidate: a future
  income-by-year or calendar-bar view).
- `DrawdownChart` — built, story'd, unused; blocked on a backend endpoint
  exposing the per-day drawdown series/episode list (`DrawdownEpisode` is
  a Pydantic model with no route — see `docs/api.md`), likely surfaces on
  a future dedicated Risk screen.
- `Tooltip` — built, story'd, currently unused in production (every
  actual disclosure uses the more specific `MethodologyPopover` instead).
- `LimitedDataNotice` — built, story'd, currently unused in production
  (every `limited`-quality figure shown so far uses `DataQualityBadge`
  inline instead).
- A potential icon system — no current need beyond the two literal
  Unicode glyphs (`ⓘ`, `→`) and `Table`'s literal `▲`/`▼` sort
  indicators; see open decision #9.
- A potential date-range picker — does not exist; every date range in the
  app today comes from a backend-resolved period boundary, never a
  user-typed date.
- A potential `ChartLegend` — does not exist as a shared component;
  `AllocationChart` builds its own inline legend, and no other chart has
  a legend at all (a categorical multi-series chart with a shared legend
  hasn't been needed yet).
- A potential `ChartHeader` — does not exist; a chart's title/subtitle is
  handled by the `SectionHeader` wrapping it at the page level, not a
  chart-owned header component.
- A potential standalone `LineChart`/`AreaChart` — `TimeSeriesChart`
  already renders both a line and a filled area for one series in one
  component; splitting them into separate primitives has no current use
  case forcing it.
- A potential shared `MetricGroup` component — see open decision #14;
  the pattern is real (three duplicated implementations), a unifying
  component is not.

None of the above is created in this phase. This is the exact list Step
3 (and any later implementation phase) should consult before building
something that sounds plausible but isn't actually needed yet.

---

## Component contracts

### Badge

- **Component**: Badge
- **Purpose**: The one place any status/tag is rendered — gain/loss
  tone, data-quality tone, or a neutral label — with an optional coloured
  dot so tone is never colour-only.
- **Variants**: `tone` — `positive`, `negative`, `warning`, `neutral`,
  `accent`, `quality-actual`, `quality-calculated`, `quality-estimated`,
  `quality-limited`, `quality-unavailable` (10 total).
- **States**: `withDot` on/off (default on).
- **Slots**: `children` (the label text/content).
- **Props**: `tone? = "neutral"`, `children`, `withDot? = true`.
- **Tokens**: see Task A audit's Badge entry — 10 colour-tone pairs,
  `--text-meta`, `--space-1/2`, `--radius-small`, plus a literal `2px`
  vertical padding (documented, not tokenized — see open decision #2).
- **Responsive**: none — inline, intrinsic size.
- **Accessibility**: the dot is `aria-hidden`; tone is always paired with
  distinct text, never colour alone.
- **Used by**: `DataQualityBadge`, `UnavailableMetric`,
  `PerformanceSummary`, `CalendarPerformanceTable`, `ReturnDecomposition`.
- **Storybook**: `Badge.stories.tsx`.
- **Figma candidate**: yes — Primitives.
- **Notes/open decisions**: data-quality tones reuse generic-tone
  background colours rather than having their own (see Task A audit);
  reconciliation-status usage of the sign tones is open decision #10.

### Button

- **Component**: Button
- **Purpose**: The single button implementation — nothing in the app
  reaches for a raw `<button>` with a hand-rolled class.
- **Variants**: `variant` — `primary`, `secondary` (default), `ghost`.
  `size` — `default`, `small`.
- **States**: `:disabled`, `:hover`, `:focus-visible` (native/CSS, not
  props).
- **Slots**: `children`.
- **Props**: all native `<button>` attributes + `variant?`, `size?`.
- **Tokens**: `--text-body-strong`, `--space-1/2/3/4`, `--radius-small`,
  `--color-text`, `--color-surface`, `--color-text-muted`,
  `--color-border-strong`, `--color-accent`, `--motion-hover`.
- **Responsive**: none.
- **Accessibility**: native `<button>` semantics preserved throughout;
  `:focus-visible` outline.
- **Used by**: `ErrorBoundary` ("Try again"). No other current consumer —
  most interaction in the app is via `Tabs` or `Link`, not `Button`.
- **Storybook**: `Button.stories.tsx`.
- **Figma candidate**: yes — Primitives.
- **Notes/open decisions**: `.small`'s font-size (`0.8125rem`) is a
  literal, not a token — too minor to register as an open decision (see
  Task A audit).

### Card

- **Component**: Card
- **Purpose**: The one section-container shape every screen uses.
- **Variants**: `elevation` — `flat` (default), `raised`.
- **States**: None currently — no hover/active/disabled state.
- **Slots**: `title?`, `subtitle?`, `action?` (header row), `children`
  (body).
- **Props**: `title?`, `subtitle?`, `action?`, `elevation?`, `children`,
  `className?`.
- **Tokens**: `--color-surface`, `--color-border`, `--radius-medium`,
  `--space-3/4/5`, `--shadow-low` (raised only), `--text-h3`,
  `--text-meta`.
- **Responsive**: none of its own; children control reflow.
- **Accessibility**: renders `<section>`; `title` renders `<h3>` — caller
  is responsible for correct heading nesting above it.
- **Used by**: every feature page, as the primary section wrapper.
- **Storybook**: `Card.stories.tsx`.
- **Figma candidate**: yes — Primitives.
- **Notes/open decisions**: none beyond the `2px` subtitle-margin literal
  (see Task A audit, cross-cutting finding).

### MetricValue

- **Component**: MetricValue
- **Purpose**: The one place a labelled figure is displayed — formatting
  happens before this component; it only presents an already-formatted
  string, never a raw number.
- **Variants**: `size` — `default`, `large`.
- **States**: normal; `unavailableReason` set (italic message, no value,
  no sign colour); sign-coloured (`positive`/`negative`/neutral, via
  `rawValue`).
- **Slots**: `meta?` (arbitrary content below the value — a badge, a
  caption).
- **Props**: `label`, `value`, `rawValue?`, `size?`, `meta?`,
  `unavailableReason?`.
- **Tokens**: `--text-meta`, `--text-figure-lg`, `--color-{positive,
  negative,text,text-muted,text-faint}`, `--space-1/2`; `size="large"`
  uses a **literal** typography declaration, deliberately not
  `--text-display` (see open decision #4 — resolved as "intentionally
  distinct," no change).
- **Responsive**: `large` scales via an inline `clamp()`.
- **Accessibility**: colour is always paired with the sign already
  present in the formatted string (`+`/`-`), never colour-alone.
- **Used by**: `OverviewPage`, `PerformanceSummary`, `MethodologyPanel`,
  `HoldingsSnapshot`, `SecurityDetail`, Performance's best/worst and
  drawdown sections.
- **Storybook**: `MetricValue.stories.tsx`.
- **Figma candidate**: yes — Primitives.
- **Notes/open decisions**: open decision #4 (display typography), fully
  investigated and resolved as "leave unchanged" in this phase.

### SectionHeader

- **Component**: SectionHeader
- **Purpose**: The recurring section-hierarchy shape (small-caps title +
  optional subtitle + understated "View X →" link) every section on every
  screen repeats.
- **Variants**: **None currently.** (A `Compact` variant was floated as a
  likely example in the original phase brief but does not exist in code —
  do not invent it here.)
- **States**: None currently.
- **Slots**: `title`, `subtitle?`, `action?`, `viewAllHref?` +
  `viewAllLabel?`.
- **Props**: `title`, `subtitle?`, `viewAllHref?`, `viewAllLabel?`,
  `action?`.
- **Tokens**: `--text-meta` (title **and** subtitle — see open decision
  #5 on the unrelated `--text-h2` naming mismatch, which does *not*
  involve this component using that token), `--color-text-muted`,
  `--color-text-faint`, `--color-accent`, `--color-border`,
  `--space-2/3/4`.
- **Responsive**: `flex-wrap` on its own row only.
- **Accessibility**: `title` renders `<h2>` — the one place every
  screen's section-heading hierarchy is established.
- **Used by**: every `Card` section across Overview, Performance,
  Holdings.
- **Storybook**: `SectionHeader.stories.tsx` (6 stories).
- **Figma candidate**: yes — Primitives.
- **Notes/open decisions**: none beyond the "no Compact variant exists"
  correction above.

### Table

- **Component**: Table
- **Purpose**: The one data-table implementation — every holdings/
  allocation/calendar table in the app is this component.
- **Variants**: **None** (single implementation) — per-column `numeric`/
  `sortable` flags are column-level configuration, not table-level
  variants.
- **States**: sorted (`aria-sort: ascending/descending/none`), row hover.
- **Slots**: none in the usual sense — `columns`/`rows` fully define
  content via render-props per column.
- **Props**: `columns`, `rows`, `rowKey`, `caption`, `onRowClick?`.
- **Tokens**: `--text-body`, `--text-meta`, `--color-border`,
  `--color-text-muted`, `--color-accent`, `--space-3/4`, `--font-mono`
  (numeric columns, applied directly — see Task A note on why this
  doesn't use `--text-figure`'s full shorthand).
- **Responsive**: `overflow-x: auto` — scrolls within its own box rather
  than overflowing the page.
- **Accessibility**: native `<table>`/`<thead>`/`<tbody>`, visually-hidden
  `<caption>`, `aria-sort` (never `role="button"` — a real regression
  fixed in Phase 5.1–5.4), keyboard-operable sortable headers
  (`tabIndex`/Enter/Space) without altering the native `columnheader`
  role.
- **Used by**: `HoldingsTable`, `AllocationSection`,
  `CalendarPerformanceTable`, Overview's top-holdings table.
- **Storybook**: `Table.stories.tsx`.
- **Figma candidate**: yes — Primitives.
- **Notes/open decisions**: none new.

### Tabs

- **Component**: Tabs
- **Purpose**: The one tab-list implementation — every period selector
  and every in-page dimension toggle is this component.
- **Variants**: **None** — behaviour is entirely data-driven via
  `items`.
- **States**: selected (`aria-selected`), disabled (`aria-disabled` +
  native `disabled` + `title` carrying the backend's own reason).
- **Slots**: none — `items` fully defines content.
- **Props**: `items`, `value`, `onChange`, `aria-label`.
- **Tokens**: `--text-body-strong`, `--color-text`, `--color-text-muted`,
  `--color-text-faint`, `--color-border`, `--color-accent`,
  `--space-1/3`, `--motion-hover`.
- **Responsive**: `overflow-x: auto` on the tab list (Phase 5.6 fix for a
  real 375px overflow bug).
- **Accessibility**: `role="tablist"`/`role="tab"`, `aria-selected`,
  `aria-disabled`, disabled reason exposed via native `title` (not colour/
  opacity alone), keyboard-operable (native `<button>`).
- **Used by**: `usePeriodTabs`/`useCapabilityTabs` consumers —
  `OverviewChart`, `PerformanceChart`, `AllocationSection`,
  `SecurityDetail`.
- **Storybook**: `Tabs.stories.tsx`.
- **Figma candidate**: yes — Primitives.
- **Notes/open decisions**: none new.

### Tooltip

- **Component**: Tooltip
- **Purpose**: A generic hover/focus tooltip for a static trigger (an
  info icon, a methodology disclosure) — distinct from `ChartTooltip`
  (position-tracking, pointer-driven chart hover).
- **Variants**: **None currently.**
- **States**: open/closed, triggered by hover *or* focus.
- **Slots**: `children` (the trigger element).
- **Props**: `content`, `children`.
- **Tokens**: `--color-text`, `--color-surface`, `--text-meta`,
  `--space-2/3`, `--radius-small`, `--shadow-medium`.
- **Responsive**: `position: fixed`, computed from the trigger's own
  bounding box.
- **Accessibility**: `role="tooltip"`, `aria-describedby`, shown on
  `onFocus`/`onBlur` as well as mouse events (keyboard parity).
- **Used by**: **no current production consumer** — built with a story,
  every actual disclosure in the app uses `MethodologyPopover` instead.
- **Storybook**: `Tooltip.stories.tsx`.
- **Figma candidate**: see open decision #12 — likely a clearly-marked
  "not yet in production use" placement rather than the primary library
  section, pending Step 3's structural decision.
- **Notes/open decisions**: unused-in-production status, tracked as a
  Future Candidate above.

---

### DataQualityBadge

- **Component**: DataQualityBadge
- **Purpose**: The one place a `DataQuality` enum value becomes a visible
  badge — a thin, fixed tone/label map over `Badge`.
- **Variants**: `quality` — `actual`, `calculated`, `estimated`,
  `limited`, `unavailable` (5).
- **States**: default label, or caller-supplied `label` override.
- **Slots**: none.
- **Props**: `quality`, `label?`.
- **Tokens**: entirely inherited from `Badge`'s quality tones — this
  component introduces no tokens of its own.
- **Responsive**: inherited from `Badge`.
- **Accessibility**: inherited from `Badge`.
- **Used by**: `CalendarPerformanceTable`, `PerformanceSummary`.
- **Storybook**: `DataQualityBadge.stories.tsx`.
- **Figma candidate**: yes — Domain components.
- **Notes/open decisions**: none new (see `docs/design-semantics.md` §1
  for the underlying axis this renders).

### DataCoverageBadge

- **Component**: DataCoverageBadge
- **Purpose**: The compact coverage summary line ("30 Sept 2020 – 30
  June 2026 · 24 valuation observations · quarterly source data") every
  screen's footer uses — reads entirely from `getDataCoverage()`'s
  response, including inferring the source-frequency label from the
  actual gap between observations, never a hard-coded claim.
- **Variants**: **None.**
- **States**: populated, or "No valuation history available yet" (zero
  observations).
- **Slots**: none.
- **Props**: `coverage` (a `DataCoverage` API object).
- **Tokens**: `--text-meta`, `--color-text-muted`.
- **Responsive**: none — a single inline text span.
- **Accessibility**: plain text; no special treatment needed.
- **Used by**: `OverviewPage`, `PerformancePage`, `HoldingsPage` footers.
- **Storybook**: `DataCoverageBadge.stories.tsx`.
- **Figma candidate**: yes — Domain components.
- **Notes/open decisions**: none.

### UnavailableMetric

- **Component**: UnavailableMetric
- **Purpose**: The one "this can't be shown, and here's why" shape —
  never a bare "N/A." Also serves as `QueryBoundary`'s generic error/empty
  renderer.
- **Variants**: **None** — a single fixed layout (title + badge +
  reason + optional action).
- **States**: with/without an `action` slot.
- **Slots**: `action?`.
- **Props**: `title`, `reason`, `action?`.
- **Tokens**: `--color-border-strong` (dashed border — the only dashed
  border in the app), `--radius-medium`, `--text-h3`, `--text-body`,
  `--space-2/3/4`.
- **Responsive**: none of its own.
- **Accessibility**: plain text content, always paired with the badge's
  "Unavailable" label, never colour alone.
- **Used by**: `QueryBoundary` (error/empty states),
  `PerformancePage` (drawdown/best-worst unavailable), `HoldingsPage`
  (allocation unavailable, no current holdings).
- **Storybook**: `UnavailableMetric.stories.tsx`.
- **Figma candidate**: yes — Domain components.
- **Notes/open decisions**: the dashed border is a deliberate singular
  visual marker, not a missing `--border-style` token (see Task A audit).

### LimitedDataNotice

- **Component**: LimitedDataNotice
- **Purpose**: "Limited is a feature, not an error" — a value shown
  alongside a plain-language reason, for any `limited`-quality metric.
- **Variants**: **None.**
- **States**: **None** — a single fixed presentation.
- **Slots**: none.
- **Props**: `title`, `explanation`.
- **Tokens**: `--color-warning-bg`, `--text-body-strong`, `--text-meta`,
  `--space-3`, `--radius-medium`.
- **Responsive**: none.
- **Accessibility**: a fixed "Limited" badge always paired with text.
- **Used by**: **no current production consumer** — re-verified during
  this audit; every `limited`-quality figure shown so far uses
  `DataQualityBadge` inline instead.
- **Storybook**: `LimitedDataNotice.stories.tsx`.
- **Figma candidate**: see open decision #12.
- **Notes/open decisions**: unused-in-production status, tracked as a
  Future Candidate above.

### MethodologyPopover

- **Component**: MethodologyPopover
- **Purpose**: "How is this calculated?" — an inline, keyboard-operable
  disclosure (click to open/close, or Escape), not a modal.
- **Variants**: **None.**
- **States**: open/closed (`aria-expanded`).
- **Slots**: none — `summary`/`detail` are plain string props, not
  render-props.
- **Props**: `summary`, `detail`.
- **Tokens**: `--color-text-muted`, `--color-text`, `--color-accent`,
  `--color-surface-raised`, `--color-border`, `--text-meta`,
  `--text-body`, `--space-2/3`, `--radius-medium`, `--shadow-medium`.
- **Responsive**: fixed `260px` panel width (matches `Tooltip`'s panel
  width exactly — convergent design intent, not a bug).
- **Accessibility**: `aria-expanded`, `aria-controls`, `role="note"` on
  the revealed panel, closes on Escape.
- **Used by**: `MethodologyPanel` (Performance screen's TWRR/XIRR
  disclosure).
- **Storybook**: `MethodologyPopover.stories.tsx`.
- **Figma candidate**: yes — Domain components.
- **Notes/open decisions**: none new.

---

## Step 3 addendum: Figma build status

All classifications above were carried out unchanged into the actual
Figma file (`Portfolio Design System`, see `docs/figma-architecture.md`
for the full page-by-page map). This addendum records only what Step 3
itself surfaced that Step 2 couldn't have known from static source
inspection alone — it does not restate anything already covered above.

- Every Primitive and Domain component listed above now has a real Figma
  `COMPONENT`/`COMPONENT_SET` on `03 Components`, with variant coverage
  matching what's documented in each contract (see "Variants" per
  component above — nothing beyond that was added in Figma).
- All 9 Charts now have a representative reference card on `04 Charts`.
- `Tooltip`, `LimitedDataNotice`, `BarChart`, `DrawdownChart` are indexed
  on `99 Archive` per open decision #12's recommendation (option b) —
  confirmed, not just proposed.
- **New fact, only visible once a real instance was placed in a
  composition**: the Reconciliation Disclosure pattern (`05 Patterns`)
  reuses a `Badge` `Tone=positive` instance for a `PASS` reconciliation
  status, and that variant's baked-in label text is "Actual" (its
  original data-quality-adjacent wording), not a reconciliation-specific
  word like "Explained." This is a concrete instance of the exact overlap
  `docs/design-semantics.md` §4 and open decision #10 already flagged in
  the abstract — Step 3 didn't create the overlap, it made it visible.
  Left as-is, not fixed, consistent with "do not resolve open decisions
  merely to make the Figma file cleaner."
