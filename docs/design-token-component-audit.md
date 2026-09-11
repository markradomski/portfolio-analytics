# Design Token → Component Audit

Task A of the pre-Step-3 hardening pass. Every component below was
re-inspected directly from its `.tsx`/`.module.css` source (not copied from
`docs/design-system-inventory.md`) — two real discrepancies against that
earlier document were found in the process and are flagged inline where
they occur, with a correction applied to `docs/design-tokens.md` (see
"Corrections" at the end of this file).

Format per component: typography / colour / spacing / radius / shadow /
motion tokens in use, responsive behaviour, semantic states, dark-mode
behaviour, and any literal (non-token) value with a recommendation.

---

## Design system primitives

### Badge
**File**: `design-system/Badge/Badge.tsx` + `.module.css`

- **Typography**: `--text-meta`.
- **Colour**: `--color-{positive,negative,warning,accent}` +
  `-bg` variants; `--color-border`, `--color-text-muted`,
  `--color-text-faint` (neutral tone); `--color-quality-*` (5 quality
  tones) + their own background pairing (reusing `--color-positive-bg`/
  `--color-accent-bg`/`--color-border`/`--color-warning-bg`/`transparent`
  rather than dedicated quality-bg tokens — see note below).
- **Spacing**: `--space-1` (dot gap), `--space-2` (horizontal padding).
- **Radius**: `--radius-small`.
- **Shadow**: none.
- **Motion**: none (no transition on this component).
- **Responsive**: none (inline, intrinsic size, `white-space: nowrap`).
- **Semantic states**: 10 tones total — 5 generic (`positive`, `negative`,
  `warning`, `neutral`, `accent`) + 5 data-quality
  (`quality-actual/calculated/estimated/limited/unavailable`), plus
  `withDot` boolean.
- **Dark mode**: fully token-driven, no explicit dark-mode branch.
- **Literal values**: vertical padding is `2px` (not `var(--space-1)` =
  4px) — a value finer than the spacing scale's smallest step.
  **Recommendation**: keep as-is; this is a deliberate micro-adjustment
  (confirmed as a recurring pattern across 8 components — see "Cross-
  cutting finding: the 2px micro-spacing value" below), not a stray
  literal. Flag for a possible `--space-0`/hairline token in a future
  decision, not resolved here.
- **Note**: data-quality tones reuse the generic tone backgrounds
  (`quality-actual` uses `--color-positive-bg`, `quality-calculated` uses
  `--color-accent-bg`) rather than having their own
  `--color-quality-*-bg` tokens. This is a real, if minor, coupling
  between the two semantic families at the *background* level even
  though the *foreground* colour is correctly kept separate
  (`--color-quality-actual` ≠ `--color-positive`, they only coincide by
  value in the current palette per `docs/design-tokens.md`). Documented
  as an open decision in `docs/design-system-decisions.md`.

### Button
**File**: `design-system/Button/Button.tsx` + `.module.css`

- **Typography**: `--text-body-strong`; `.small` overrides to a literal
  `0.8125rem` (13px) — not a token.
- **Colour**: `--color-text`, `--color-surface`, `--color-text-muted`,
  `--color-border-strong`, `--color-accent` (focus ring).
- **Spacing**: `--space-1/2/3/4`.
- **Radius**: `--radius-small`.
- **Shadow**: none.
- **Motion**: `--motion-hover` (background/border/colour transitions).
- **Responsive**: none.
- **Semantic states**: `variant` (`primary`/`secondary`/`ghost`), `size`
  (`default`/`small`), `:disabled` (opacity 0.45), `:hover`,
  `:focus-visible`.
- **Dark mode**: fully token-driven.
- **Literal values**: `.small`'s `font-size: 0.8125rem` is a literal, not
  drawn from the type scale (no token sits between `--text-meta`'s
  0.75rem and `--text-body`'s 0.9375rem). **Recommendation**: leave as-is
  — introducing a token for one four-character usage would be exactly the
  "add a token because it might be useful" anti-pattern this phase
  forbids. Not flagged as an open decision; too minor to warrant one.

### Card
**File**: `design-system/Card/Card.tsx` + `.module.css`

- **Typography**: `--text-h3` (title), `--text-meta` (subtitle).
- **Colour**: `--color-surface`, `--color-border`, `--color-text`,
  `--color-text-muted`.
- **Spacing**: `--space-3/4/5`.
- **Radius**: `--radius-medium`.
- **Shadow**: `--shadow-low` (`raised` elevation only; `flat` is
  `box-shadow: none`).
- **Motion**: none.
- **Responsive**: none of its own.
- **Semantic states**: `elevation` (`flat`/`raised`).
- **Dark mode**: fully token-driven.
- **Literal values**: `.subtitle { margin-top: 2px }` — same
  cross-cutting micro-spacing value as Badge (see below).

### MetricValue
**File**: `design-system/MetricValue/MetricValue.tsx` + `.module.css`

- **Typography**: `--text-meta` (label/meta), `--text-figure-lg`
  (default value), `--text-body` (unavailable message) — plus one
  **literal** typography declaration for `size="large"` (see C1 below).
- **Colour**: `--color-text-muted`, `--color-text`, `--color-positive`,
  `--color-negative`, `--color-text-faint`.
- **Spacing**: `--space-1/2`.
- **Radius**: none.
- **Shadow**: none.
- **Motion**: none.
- **Responsive**: `size="large"`'s literal `clamp()` scales with
  viewport width (see C1).
- **Semantic states**: `size` (`default`/`large`), sign-coloured via
  `rawValue` (`positive`/`negative`/neutral — neutral = no colour class
  applied, inherits `--color-text`), `unavailableReason` set (renders
  italic message, no value, no sign colour at all).
- **Dark mode**: fully token-driven.
- **Literal values**: `.value.large`'s
  `font: 600 clamp(1.75rem, 1.3rem + 1.5vw, 2.75rem)/1.1 var(--font-mono)`
  is a full literal typography declaration, not a token reference — this
  is Task C1, addressed in `docs/design-system-decisions.md` (kept as a
  literal; not merged with `--text-display`, they are different roles).

### SectionHeader
**File**: `design-system/SectionHeader/SectionHeader.tsx` + `.module.css`

- **Typography**: `--text-meta` (title **and** subtitle — the title uses
  `--text-meta` deliberately, not `--text-h2`; see C2 below), `--text-meta`
  (the "View all →" link, same token again).
- **Colour**: `--color-text-muted`, `--color-text-faint`,
  `--color-border`, `--color-accent`.
- **Spacing**: `--space-2/3/4`.
- **Radius**: none.
- **Shadow**: none.
- **Motion**: none (the "View all" link has no transition — a real, minor
  inconsistency next to `AppShell`'s nav links and `Button`, which do
  transition on hover; not flagged as an open decision, too small to
  matter visually).
- **Responsive**: `flex-wrap` on the header row only.
- **Semantic states**: implicit only — no `variant` prop exists despite
  `Compact` being floated as a likely example in the original phase brief
  (confirmed: no such prop in `SectionHeaderProps`).
- **Dark mode**: fully token-driven.
- **Literal values**: subtitle `margin: 2px 0 0` (cross-cutting, see
  below).

### Table
**File**: `design-system/Table/Table.tsx` + `.module.css`

- **Typography**: `--text-body` (cells), `--text-meta` (headers),
  `--font-mono` (numeric columns, applied directly rather than via a
  `--text-figure` token — see note).
- **Colour**: `--color-border`, `--color-text-muted`, `--color-accent`
  (focus ring).
- **Spacing**: `--space-3/4` (cell padding), `--space-1` (sort icon gap).
- **Radius**: none.
- **Shadow**: none.
- **Motion**: none.
- **Responsive**: `.wrap { overflow-x: auto }` — the table scrolls
  within its own box rather than overflowing the page.
- **Semantic states**: sortable (`aria-sort`), hover row highlight.
- **Dark mode**: fully token-driven.
- **Literal values**: none problematic. **Note**: `.numeric` sets
  `font-family: var(--font-mono)` directly rather than using
  `--text-figure`'s full shorthand (which also sets weight/size/
  line-height) — a deliberate choice, since a table cell needs the
  table's own `--text-body` size/weight with only the family swapped for
  tabular-numeral alignment, not the heavier weight `--text-figure`
  carries. Not a violation; documented so it isn't mistaken for one.

### Tabs
**File**: `design-system/Tabs/Tabs.tsx` + `.module.css`

- **Typography**: `--text-body-strong`.
- **Colour**: `--color-text`, `--color-text-muted`, `--color-text-faint`,
  `--color-border`, `--color-accent`.
- **Spacing**: `--space-1/3`.
- **Radius**: none.
- **Shadow**: none.
- **Motion**: `--motion-hover` (colour/border-colour transitions).
- **Responsive**: `.list { overflow-x: auto }` — added in Phase 5.6 after
  a real horizontal-overflow bug (a full 8-tab period strip didn't fit at
  375px and stretched the page instead of scrolling within its own row).
- **Semantic states**: selected (`aria-selected`), disabled
  (`aria-disabled` + native `disabled` + `title` carrying the backend's
  own reason).
- **Dark mode**: fully token-driven.
- **Literal values**: the active-tab underline is a literal `2px solid
  transparent`/`2px solid var(--color-text)` border — consistent with the
  app-wide 2px-for-emphasis-strokes convention (see Border section of
  `docs/design-tokens.md`), not a one-off.

### Tooltip
**File**: `design-system/Tooltip/Tooltip.tsx` + `.module.css`

- **Typography**: `--text-meta`.
- **Colour**: `--color-text`, `--color-surface`.
- **Spacing**: `--space-2/3`.
- **Radius**: `--radius-small`.
- **Shadow**: `--shadow-medium`.
- **Motion**: none (appears/disappears instantly on hover/focus).
- **Responsive**: `position: fixed`, computed from the trigger's own
  bounding box at open time — no distinct mobile behaviour.
- **Semantic states**: open/closed.
- **Dark mode**: fully token-driven.
- **Literal values**: `max-width: 260px` — a literal, matches
  `MethodologyPopover`'s panel width (also `260px`) exactly. Both are
  small popovers of the same rough shape; not flagged as inconsistent,
  the shared literal is more likely convergent design intent than
  accidental duplication, but worth noting since neither is currently
  consumed in production (see Infrastructure/Future-candidates section).

---

## Data-quality components

### DataQualityBadge
**File**: `data-quality/DataQualityBadge/DataQualityBadge.tsx` (no own
`.module.css` — a thin `Badge` wrapper)

- **Tokens**: entirely inherited from `Badge`'s `quality-*` tones — this
  component itself introduces no new token usage, only a fixed
  `quality → {tone, label}` map.
- **Semantic states**: the 5 `DataQuality` values, 1:1 with `Badge`'s
  quality tones.
- **Dark mode**: inherited from `Badge`.

### DataCoverageBadge
**File**: `data-quality/DataCoverageBadge/DataCoverageBadge.tsx` +
`.module.css`

- **Typography**: `--text-meta`.
- **Colour**: `--color-text-muted`.
- **Spacing/radius/shadow/motion**: none — a single inline text span.
- **Semantic states**: populated vs. "No valuation history available yet"
  (zero observations).
- **Dark mode**: fully token-driven.
- **Literal values**: none. The frequency-label thresholds (`days > 80` →
  "quarterly", `> 25` → "monthly", `> 5` → "weekly", else "daily") inside
  the component logic are numeric constants, not design tokens — out of
  this audit's scope (they're a data-interpretation rule, not a visual
  one), noted only for completeness.

### UnavailableMetric
**File**: `data-quality/UnavailableMetric/UnavailableMetric.tsx` +
`.module.css`

- **Typography**: `--text-h3` (title), `--text-body` (reason).
- **Colour**: `--color-border-strong` (dashed border).
- **Spacing**: `--space-2/3/4`.
- **Radius**: `--radius-medium`.
- **Shadow**: none.
- **Motion**: none.
- **Semantic states**: with/without an `action` slot.
- **Dark mode**: fully token-driven.
- **Literal values**: the border is `1px dashed` — the only *dashed*
  border in the entire codebase (every other border is solid). This is a
  deliberate, singular visual marker for "this box is explaining an
  absence," not a token gap (a `--border-style` token would be
  over-engineering for one usage).

### LimitedDataNotice
**File**: `data-quality/LimitedDataNotice/LimitedDataNotice.tsx` +
`.module.css`

- **Typography**: `--text-body-strong` (title), `--text-meta`
  (explanation).
- **Colour**: `--color-warning-bg`.
- **Spacing**: `--space-3`.
- **Radius**: `--radius-medium`.
- **Shadow**: none.
- **Motion**: none.
- **Semantic states**: none — a single fixed presentation.
- **Dark mode**: fully token-driven.
- **Literal values**: `margin-top: 2px` (cross-cutting, see below).
- **Usage confirmed**: still **not consumed by any feature page** (verified
  again — `grep` for `LimitedDataNotice` outside its own file and story
  finds nothing). Every `limited`-quality figure currently shown
  (Performance, Overview) uses `DataQualityBadge` inline instead. Carried
  forward from Step 1, re-verified true.

### MethodologyPopover
**File**: `data-quality/MethodologyPopover/MethodologyPopover.tsx` +
`.module.css`

- **Typography**: `--text-meta` (trigger), `--text-body` (panel).
- **Colour**: `--color-text-muted`, `--color-text`, `--color-accent`,
  `--color-surface-raised`, `--color-border`.
- **Spacing**: `--space-2/3`.
- **Radius**: `--radius-medium`.
- **Shadow**: `--shadow-medium`.
- **Motion**: none (opens/closes instantly).
- **Semantic states**: open/closed (`aria-expanded`).
- **Dark mode**: fully token-driven.
- **Literal values**: `width: 260px` (see Tooltip note above — same
  literal, same rough shape, both currently used: this one *is* consumed,
  by `MethodologyPanel` on the Performance screen).

---

## Common / infrastructure components

### Skeleton / ChartSkeleton
**File**: `common/Skeleton/Skeleton.tsx` + `.module.css`

- **Colour**: `--color-border`, `--color-border-strong` (shimmer
  gradient stops).
- **Radius**: `var(--radius-${radius})` — the only component that
  interpolates a token name from a prop, rather than switching between
  fixed class names.
- **Motion**: a **literal** `1.4s ease infinite` — see C6 below; not
  `--motion-hover`/`--motion-transition`/`--motion-chart` (none of which
  is a plausible fit for a 1.4s looping shimmer — those three are all
  sub-300ms one-shot transition durations, a different kind of motion
  value entirely).
- **Responsive**: `ChartSkeleton` is `width: 100%`.
- **Semantic states**: animated, or static under
  `prefers-reduced-motion: reduce` (the **only** place in the codebase
  that currently checks this media query).
- **Dark mode**: fully token-driven (the gradient uses border tokens,
  which are already theme-aware).

### QueryBoundary
**File**: `common/QueryBoundary/QueryBoundary.tsx` (no `.module.css` —
pure composition logic, renders other components)

- **Tokens**: none directly — delegates entirely to `ChartSkeleton`
  (loading) and `UnavailableMetric` (error/empty).
- **Semantic states**: pending / error / empty / data — the single
  branch point for all four across the app.

### ErrorBoundary
**File**: `common/ErrorBoundary/ErrorBoundary.tsx` + `.module.css`

- **Typography**: `--text-body-strong` (title), `--text-meta` (detail).
- **Colour**: `--color-negative`, `--color-negative-bg`.
- **Spacing**: `--space-2/3/5`.
- **Radius**: `--radius-medium`.
- **Shadow**: none.
- **Motion**: none.
- **Semantic states**: normal / errored.
- **Dark mode**: fully token-driven.
- **Note**: this is the **only** component in the app that uses
  `--color-negative`/`--color-negative-bg` for something that is not a
  financial loss — a genuine UI/rendering error. Same category of
  "negative tone reused for a non-financial meaning" as the
  reconciliation-status badge (see `docs/design-semantics.md` §4);
  flagged there, not duplicated as a second open decision here.

---

## Layout

### AppShell
**File**: `components/layout/AppShell/AppShell.tsx` + `.module.css`

- **Typography**: `--text-h2` (brand wordmark — **correction to Step 2**,
  see below), `--text-body-strong` (nav links).
- **Colour**: `--color-border`, `--color-text-muted`, `--color-text`,
  `--color-surface`, `--color-accent`.
- **Spacing**: `--space-1/2/3/4/5/6/7`.
- **Radius**: `--radius-small` (nav link hover background).
- **Shadow**: none.
- **Motion**: `--motion-hover`.
- **Responsive**: `900px` breakpoint — sidebar grid collapses to a single
  column, nav becomes a horizontal-scrolling row (`min-width: 0` fix from
  Phase 5.6, preserved).
- **Semantic states**: active nav link (`.linkActive`, styled via
  `NavLink`'s active-class mechanism, not a token-level state).
- **Dark mode**: fully token-driven.
- **Correction to `docs/design-tokens.md`**: that document stated
  `--text-h2` is "not used by name anywhere." That was wrong. It **is**
  used — by `AppShell.module.css`'s `.brand` rule, for the "Portfolio"
  wordmark, which is rendered as a `<p>` (not an `<h2>` or any heading
  element — confirmed in `AppShell.tsx`: `<p className={styles.brand}>
  Portfolio</p>`), and its `font-family` is immediately overridden to
  `var(--font-display)` in the same rule, so the token only actually
  contributes its *weight/size/line-height* (`600 1.375rem/1.3`), not its
  family. So: the token is used, but for a brand wordmark, not a heading —
  a real name/usage mismatch, distinct from the "unused" claim in Step 2.
  `docs/design-tokens.md` has been corrected to reflect this (see
  "Corrections" at the end of this file). Also carried into
  `docs/design-system-decisions.md` as open decision #5.

---

## Charts

### ChartContainer
**File**: `charts/ChartContainer/ChartContainer.tsx` + `.module.css`

- **Typography**: `--text-h3` (optional title).
- **Colour**: `--color-text`.
- **Spacing**: `--space-3`.
- **Responsive**: `ResizeObserver`-driven — the one place every chart's
  width comes from.
- **Semantic states**: none of its own (a pure sizing/accessibility
  wrapper).
- **Accessibility**: always renders a visually-hidden `<p>` with the
  caller's `accessibleSummary` — required prop, not optional.

### ChartTooltip
**File**: `charts/ChartTooltip/ChartTooltip.tsx` + `.module.css`

- **Typography**: `--text-meta`, `--text-body-strong` (date row),
  `--text-figure` (value row).
- **Colour**: `--color-text`, `--color-surface`.
- **Spacing**: `--space-3` (padding), `--space-3` (row gap), literal
  `2px` (row top margin — cross-cutting, see below).
- **Radius**: `--radius-small`.
- **Shadow**: `--shadow-medium`.
- **Responsive**: `min-width: 140px`, flips side near the container's
  right edge (positioning logic, not CSS media queries).

### Crosshair
**File**: `charts/Crosshair/Crosshair.tsx` (no `.module.css` — inline
SVG attributes only)

- **Colour**: `var(--color-text-muted)` (line), `var(--color-accent)`
  (dot fill), `var(--color-surface)` (dot stroke) — all via inline SVG
  attributes, not CSS classes (SVG geometry components in this codebase
  consistently style via props/attributes rather than CSS Modules — a
  deliberate pattern, not an inconsistency, since D3-computed coordinates
  and CSS Modules don't compose well for per-element positioning anyway).
- **Literal values**: `strokeWidth={1}` (line), `r={4}`/`strokeWidth={2}`
  (dot) — the `2px` here matches the app-wide emphasis-stroke convention.

### Axis
**File**: `charts/Axis/Axis.tsx` (no `.module.css` — styles applied
imperatively via `d3.select`, reading CSS custom properties as raw
strings)

- **Colour**: `var(--chart-axis)` (domain/tick lines), `var(--chart-grid)`
  (grid lines), `var(--color-text-muted)` (tick text fill).
- **Literal values**: tick text `font-size: "11px"` and
  `font-family: "var(--font-body)"` set via `.attr(...)` rather than a
  `--text-*` composite token — because d3-axis's tick text needs
  font-size and font-family set as **separate** SVG presentation
  attributes, not a CSS `font` shorthand, so a composite token can't be
  applied directly here even in principle. `11px` itself doesn't match
  any existing `--text-*` token's size (closest is `--text-meta`'s
  `0.75rem` = 12px). **Recommendation**: leave as-is; documented as a
  structural constraint (SVG attribute vs. CSS shorthand), not an
  oversight.

### TimeSeriesChart
**File**: `charts/TimeSeriesChart/TimeSeriesChart.tsx` + `.module.css`

- **Typography**: `--text-meta` (quality caption), `--text-body-strong`
  (tooltip date), `--text-figure` (tooltip value).
- **Colour**: `var(--color-accent)` (line/area/points, via inline SVG
  attributes), `var(--color-positive)`/`var(--color-negative)` (flow
  markers), `--chart-grid`/`--chart-axis` (via `Axis`).
- **Motion**: none (no chart-transition animation — `--motion-chart`
  remains unused here too, see C5).
- **Semantic states**: 4 data-quality line treatments (solid/dashed ×
  opacity), gap (null value, line breaks), single-point dot, flow
  markers (contribution/withdrawal).
- **Literal values**: dashed segment `strokeDasharray="3,3"`, opacity
  `0.55`/`1`/`0.08`/`0.04` — all inline SVG attributes tuned per-visual,
  not tokens; consistent with the Crosshair/Axis pattern of geometry
  components styling via attributes rather than CSS classes.

### AllocationChart
**File**: `charts/AllocationChart/AllocationChart.tsx` + `.module.css`

- **Typography**: `--text-body` (legend label), `--text-figure` (legend
  value, at a literal `font-size: 0.875rem` override — smaller than
  `--text-figure`'s default `1rem`, since the legend needs a table-row
  scale, not a headline scale).
- **Colour**: `--chart-series-1..6` (categorical palette, cycled via
  `i % PALETTE.length`), `--color-unknown` (the `kind: "unknown"` case),
  `--color-text`, `--color-text-muted`.
- **Spacing**: `--space-2/3/4`.
- **Literal values**: swatch `10px × 10px`, `border-radius: 2px` (not
  `--radius-small`'s 4px — deliberately smaller for a legend swatch at
  this scale), column widths `4.5rem`/`7rem` (legend alignment, layout-
  specific, not tokens).
- **Structural gap (carried from Step 1, reconfirmed)**: takes a fixed
  pixel `width` prop directly rather than being composed inside a
  `ChartContainer` render-prop like every other chart — confirmed both
  current call sites (`OverviewPage`, `AllocationSection`) hard-code
  `width={640}`.

### AllocationHistoryChart
**File**: `charts/AllocationHistoryChart/AllocationHistoryChart.tsx` +
`.module.css`

- **Typography**: `--text-body`, `--text-body-strong` (tooltip date),
  `--text-meta` (tooltip rows).
- **Colour**: `--chart-series-1..6` (stacked bands), inherited
  `Axis`/`ChartTooltip`/`Crosshair` tokens.
- **Semantic states**: category present/absent per date (absence, not a
  zero-filled band), null allocation_pct → "Unavailable" in tooltip.
- **Literal values**: `fillOpacity={0.85}` on each band — a single fixed
  value, not per-state.

### BarChart
**File**: `charts/BarChart/BarChart.tsx` + `.module.css`

- **Typography**: `--text-body-strong` (tooltip label), `--text-figure`
  (tooltip value).
- **Colour**: `--color-positive`/`--color-negative`/`--color-accent`
  (tone-to-colour map), inherited `Axis` tokens.
- **Semantic states**: `tone` (`positive`/`negative`/`neutral`, defaults
  to sign-of-value), hover (dims non-hovered bars to `opacity: 0.4`).
- **Confirmed still unused** by any feature page (re-verified: no
  `<BarChart` outside its own file/story).

### DrawdownChart
**File**: `charts/DrawdownChart/DrawdownChart.tsx` + `.module.css`

- **Typography**: `--text-body-strong` (tooltip date), `--text-figure`
  (tooltip value).
- **Colour**: `--color-negative`, `--color-negative-bg` (episode
  shading), `--chart-axis`.
- **Semantic states**: episode window shading, hover crosshair/tooltip.
- **Confirmed still unused** by any feature page (re-verified). The
  backend has no endpoint exposing the per-day drawdown series or
  episode list this component needs (`DrawdownEpisode` is a Pydantic
  model with no route — documented in `docs/api.md`); Performance's
  drawdown section uses a compact stats summary instead.

---

## Feature-level CSS with reusable design decisions

Two patterns recur across `OverviewPage.module.css`,
`PerformancePage.module.css`, and `HoldingsPage.module.css` that are
design decisions, not page-specific layout, and are candidates for
promotion to a shared pattern in Step 7 (not done in this phase):

1. **The metric-group flex-wrap fix** — every one of the three files
   independently repeats:
   ```css
   .summaryRow { display: flex; flex-wrap: wrap; gap: var(--space-6); }
   .summaryRow > * { min-width: 0; flex: 1 1 140px; overflow-wrap: break-word; }
   ```
   (`OverviewPage.module.css`, `PerformancePage.module.css`'s
   `.summaryRow`, `HoldingsPage.module.css`'s `.summaryRow`) — the exact
   same 6 lines, copy-pasted three times rather than shared. This is a
   real duplication (not a token gap) worth a shared class or a
   `MetricGroup` component in a future phase — flagged as open decision
   #11 in `docs/design-system-decisions.md`... actually see note: this is
   additional to the numbered list already in Task D, added there as
   item 14.

2. **The `860px` breakpoint** appears identically in `OverviewPage.
   module.css` and `PerformancePage.module.css` (collapsing a two-column
   grid to one column) but `HoldingsPage.module.css` has **no** page-level
   breakpoint at all — its responsiveness comes entirely from `Table`'s
   own `overflow-x: auto` and `MetricValue`'s flex-wrap. This is the same
   inconsistency Step 2 already flagged (C7) — reconfirmed here from the
   actual files, not assumed.

## Cross-cutting finding: the 2px micro-spacing value

A literal `2px` (not `var(--space-1)` = 4px) appears in **8 places**,
always for the same purpose — a tight vertical gap between a label/date
and the value or explanation directly beneath it:

`Badge` (dot-to-label gap is `--space-1`, but *padding* is `2px`),
`Card.subtitle`, `SectionHeader`'s subtitle, `LimitedDataNotice.
explanation`, `ChartTooltip.row`, `BarChart.label`, `DrawdownChart.date`,
`TimeSeriesChart.date`, `PerformancePage`'s `.reconciliationDetail dd`.

This is consistent and clearly deliberate — not 8 independent oversights —
but it sits below the spacing scale's smallest defined step. **Recorded as
open decision #2 (sizing/fine-spacing token strategy) in
`docs/design-system-decisions.md`**; not resolved here, since introducing
a `--space-0` token for a value currently satisfied by a literal would be
exactly the kind of anticipatory token addition this phase's constraints
forbid.

## Corrections made to earlier documentation

- **`docs/design-tokens.md`**, `--text-h2` row: corrected from "Not
  directly referenced by name" to reflect that it **is** used, by
  `AppShell.module.css`'s `.brand` rule (the nav wordmark, rendered as a
  `<p>`, with `font-family` immediately overridden to `--font-display` in
  the same rule). The surrounding claim that "no component renders
  `1.375rem` text via a `<h2>` element through this token" remains true
  and is preserved — only the "unused" framing was wrong.
