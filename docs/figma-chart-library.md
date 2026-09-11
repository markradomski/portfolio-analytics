# Figma Chart Library

Step 6 deliverable. Formalises the existing chart system (`web/src/
components/charts/`) as a set of visual contracts — what each chart
communicates, not how D3 computes it. Everything below was re-verified
against the live application (browser-checked at 1280px/375px, light/dark,
on Overview/Performance/Holdings — see §11) and the actual source, not
carried forward from `docs/design-system-inventory.md`/`docs/figma-
component-library.md` unchecked. Where those documents already covered a
fact accurately, this document references rather than repeats it.

No chart implementation, financial calculation, API, or backend code
changed in this step. No new chart type, colour, or token was introduced.

## 1. Purpose

Make the existing chart language legible as a Figma system: a designer
composing a new screen should be able to pick "TimeSeriesChart" or
"AllocationChart" the same way they'd pick "Badge," understanding its
visual contract without reading `d3.scaleTime()`/`bisector()`/SVG path
code. Figma represents the *contract* (axes, tooltip, data-quality
treatment, states); Storybook and React remain the only place the
contract is actually implemented and tested.

## 2. Chart inventory

| Chart | Purpose | Data shape | Screen(s) | Interaction | Responsive | States |
|---|---|---|---|---|---|---|
| `ChartContainer` | Sizes any chart body to its available width (`ResizeObserver`) and carries the required `accessibleSummary` | `{width, height}` handed to a render-prop child | Wraps every chart except `AllocationChart` | none (a sizing wrapper) | Re-measures on any container resize | n/a |
| `ChartTooltip` | The one tooltip shape every chart's hover state uses | caller-supplied content (date/value/quality) | `TimeSeriesChart`, `BarChart`, `DrawdownChart`, `AllocationHistoryChart` | positioned at hovered point, flips near right edge | follows chart width | shown/hidden |
| `Crosshair` | Vertical line + optional dot at the hovered x position | `{x, height, y?}`, pre-computed by the caller's D3 scales | `TimeSeriesChart`, `AllocationHistoryChart` (not `DrawdownChart`/`BarChart`, which hover differently) | pointer-driven | n/a | shown/hidden |
| `Axis` | Imperative `d3-axis` wrapper — the one sanctioned direct-DOM D3 touch | a D3 scale (`scaleTime`/`scaleLinear`/`scaleBand`) | every chart | none | tick count fixed per chart (not viewport-responsive — see §12) | n/a |
| `TimeSeriesChart` | Primary historical-series chart — plots EITHER a dollar value (Overview) OR a unitless return index (Performance, Holdings' security detail), never both meanings in one chart instance | `TimeSeriesPoint[]` (`date`, `value: string\|null`, `quality`), optional `FlowMarker[]` | Overview (value), Performance (return index), Holdings' Security Detail (value/units/weight, via `formatValue`) | hover → crosshair + tooltip; period selector externally driven | `ChartContainer`-sized | 4 quality treatments + gap + flow markers |
| `PortfolioGrowthChart` | The Overview screen's simple wealth-snapshot chart (Step 9A, simplified 9A.2) — blue Contributions area from the **$0 floor** up to `max(net_contributions, 0)`, green Investment Gain / red Investment Loss band up to the Total Balance line, **all clamped ≥ $0**. Communication layer, not the signed accounting identity — that's on Performance. Never a rate of return. | `PortfolioGrowthPoint[]` (`date`, `portfolio_value`, `net_contributions`, `investment_gain`, …) | Overview only (via `PortfolioGrowthSection`) | hover/keyboard → crosshair + plain 3-line tooltip; period selector + persistent `ChartLegend` externally in the section | `ChartContainer`-sized (340px) | gain / loss / zero, negative net contributions (blue stays at $0, never drawn below), withdrawal lowers the blue foundation, gap-on-null |
| `BalanceDecompositionChart` | The advanced Performance decomposition chart (Step 9A) — the detailed time series that lived on Overview through Step 9: Total Balance line, zero-anchored Contributions & Withdrawals area, per-period Investment Gain (green) / Investment Loss (red) areas, contribution/withdrawal markers. A *wealth* decomposition in dollars, never a rate of return. | `PortfolioGrowthPoint[]` (`date`, `portfolio_value`, `net_contributions`, `period_investment_gain`, `cash_flow_events`, …) | Performance only (via `PerformanceDecompositionChart`) | hover/keyboard → crosshair + rich tooltip (event amount, value, net contributions, period & cumulative gain) | `ChartContainer`-sized (340px) | gain / loss / zero, isolated single-day gain as a bar, negative net contributions (never clamped), gap-on-null |
| `PerformanceDecompositionChart` (feature wrapper) | Wraps `BalanceDecompositionChart` for the Performance page: slices the growth series to the selected period, persistent `ChartLegend`, `Chart \| Table` toggle. The `Table` view is the authoritative period bridge (`Beginning + Contributions − Withdrawals + Investment return = Ending`) from `PerformanceOverview`, verbatim. Additive to the existing Performance page. | `PortfolioGrowthPoint[]` + `PerformanceOverview` for the selected period | Performance only ("Balance decomposition" card) | `Chart \| Table` toggle (`Tabs`); period from `useSelectedPeriod` | `ChartContainer`-sized (340px) chart; `Table` view | Chart: explicit unavailable when the window has no valued history; Table: unavailable when a boundary valuation is missing (bridge never fabricated) — section always visible (Step 9A.1) |
| `ChartLegend` | A persistent, hover-independent colour key — line/area swatches matching a chart's own paint | `ChartLegendItem[]` (`label`, `color`, `shape?`, `opacity?`) | `PortfolioGrowthSection` | none (static) | wraps on narrow screens | n/a |
| `AllocationChart` | A single proportional stacked bar + inline legend — chosen over a pie for information density | `AllocationSegment[]` (`key`, `label`, `value`, `weight`, `kind?`) | Overview, Holdings' `AllocationSection` | hover dims non-hovered segments/legend rows | **fixed 640px width — not `ChartContainer`-sized** (see §4) | known/unknown segment, unavailable weight |
| `AllocationHistoryChart` | 100%-stacked area of allocation proportions over time | `AllocationHistoryPoint[]` (`date`, `weights`, `allocation_pct`) | Holdings' "Allocation over time" | hover → crosshair + per-category tooltip | `ChartContainer`-sized | category present/absent per date (never zero-filled) |
| `BarChart` | One bar per period, coloured by sign | `BarDatum[]` (`label`, `value`, `tone?`) | **none — built, story'd, not consumed by any screen** | hover dims non-hovered bars | `ChartContainer`-sized | tone defaults to sign-of-value |
| `DrawdownChart` | Flow-neutral drawdown-from-high-water-mark series with episode shading | `DrawdownPoint[]` + `DrawdownEpisodeMarker[]` | **none — built, story'd, not consumed by any screen** (Performance shows a compact stats summary instead; no endpoint exposes the per-day series yet) | hover → crosshair + tooltip | `ChartContainer`-sized | episode shading, gap-on-null |

**Chart compositions (not standalone components)**, confirmed against
`docs/figma-pattern-library.md` (Step 5) rather than re-derived:

- **Chart + Period Selector** — `Tabs` + a chart, sharing `useSelectedPeriod`. Used by Overview and Performance.
- **Chart + Table** — `AllocationChart` + `Table` sharing one data response. Used by Holdings.
- **Chart + Methodology Disclosure** — Performance's TWRR/XIRR `MetricValue`s sit above a `MethodologyPopover`, not attached to the chart itself, but conceptually paired: the chart shows the return-index shape, the disclosure explains the number beside it.
- **Chart + Data Quality** — every chart's own quality-segment treatment (below) *is* this pattern; there is no separate "chart + data-quality-notice" composition beyond what's built into `TimeSeriesChart`/`AllocationHistoryChart` themselves, confirmed by inspecting every chart-bearing section: none pairs a chart with a standalone `LimitedDataNotice` today.

No new chart category was added to this inventory — it is exactly the 9
components + 4 compositions already catalogued in `docs/design-system-
inventory.md` and `docs/figma-component-map.md`.

## 3. Chart architecture (confirmed, not re-derived)

```
React owns: state, composition, hover state via useNearestPoint, routing
D3 owns:    scales, path/area generation, axis tick generation
```

The one sanctioned exception is `Axis`, an imperative `d3.select` wrapper
— documented in Step 1 and re-confirmed here by reading the source again:
no other chart component touches the DOM directly outside React's own
JSX/SVG rendering.

## 4. Geometry

- **Chart height**: no single canonical value — each call site picks its
  own (`ChartContainer`'s own default is 320px; Overview's main chart
  passes 340; Performance's return-history chart and Holdings' security
  detail chart pass 280; Holdings' allocation-over-time chart passes
  260). This was already documented as a "no dedicated sizing scale" gap
  in `docs/design-tokens.md` and is restated here, not resolved.
- **Internal margin**: every chart except `AllocationChart` and
  `AllocationHistoryChart`/`DrawdownChart`/`BarChart` (which share the
  same convention) uses the identical `MARGIN = { top: 16, right: 16,
  bottom: 28, left: 64 or 56 }` object, confirmed by reading each
  component's source — a real, consistent geometry contract, not
  independently reinvented per chart.
- **Minimum usable chart area**: not enforced by any component — a chart
  given 0 width (before `ChartContainer`'s `ResizeObserver` fires) simply
  doesn't render its children (`width > 0` guard in `ChartContainer`).
- **Tooltip/crosshair positioning**: computed from the same `xScale`/
  `yScale` the chart's own geometry uses — never independently
  positioned, so a tooltip can never point to a location the chart data
  didn't actually produce.
- **Table/chart alignment**: `AllocationChart`'s legend column widths
  (`4.5rem` weight / `7rem` value) are its own layout constants, not
  shared with `Table`'s numeric column widths — the two happen to align
  informally in the "Chart + Table" pattern because both use
  `IBM Plex Mono` for numerals, not because of a shared alignment grid.

**The `AllocationChart` sizing exception — confirmed present, not
fixed**: every other chart is composed inside a `ChartContainer`
render-prop and receives `{width, height}` from `ResizeObserver`-driven
measurement. `AllocationChart` instead takes a `width` prop directly, and
both current call sites (`OverviewPage.tsx`, `AllocationSection.tsx`)
hard-code `width={640}`. This was flagged in Step 1
(`docs/design-system-inventory.md`) and recorded as open decision #11
(`docs/design-system-decisions.md`) — **still open, not changed here**,
per this step's explicit instruction not to "fix" it unless the
implementation itself has already changed (it has not).

## 5. Axes

- **X axis**: `d3.scaleTime()`-driven, `tickCount` fixed per chart (6 for
  `TimeSeriesChart`/`DrawdownChart`/`AllocationHistoryChart`), rendered
  via the shared `Axis` component. No responsive tick-density reduction
  exists — the same tick count is requested at 1280px and 375px (d3-axis
  itself may render fewer ticks than requested if they'd collide, but no
  component code changes the *requested* count by viewport).
- **Y axis**: `d3.scaleLinear()`, `tickCount` 4–5 depending on the chart,
  with grid lines (`--chart-grid`) and a formatted tick label.
- **Tick formatting — confirmed against source, not assumed**:
  - Currency: `formatMoney()` (or the caller-supplied `formatValue` prop
    on `TimeSeriesChart`, added specifically so a non-currency series
    like Performance's return index is never given a `$` sign).
  - Percentage: `formatPercentSigned()` (`DrawdownChart`'s y-axis).
  - Index/unitless: `formatIndex()` (Performance/Holdings' security
    detail units/weight views).
  - Dates: the X axis uses D3's own default time-tick formatting (no
    custom date-format function is passed to `Axis` for the X axis in
    any chart) — a real, honest gap: there is no explicit "date tick
    format contract" beyond D3's built-in behaviour. Documented as a
    known gap (§17), not invented as if a custom format existed.
  - Negative values: rendered by the same formatter as positive ones
    (`formatMoney`/`formatPercentSigned` both handle negative numbers
    via their sign already) — no separate "negative axis" treatment
    exists or is needed.
  - Large/compact values: no `formatMoneyCompact()` is used on any
    chart axis today (it exists in `formatting/money.ts` but isn't wired
    to any chart's `Axis` — confirmed via grep) — a real, minor gap, not
    invented as present.
- **Grid lines**: `--chart-grid` token, Y axis only (`grid` prop),
  `gridLength` spans the plot width.
- **Zero line**: `BarChart` and `DrawdownChart` both draw an explicit
  zero-baseline (`yScale(0)`) as a `<line>` in `--chart-axis` colour —
  confirmed present in both; `TimeSeriesChart`/`AllocationHistoryChart`
  have no zero line (their domains don't necessarily include zero
  meaningfully — a return-index chart's "zero" isn't the portfolio's
  break-even point the way a bar chart's is).

## 6. Series treatment

### Time series (`TimeSeriesChart`)

- **Line weight**: solid segments 2px, `estimated` (carried-forward)
  segments 1.25px, dashed (`strokeDasharray: "3,3"`), 55% opacity — a
  visibly lighter, dashed treatment, never indistinguishable from a real
  observation.
- **Interpolation**: `d3.curveMonotoneX` — a smooth but monotone curve
  (never overshoots between points), the same curve for every
  quality segment.
- **Point visibility**: a single-point quality run (one day of a given
  quality surrounded by gaps/quality changes) renders as a 3px dot
  rather than being silently dropped — confirmed in source and by the
  existing `TimeSeriesChart.test.tsx` regression test.
- **Hover state**: crosshair + `ChartTooltip` via `useNearestPoint`
  (shared `d3.bisector`-based hook).
- **Missing data**: a `null` value **breaks the line** (`d3.line().defined()`),
  never plotted as zero or interpolated across.
- **Sparse observations**: see §8 — this is the chart most directly
  shaped by this dataset's quarterly cadence.
- **Contribution/withdrawal flow markers**: small green (`--color-
  positive`, contribution) / red (`--color-negative`, withdrawal) tick
  marks above/below the line — visually and structurally distinct from
  the line itself (a separate SVG element, not a line-colour change), so
  "money moved" is never confused with "the portfolio performed."

### Area/filled series

Only `TimeSeriesChart` (a filled area under the line, `fillOpacity: 0.08`
or `0.04` for estimated segments) and `AllocationHistoryChart` (a 100%-
stacked area, `d3.stack`) currently use a filled-area treatment. **No new
area-chart language was introduced** — `AreaChart` as a standalone
primitive does not exist and was not created in this step, since
`TimeSeriesChart` already renders both a line and its own area in one
component and no second use case demands splitting them apart.

### Bars (`BarChart`)

- **Bar width**: `d3.scaleBand()` with `padding(0.3)`.
- **Positive/negative treatment**: bars extend from the zero baseline
  either up (positive) or down (negative); `tone` defaults to
  sign-of-value when the caller doesn't supply one explicitly.
- **Hover**: non-hovered bars dim to `opacity: 0.4`.
- **Grouping/stacking**: `BarChart` has no grouped or stacked mode —
  one bar per datum only. **No `StackedBar` component was created** in
  this step; `AllocationHistoryChart`'s stacked-area treatment is the
  closest existing thing to a "stacked" visual and is time-based, not
  bar-based, per the existing, unchanged classification in `docs/figma-
  component-map.md`.

## 7. Portfolio-specific chart semantics

Re-verified against `docs/design-semantics.md` (Steps 1–2) and the live
application — all four axes remain structurally independent in the
chart system specifically, not just in `Badge`/`MetricValue`:

- **Financial sign** (`positive`/`negative`/`neutral`): `--color-positive/
  negative`, used for `BarChart`'s bar colour, `TimeSeriesChart`'s flow
  markers, and nowhere else in the chart family — a chart's *line* colour
  is always `--color-accent` (blue) regardless of whether the portfolio
  is up or down; only discrete markers (bars, flow ticks) carry sign
  colour. This is a real, confirmed implementation choice: a
  `TimeSeriesChart` plotting a losing period does not turn its line red.
- **Data quality** (`ACTUAL`/`CALCULATED`/`ESTIMATED`/`LIMITED`/
  `UNAVAILABLE`): drives `TimeSeriesChart`'s per-segment dash/opacity
  treatment and `AllocationHistoryChart`'s per-date category presence —
  never a colour hue change, only opacity/dash, so quality is legible
  without relying on colour perception alone.
- **Capability** (`available`/`unavailable` + reason): not rendered
  *inside* any chart — an unavailable chart (e.g. Holdings' allocation
  when `status: "unavailable"`) is replaced entirely by `UnavailableMetric`
  outside the chart component, confirmed in `HoldingsPage.tsx` and
  `AllocationSection.tsx`. The chart component itself has no "unavailable"
  visual state of its own to draw — the *pattern* wrapping it decides
  not to render the chart at all.
- **Reconciliation** (`PASS`/`FAIL`/`LIMITED`): not a chart concept at
  all — reconciliation is rendered via `Badge` in `ReturnDecomposition`
  (see `docs/figma-pattern-library.md` pattern 10), never inside a chart.

**None of these four are collapsed into one generic "chart colour
system."** Confirmed: `--chart-series-1..6` (the categorical palette used
by `AllocationChart`/`AllocationHistoryChart` to distinguish securities/
asset classes) is a *fifth*, separate colour concept again — categorical
identity, not sign, quality, capability, or reconciliation. A security's
palette colour carries no meaning beyond "this is a different category
from that one."

## 8. Sparse historical data

This dataset's real coverage (`docs/design-tokens.md`, restated here in
its chart-specific consequence): **24 actual valuation observations**
across **~2,190 days** (30 Sept 2020 – 30 June 2026), meaning the vast
majority of days in any `TimeSeriesChart`/`AllocationHistoryChart` are
carried-forward (`estimated`), not genuinely observed.

**Confirmed via live browser check (§11 below, both light and dark
mode)**: the chart does **not** visually imply daily observed data. The
carried-forward stretch between two real quarterly observations renders
as a visibly lighter, dashed segment — a viewer can see, directly in the
line itself, exactly which stretches are real and which are held over.
No smoothing, no interpolation between the sparse real points beyond the
curve's own monotone interpolation (which connects real points to real
points, or real points to the start/end of a carried-forward run — it
does not fabricate intermediate data).

**The chart deliberately renders a continuous line through carried-
forward values** (rather than, say, a stepped flat line or a gap) — this
is documented as the existing, intentional behaviour per this step's own
instruction, not changed. The *dashed* treatment is what prevents this
continuity from being misread as continuous observation.

## 9. Fully-divested portfolio state

Re-verified live (§11) on the real portfolio, which is currently in
exactly this state: **0 current holdings, $126.88 cash, historical data
for 7 years including individual securities (VAS, VGS, etc.) fully
intact**.

The four states this step asks to be kept distinct, confirmed as
actually distinct in the chart system:

| State | Chart behaviour | Verified |
|---|---|---|
| No current holdings | `HoldingsTable`'s `UnavailableMetric` ("No current holdings — this portfolio is fully divested to cash...") replaces the table; **no chart is affected** — `AllocationHistoryChart` on the same screen keeps rendering 7 years of real data | Live, Holdings screen |
| No historical data | Would mean `AllocationHistoryChart` itself renders its own empty state ("No allocation history available yet.") — **not this portfolio's actual condition**, confirmed by the historical chart rendering real bands | Live (contrapositive verified: historical chart is populated, not empty) |
| Unavailable data | Holdings' *current* `AllocationChart`/table pairing is replaced by `UnavailableMetric` ("no allocation computed for 2026-06-30") because there's nothing to allocate today — a capability/computation fact about *today*, not about history | Live, Holdings screen |
| Zero value | The portfolio's *current* total value ($126.88) is a real, non-zero number — cash, not "zero." No chart in this application currently needs to distinguish a genuine `$0` portfolio value from an unavailable one, since this dataset never reaches literal zero; the distinction is documented as a general `MetricValue`/chart rule (`unavailable ≠ zero`) rather than demonstrated with a live example that doesn't exist | Documented, not demonstrable live |

No historical holdings were fabricated to demonstrate any of the above —
every example above is the real API response for this real portfolio.

## 10. Period controls

The chart period selector (`Tabs`, fed by `usePeriodTabs`) is
capability-driven, confirmed again live in this step (§11): the `1M` tab
was disabled with a real backend-reported reason
("nearest valuations span 91 days...") in earlier phase verification, and
in this step's own live check the same tab set (`1M`/`3M`/`6M`/`YTD`/
`1Y`/`3Y`/`5Y`/`MAX`) rendered with `1M`/`3M` visibly muted/disabled. No
period was hard-coded as always-available; every tab's enabled/disabled
state is resolved from `PerformancePeriod.status`/`note` per period
label, never a frontend rule. **No date-range picker exists in the
implementation and none was created** — every date boundary in every
chart comes from a backend-resolved `PerformancePeriod.start_date`/
`end_date`, never a user-typed date.

Responsive: the tab row scrolls horizontally within its own strip
(`overflow-x: auto`, the Phase 5.6 fix) rather than widening the page —
**re-confirmed live at 375px in this step** (§11): the period tabs remain
on one row, partially scrolled, with the rest of the page correctly
un-overflowed (`document.documentElement.scrollWidth === clientWidth`).

## 11. Tooltip and crosshair system

- **Trigger**: `onPointerMove` over a transparent hit-rect spanning the
  plot area; `useNearestPoint`'s `d3.bisector` finds the nearest real
  data point by x position (never an interpolated "in-between" point).
- **Placement**: `ChartTooltip` positions itself at the hovered point's
  x, flipping to the left when within 160px of the container's right
  edge — confirmed unchanged from Step 1's documentation.
- **Value hierarchy**: date first (`--text-body-strong`), then the
  primary value (`--text-figure`, sign-coloured via the same `sign()`
  logic `MetricValue` uses), then a plain-language quality sentence
  ("Vanguard reported" / "Priced this date" / "Carried forward from last
  known price" / "No price available") — never a raw enum value like
  `"estimated"` shown to the user directly.
- **Sign treatment**: the tooltip's value line carries `data-sign`
  (used for colour), matching `MetricValue`'s own convention — the same
  visual language, not a second one invented for charts.
- **Data-quality treatment**: the plain-language sentence above is the
  tooltip's data-quality mechanism — confirmed this is the *only* place
  in the chart system that spells out data quality in words rather than
  only visually (dash/opacity); a screen-reader-only user hovering
  wouldn't get this without the tooltip content being read, which is a
  real accessibility gap (see §14).
- **Unavailable values**: `formatValue` (or `formatMoney` by default)
  renders `"—"` for a `null` hovered value — confirmed via the
  `formatValue !== null` guard added to `TimeSeriesChart` in Phase 5.6.
- **Mobile behaviour**: tooltip positioning logic is identical at any
  viewport width (it's computed from the SVG's own coordinate space, not
  the page's) — confirmed no separate mobile tooltip behaviour exists or
  was invented.
- **Keyboard/accessibility**: **confirmed gap, not fixed** — hover is
  pointer-only (`onPointerMove`/`onPointerLeave`); there is no keyboard
  equivalent (e.g. arrow-key data-point stepping) in the current
  implementation. Documented as a known gap (§14), not silently patched
  in this step.
- **Not a calculation layer, confirmed**: every value the tooltip shows
  (date, value, quality) is read directly off the hovered data point
  object — no arithmetic happens inside `ChartTooltip`, `Crosshair`, or
  `useNearestPoint`.

## 12. Responsive chart behaviour (live-verified this step)

**Desktop (1280px)**, verified on Overview/Performance/Holdings, light
and dark: charts render at their full intended margin/height, period
tabs sit on one row with room to spare, no overflow.

**Mobile (375px)**, verified on Overview: chart height is unchanged
(charts don't shrink their vertical size at narrow widths — only their
width, via `ChartContainer`'s `ResizeObserver`), margins are unchanged
(the same `MARGIN` object at any width), the period-tab row scrolls
within its own strip rather than the page overflowing, the Metric Group
above the chart wraps to two rows. **No tick-count reduction happens at
narrow widths** (documented as a real characteristic in §5, not
invented as a responsive feature) — a narrow chart simply renders the
same number of requested ticks in less space, occasionally causing d3-
axis to drop a colliding tick on its own (D3's own built-in collision
avoidance, not application code).

**Table relationship**: `Table`'s own `overflow-x: auto` (confirmed
unchanged, Step 4) is the only chart-adjacent responsive mechanism that
differs from the chart itself — a paired table scrolls horizontally
independently of its chart.

**No new breakpoints were used or invented.** The only breakpoints in
the application remain `860px` (Overview/Performance metric-grid
collapse) and `900px` (AppShell nav collapse) — neither is a chart-
specific breakpoint; charts resize continuously via `ResizeObserver`,
not at discrete breakpoints.

## 13. Dark mode (live-verified this step)

Verified live at 1280px on Overview (chart + period tabs + flow-marker
legend) and Performance (return-index chart), in both
`prefers-color-scheme: light` and `dark` (browser-level emulation, not a
manual toggle — confirmed the app has no in-app theme switcher, matching
`docs/design-tokens.md`'s documented theme architecture):

- **Axes/grid**: `--chart-axis`/`--chart-grid` resolve to their dark-mode
  values (lighter grey-on-dark rather than grey-on-light) automatically
  — no separate dark-mode axis component exists.
- **Lines/fills**: `--color-accent` (the line colour) switches from
  `#1d4ed8` (light) to `#60a5fa` (dark) — same token, different resolved
  value, confirmed visually distinct and legible in both screenshots.
- **Tooltip**: `--color-surface`/`--color-text` invert correctly (a dark
  tooltip-on-light-background in light mode, a lighter tooltip-on-
  dark-background in dark mode).
- **Data-quality/sign states**: `--color-positive`/`--color-negative` and
  the quality-segment dash/opacity treatment are unaffected by theme —
  confirmed the dashed carried-forward segment remains visually distinct
  in both modes (opacity/dash-pattern are theme-independent CSS/SVG
  properties, not colour).
- **No separate dark-mode chart component was created** — every colour
  used by every chart component is a CSS custom property read at render
  time (`var(--chart-axis)` etc. via inline SVG `stroke`/`fill`
  attributes reading the same custom properties any other component
  reads), so the theme change requires zero chart-specific code.

## 14. Accessibility

Inspected against the actual implementation, not an idealised standard:

- **Chart titles**: `ChartContainer`'s optional `title` prop renders a
  `<figcaption>`; every chart-bearing section additionally sits under a
  `SectionHeader`'s `<h2>` one level up.
- **Supporting text — the chart's real accessible content**:
  `ChartContainer`'s `accessibleSummary` (required, not optional) is a
  visually-hidden `<p>` stating the chart's data range and observation
  count in plain language (e.g. "Portfolio value from 2025-06-30 to
  2026-06-30, 366 observations. Dashed segments are carried-forward
  estimates, not new valuations.") — confirmed this is the chart's real
  and only textual alternative to the visual rendering; the SVG itself
  is `role="img" aria-hidden="true"` (the visual is explicitly hidden
  from assistive tech, deferring entirely to the summary paragraph).
- **`AllocationChart` is the one exception**: it isn't wrapped in
  `ChartContainer` (§4's known sizing exception has this accessibility
  consequence too) and instead puts its own `role="img" aria-label`
  directly on the SVG — a real, different pattern from every other
  chart, documented rather than normalised.
- **Keyboard interaction**: **confirmed gap** — no chart in this system
  supports keyboard-driven data exploration (arrow-key stepping through
  points); hover/tooltip is pointer-only. The period-selector `Tabs`
  themselves ARE keyboard-operable (native `<button>`s,
  `aria-selected`/`aria-disabled`), but the chart body is not.
- **Colour independence**: confirmed — data quality is dash+opacity (not
  colour-only), financial sign is always paired with a `+`/`-` in the
  adjacent formatted text (not colour-only on the chart line itself,
  since the line is never sign-coloured to begin with — see §7).
- **Data table as an accessible alternative**: exists for the "Chart +
  Table" pattern (Holdings' `AllocationSection`) — the `Table` there is
  a fully accessible alternative representation of the same data the
  chart shows. **No other chart has an adjacent accessible table** —
  `TimeSeriesChart` (Overview/Performance) has no tabular alternative
  beyond its `accessibleSummary` text. Documented as a known gap, not
  invented as present.
- **Reduced motion**: no chart currently animates a transition
  (`--motion-chart` remains unused, per `docs/design-tokens.md`, restated
  here as still true) — there is nothing for `prefers-reduced-motion` to
  need to suppress in the chart system today.
- **Screen-reader considerations, summarised**: a screen-reader user
  gets the `accessibleSummary` paragraph (range + observation count +
  the carried-forward disclosure) but **not** the specific value at any
  individual point, and **not** the tooltip's plain-language quality
  sentence per point — both are genuine, documented gaps in the current
  implementation, not fixed in this step (per the explicit instruction
  not to silently fix unrelated accessibility issues here).

## 15–18. Figma chart library, components, contracts, compositions

The Figma work for the chart system was substantially completed in Step
3 (`04 Charts` page: 9 reference cards) and Step 5 (`05 Patterns`:
`Chart + Period Selector`, `Chart + Table`) and re-verified, not rebuilt,
in this step. No new Figma chart component or page was created — the
existing structure already satisfies this step's own instruction to
represent visual contracts, not D3 internals:

- Each `04 Charts` card shows: a representative visual (real Figma
  vector/rectangle nodes, clearly a design-reference illustration, never
  claimed as real portfolio data) + a documentation block covering
  purpose, data shape, states, and known exceptions (e.g.
  `AllocationChart`'s sizing, `BarChart`/`DrawdownChart`'s unused status)
  — confirmed still accurate against source in this step's re-audit, no
  changes needed.
- `Crosshair`, `ChartTooltip`, and `Axis` each have their own card,
  composed from the same bound colour variables the full charts use —
  not recreated as separate "Figma component" primitives with variants,
  since none of the three has a meaningful variant axis (a crosshair
  doesn't have "types," it has one visual shape used identically
  everywhere) — confirmed no variant explosion was warranted or created.
- **Individual chart contracts** (purpose/data shape/states/interaction/
  responsive/accessibility/Figma/Storybook/React/tokens) for
  `TimeSeriesChart`, `AllocationChart`, `AllocationHistoryChart`,
  `BarChart`, `DrawdownChart` are the inventory table in §2 plus §§4–14
  above — not restated a third time in a separate per-chart section,
  since this document's structure already answers every field the
  brief's contract template asks for, per chart, without duplicating
  prose.
- **Chart compositions** (`Chart + Period Selector`, `Chart + Table`) are
  fully specified in `docs/figma-pattern-library.md` patterns 4 and 5 —
  referenced, not repeated here.

### Figma ↔ Storybook ↔ React traceability (per chart)

| Chart | Figma | Storybook | React | Tokens | API/analytics data contract |
|---|---|---|---|---|---|
| TimeSeriesChart | `04 Charts` card | `TimeSeriesChart.stories.tsx` | `charts/TimeSeriesChart/TimeSeriesChart.tsx` | `--color-accent/positive/negative`, `--chart-grid/axis` | `PortfolioDailyPoint[]` (Overview), `PerformancePeriod`-bounded history (Performance), `HoldingRow[]` (Holdings security detail) |
| AllocationChart | `04 Charts` card | `AllocationChart.stories.tsx` | `charts/AllocationChart/AllocationChart.tsx` | `--chart-series-1..6`, `--color-unknown` | `AllocationResult` |
| AllocationHistoryChart | `04 Charts` card | `AllocationHistoryChart.stories.tsx` | `charts/AllocationHistoryChart/AllocationHistoryChart.tsx` | `--chart-series-1..6` | `AllocationHistoryPoint[]` |
| BarChart | `04 Charts` card | `BarChart.stories.tsx` | `charts/BarChart/BarChart.tsx` | `--color-positive/negative/accent` | `BarDatum[]` (no current API consumer) |
| DrawdownChart | `04 Charts` card | `DrawdownChart.stories.tsx` | `charts/DrawdownChart/DrawdownChart.tsx` | `--color-negative/negative-bg` | `DrawdownPoint[]`/`DrawdownEpisode[]` (no current API endpoint) |

## Known gaps (confirmed, not fixed)

1. No keyboard-driven chart data exploration (§11/§14).
2. No per-point screen-reader announcement — only the chart-level
   `accessibleSummary` (§14).
3. No custom X-axis date-tick format contract beyond D3's default (§5).
4. No `formatMoneyCompact()` usage on any chart axis (§5).
5. `AllocationChart` has no accessible data table alternative the way
   Holdings' paired Table does for the Chart + Table pattern (§14).
6. `BarChart`/`DrawdownChart` remain unconsumed by any production screen
   (already known from Steps 3–4, reconfirmed here).

## Open decisions

No existing open decision (Steps 1–5, `docs/design-system-decisions.md`
#1–#16) was resolved in this step. `AllocationChart`'s sizing exception
(open decision #11) was re-verified live and remains exactly as
documented — the implementation has not changed, so it was not "fixed."

**No genuinely new chart-specific open decision was discovered.** The
six items in "Known gaps" above are implementation gaps (missing
capability), not ambiguous design decisions requiring a future choice —
each has an obvious eventual direction (add keyboard support, add a data
table, etc.) rather than competing options to weigh, so none was added
to the open-decisions register as a new numbered entry.
