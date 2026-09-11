# Figma Pattern Library

Step 5 deliverable. Formalises the reusable arrangements of components
established in Steps 3–4 into named, classified composition patterns.
Two patterns required by this step's own brief (`Chart + Period
Selector`, `Chart + Table`) did not yet exist as Figma patterns — they
were built in this step, composed from real component instances, never
from a flattened screenshot. No other pattern was invented; every entry
below already appears in the shipping product.

**Pattern vs. component vs. screen**, the working distinction this
document holds to throughout:

```
COMPONENT  a reusable visual object            (MetricValue, Badge)
PATTERN    a reusable arrangement of components (Metric Group, Section)
SCREEN     a product-level composition of patterns (Performance)
```

## Pattern inventory and classification

| # | Pattern | Classification | Figma group |
|---|---|---|---|
| 1 | Page Header | CORE | 03 Section |
| 2 | Section | CORE | 03 Section |
| 3 | Metric Group | CORE | 04 Metrics |
| 4 | Chart + Period Selector | CORE | 05 Charts |
| 5 | Chart + Table | REUSABLE | 06 Tables |
| 6 | Data Table | CORE | 06 Tables |
| 7 | Loading / Empty / Unavailable | CORE | 07 Data States |
| 8 | Coverage Footer | REUSABLE | 10 Historical / Portfolio States |
| 9 | Methodology Disclosure | DOMAIN-SPECIFIC | 08 Methodology |
| 10 | Reconciliation Disclosure | DOMAIN-SPECIFIC | 09 Reconciliation |
| 11 | Fully-Divested / Historical-Still-Available | DOMAIN-SPECIFIC | 10 Historical / Portfolio States |

**Classification rationale**: CORE patterns appear on every screen and
compose only generic primitives (Card, SectionHeader, MetricValue, Table,
Tabs) — a future screen cannot avoid using them. REUSABLE patterns are
genuinely reusable across screens but not universal (Coverage Footer
appears on all 3 current screens but is conceptually optional; Chart +
Table appears once today but composes only generic primitives, so it's
reusable in principle even with one current instance). DOMAIN-SPECIFIC
patterns encode portfolio-analytics-specific meaning (methodology,
reconciliation, the fully-divested state) that wouldn't transfer to an
unrelated product. No pattern was classified PAGE-SPECIFIC or
INFRASTRUCTURE — nothing audited turned out to be a one-off page layout
or a non-visual infrastructure concern (`QueryBoundary`, which *is*
infrastructure, is not a pattern itself; it's the mechanism patterns 7
and others render through, documented under Data-quality behaviour below
rather than listed as its own pattern). No FUTURE CANDIDATE patterns were
identified — every arrangement examined already exists in the product at
least once.

**Figma organisation used** (per this step's own numbered list; groups
1, 2, and 11 have no pattern assigned and are intentionally empty —
see "Groups with nothing in them" at the end):

```
05 Patterns
  03 Section              → Page Header, Section
  04 Metrics              → Metric Group
  05 Charts               → Chart + Period Selector
  06 Tables               → Data Table, Chart + Table
  07 Data States          → Loading / Empty / Unavailable
  08 Methodology          → Methodology Disclosure
  09 Reconciliation       → Reconciliation Disclosure
  10 Historical / Portfolio States → Coverage Footer, Fully-Divested/Historical-Still-Available
```

---

## 1. Page Header

- **Purpose**: the `<h1>` + one-sentence description (+ optional back-link)
  every feature page opens with.
- **Classification**: CORE.
- **React**: not a shared component — plain JSX repeated at the top of
  `OverviewPage.tsx`, `PerformancePage.tsx`, `HoldingsPage.tsx`, and
  `SecurityDetail.tsx` (which adds the back-link). **Storybook**: none
  (no component to story — see Known exceptions).
- **Figma**: `05 Patterns` → `03 Section > Page Header`, showing
  Performance's actual header text.
- **Required components**: none (plain text) — `<h1>` + description.
- **Optional elements**: a "← Back to X" link above the title (used only
  by `SecurityDetail`).
- **Variants/States**: none.
- **Tokens**: `--text-h1` (title, plain text, not a component), `--text-
  body` (description), `--color-text-muted` (description colour),
  `--space-2` (title/description gap).
- **Responsive**: no page-level breakpoint changes this pattern's own
  layout; it reflows naturally as block text at any width.
- **Accessibility**: this is the one place a screen's `<h1>` is
  established — every `SectionHeader` `<h2>` on the page nests under it.
- **Data-quality behaviour**: none — static copy, not data-driven.
- **Known exceptions**: not a shared React component, so there is no
  single Storybook story to point to; each page repeats the JSX by hand.
  This was true before Step 5 and is not changed by it (React changes
  are out of scope for this step).
- **Open decisions**: none new.

## 2. Section

- **Purpose**: `Card` + `SectionHeader` + content, the recurring
  container every named block on every screen uses.
- **Classification**: CORE.
- **React**: composition of `design-system/Card/Card.tsx` +
  `design-system/SectionHeader/SectionHeader.tsx`, wrapped in one or more
  `QueryBoundary`s at each call site — not itself a component.
  **Storybook**: `Card.stories.tsx` + `SectionHeader.stories.tsx`
  individually; no combined story.
- **Figma**: `05 Patterns` → `03 Section > Section`, one `Card`
  (`Elevation=raised`) instance with representative body text.
- **Required components**: `Card`, `SectionHeader`.
- **Optional content**: metric group, chart, table, notice, or
  disclosure — the pattern is deliberately content-agnostic; **no
  separate "Chart Section"/"Table Section"/"Metric Section" component was
  created**, per this step's explicit instruction to prefer composition.
- **Variants/States**: `Card`'s own `flat`/`raised` variants apply; no
  additional pattern-level variants.
- **Tokens**: inherited from `Card` and `SectionHeader` (`--color-surface/
  border`, `--radius-medium`, `--space-3/4/5`, `--text-h3`/`--text-meta`).
- **Responsive**: none of its own; content inside determines reflow.
- **Accessibility**: `SectionHeader` establishes the `<h2>`; content
  inside establishes its own further hierarchy (a table's caption, a
  chart's accessible summary).
- **Data-quality behaviour**: none directly — a `QueryBoundary` wrapping
  the content decides loading/error/empty, not the Section pattern
  itself (see pattern 7).
- **Known exceptions**: none.
- **Open decisions**: none new.

## 3. Metric Group

- **Purpose**: a row of `MetricValue`s presenting related figures
  together (a portfolio's value/gain/return, a performance summary's four
  stats, a holdings snapshot).
- **Classification**: CORE.
- **React**: the identical 6-line CSS block
  (`.summaryRow { display: flex; flex-wrap: wrap; gap: var(--space-6); }`
  + the `min-width:0`/`flex:1 1 140px` fix) copy-pasted in
  `OverviewPage.module.css`, `PerformancePage.module.css`, and
  `HoldingsPage.module.css` — **not** a shared component (open decision
  #14, unchanged in this step). **Storybook**:
  `MetricValue.stories.tsx` covers the individual metric; no combined
  "Metric Group" story exists.
- **Figma**: `05 Patterns` → `04 Metrics > Metric Group`, 3 `MetricValue`
  instances (default/negative/unavailable) in a row.
- **Required components**: 2 or more `MetricValue` instances.
- **Optional elements**: supporting metadata below a metric (the `meta`
  slot on `MetricValue` itself — e.g. a `DataQualityBadge`).
- **Variants/States**: no fixed count — the real implementation shows
  anywhere from 3 (Overview header, Holdings snapshot) to 4 (Performance
  summary) metrics; **not modelled as separate "2-metric"/"3-metric"/
  "4-metric" Figma variants**, per this step's explicit preference for
  flexible Auto Layout composition over variant proliferation. The Figma
  frame uses `flex-wrap`-equivalent Auto Layout (`layoutMode: HORIZONTAL`
  with wrap), matching the CSS exactly.
- **Tokens**: `--space-6` (gap), `--text-meta`/`--text-figure-lg`
  (inherited from `MetricValue`), `--color-positive/negative` (sign).
- **Responsive**: wraps to multiple rows on narrow viewports (the actual
  CSS `flex-wrap: wrap` behaviour) — each metric's own `min-width: 0`
  lets a long unavailable-reason sentence wrap within its column instead
  of forcing the whole row wider (the Phase 5.6 mobile-overflow fix).
- **Accessibility**: each `MetricValue`'s label/value pair is plain text;
  no additional semantics at the group level.
- **Data-quality behaviour — the important rule this pattern must
  preserve**: an unavailable metric within the group renders via
  `MetricValue`'s `unavailableReason` path (italic message, **no** sign
  colour), never a `$0`/`0%` placeholder sitting visually identical to a
  real zero. Confirmed still true in the Figma `unavailable` variant
  instance available for use in this pattern (see
  `docs/figma-component-library.md`'s MetricValue entry).
- **Known exceptions**: the 3-file CSS duplication is a real
  implementation fact, documented, not fixed — see open decision #14
  (`docs/design-system-decisions.md`), explicitly not resolved in this
  step.
- **Open decisions**: none new (references existing #14).

## 4. Chart + Period Selector

- **Purpose**: the recurring "pick a window, see the historical chart for
  it" composition used by Overview's value chart and Performance's
  return-history chart.
- **Classification**: CORE.
- **React**: `OverviewChart.tsx` and `PerformanceChart.tsx` — both built
  from `Tabs` (fed by `usePeriodTabs`) + `ChartContainer` +
  `TimeSeriesChart`, sharing the `useSelectedPeriod` hook for
  URL-addressable, backend-resolved period boundaries. **Storybook**:
  `Tabs.stories.tsx`'s `PeriodSelector` story + `TimeSeriesChart.stories.tsx`
  individually; no combined pattern story (page-specific composition,
  correctly not story'd on its own per Step 1's inventory).
- **Figma**: `05 Patterns` → `05 Charts > Chart + Period Selector` —
  **new in this step**. A period-tab row (with one disabled variant
  shown, mirroring a real backend-reported unavailable period — never a
  frontend-invented rule) + a representative `TimeSeriesChart`-style
  line + a coverage line.
- **Required components**: `Tabs`, a chart (`TimeSeriesChart` in both
  current usages).
- **Optional elements**: a coverage line beneath the chart (present in
  both real usages, not strictly required by the pattern's own
  definition).
- **Variants/States**: period availability is entirely capability-driven
  — a disabled tab's reason comes from the backend's own
  `PerformancePeriod.status`/`note` (Overview/Performance) never a
  frontend rule like "hide periods under a year." **No period was
  invented that the API doesn't actually support** — the Figma tab row
  shows exactly the 8 labels (`1M`/`3M`/`6M`/`YTD`/`1Y`/`3Y`/`5Y`/`MAX`)
  the real `usePeriodTabs` hook is called with.
- **Tokens**: `Tabs`' own tokens + `TimeSeriesChart`'s (see
  `docs/figma-component-library.md`).
- **Responsive**: the tab row scrolls horizontally
  (`overflow-x: auto`) rather than overflowing the page at narrow widths
  (the Phase 5.6 fix) — the chart itself resizes via `ChartContainer`'s
  `ResizeObserver`.
- **Accessibility**: `role="tablist"`/`aria-selected`/`aria-disabled` on
  the period tabs; the chart's `accessibleSummary` (via `ChartContainer`)
  carries the chart's meaning independent of visual rendering.
- **Data-quality behaviour**: loading → `ChartSkeleton`; empty → "No
  portfolio history available yet." (Overview) / "No return history
  available for this period yet." (Performance); the chart's own line
  segments distinguish `actual`/`calculated`/`estimated` quality (dashed
  for carried-forward), and a null value breaks the line rather than
  plotting as zero.
- **Known exceptions**: on Performance, the selected period *also* drives
  the summary metrics above the chart (shared state via
  `useSelectedPeriod`) — this cross-pattern data relationship (Chart +
  Period Selector feeding Metric Group) is a real, important
  implementation fact not separately diagrammed as its own pattern, since
  it's a data-flow relationship between two existing patterns, not a
  third visual arrangement.
- **Open decisions**: none new.

## 5. Chart + Table

- **Purpose**: a chart and a table presenting the *same* dataset, the
  chart showing proportion/shape visually, the table showing exact
  values — never two independently-calculated views of the same figures.
- **Classification**: REUSABLE.
- **React**: `AllocationSection.tsx` (Holdings screen) — `AllocationChart`
  directly followed by a `Table`, both reading the same
  `AllocationResult` API response (`weights`/`allocation_pct`). No
  recalculation happens between the chart and the table; the table's
  `sortValue`/`render` functions read the identical fields the chart's
  segments were built from. **Storybook**: `AllocationChart.stories.tsx`
  + `Table.stories.tsx` individually.
- **Figma**: `05 Patterns` → `06 Tables > Chart + Table` — **new in this
  step**. A representative proportional bar + a `Table` instance beneath
  it.
- **Required components**: a chart, a `Table`, both bound to one shared
  data context — this is a defining requirement of the pattern, not an
  optional pairing (a table alone is pattern 6, "Data Table"; a chart
  alone belongs to `04 Charts`).
- **Optional elements**: none — both parts are required by the pattern's
  own definition.
- **Variants/States**: none — the pattern's shape doesn't vary; only the
  chart type paired with the table might (`AllocationChart` today).
- **Tokens**: inherited from the chart and `Table` components.
- **Responsive**: `Table`'s own `overflow-x: auto`; the chart resizes per
  its own sizing model (see `AllocationChart`'s fixed-width-vs-
  `ChartContainer` note in `docs/figma-component-library.md` — restated,
  not resolved, here too).
- **Accessibility**: the chart's `role="img" aria-label`
  (`AllocationChart` puts its own accessible label directly on the SVG,
  unlike chart family members wrapped in `ChartContainer`) + the table's
  native semantics.
- **Data-quality behaviour**: when the underlying `AllocationResult` is
  `status: "unavailable"`, **neither** the chart nor the table renders at
  all — the whole pattern is replaced by `UnavailableMetric` with the
  backend's own reason (verified in `HoldingsPage.tsx`'s
  `AllocationSection` branch). This is the same "the pattern doesn't
  half-render" behaviour as pattern 7 more generally.
- **Known exceptions**: only one real current usage (Holdings'
  allocation section) — classified REUSABLE rather than CORE because it
  isn't yet proven across multiple screens, even though nothing about
  its composition ties it to Holdings specifically.
- **Open decisions**: none new (references existing #11, AllocationChart
  sizing).

## 6. Data Table

- **Purpose**: the one data-table shape — every holdings/allocation/
  calendar listing in the app.
- **Classification**: CORE.
- **React**: `design-system/Table/Table.tsx`, used directly (not wrapped
  in a further pattern component) by `HoldingsTable.tsx`,
  `CalendarPerformanceTable.tsx`, `AllocationSection.tsx`, and Overview's
  inline top-holdings table. **Storybook**: `Table.stories.tsx`.
- **Figma**: `05 Patterns` → `06 Tables > Data Table`, a representative
  3-row snippet (VAS/VGS/Cash).
- **Required components**: `Table`.
- **Numeric alignment**: right-aligned, `IBM Plex Mono`, confirmed
  matching `.numeric` CSS exactly (re-verified in Step 4, restated here).
- **Sorting**: `aria-sort` on sortable headers, defaulting to a
  financially-sensible sort (value descending) — **not redrawn as a
  distinct Figma sort-arrow state** in this step either (same gap noted
  in `docs/figma-component-library.md`'s Table entry); documented in text
  only.
- **Selected/hover states**: `.row:hover td { background: var(--color-
  border) }` exists in CSS; not modelled as a separate Figma state (a
  static file has no meaningful hover to show beyond a colour swap
  already implied by the token).
- **Unavailable/zero values**: a cell renders "Unavailable" (text) when
  the underlying field is `null`, and a real `$0.00`/`0.0%` when the
  value is genuinely zero — the two are never conflated (verified in
  `HoldingsTable.tsx`'s render functions: `r.allocation_pct === null ?
  "Unavailable" : formatPercentPlain(...)`).
- **Empty state**: not the table's own concern — the *pattern* wrapping
  it (a `QueryBoundary`'s `isEmpty`) substitutes `UnavailableMetric`
  entirely rather than rendering an empty `<table>` shell (see pattern
  7).
- **Responsive**: `overflow-x: auto` on the table's own wrapper — **not**
  redesigned into a card-based mobile layout, since that is not the real
  implementation's strategy at any screen size (confirmed, re-stated per
  this step's explicit instruction not to invent mobile behaviour).
- **Accessibility**: native `<table>`/`<thead>`/`<tbody>`, visually-hidden
  `<caption>`, `aria-sort` (never `role="button"` — the Phase 5.1–5.4
  regression this component's design exists partly to prevent
  repeating).
- **Known exceptions**: sort-arrow visual and hover state not modelled in
  Figma (documented in text — see `docs/figma-component-library.md`).
- **Open decisions**: none new.

## 7. Loading / Empty / Unavailable

- **Purpose**: the semantic backbone of the whole application's trust
  model — distinguishing five states that must never visually collapse
  into one another.
- **Classification**: CORE.
- **The five states, precisely** (this step's own required distinction,
  confirmed against the real implementation, not just asserted):

  | State | Meaning | Real trigger | Rendered as |
  |---|---|---|---|
  | LOADING | data has not arrived yet | `query.isPending` | `ChartSkeleton`/`Skeleton` — shape only, never a fake figure |
  | EMPTY | a valid response contains zero relevant records | `isEmpty(data)` true, e.g. `holdings.length === 0` | `UnavailableMetric` with an empty-specific `emptyMessage` (e.g. "No securities currently held.") |
  | UNAVAILABLE | the metric/capability cannot currently be calculated or provided at all | `query.isError`, or the API's own `status: "unavailable"` / `Capability.available === false` | `UnavailableMetric` with the backend's own `reason`/`note` string |
  | LIMITED | data exists but confidence/coverage is constrained | `data_quality: "limited"` on a `Metric` | `DataQualityBadge`/`LimitedDataNotice` (the latter unconsumed in production today — see `docs/figma-component-library.md`) |
  | ZERO | the actual numeric value is a real zero | a parsed value `=== 0` | `MetricValue`'s ordinary neutral-sign rendering — a real number like any other, **not** a special "zero state" |

  **EMPTY and UNAVAILABLE both render through the same `UnavailableMetric`
  component today** — confirmed in `QueryBoundary.tsx` (both branches
  call `<UnavailableMetric title=... reason=... />`, differing only in
  which title/reason string each carries). This is a real, documented
  implementation fact — the two states are distinguished by *content*
  (the specific title/reason), not by a visually distinct component or
  colour. This is not a bug to fix in this step; it's stated here exactly
  because Part 9 asks the distinction to be explicit rather than
  papered over.
- **React**: `common/QueryBoundary/QueryBoundary.tsx` is the single
  mechanism that decides which of Loading/Empty/Unavailable fires, for
  every data-bearing section in the app. **Storybook**: no story (a
  data-fetching wrapper, not a visual component in isolation — per Step 1's
  inventory, unchanged).
- **Figma**: `05 Patterns` → `07 Data States > Loading / Empty /
  Unavailable`, three side-by-side examples (a skeleton rectangle, an
  `UnavailableMetric` instance labelled "Empty," a second
  `UnavailableMetric` instance labelled "Unavailable" — both instances of
  the same component, differing only in their title/reason text,
  faithfully matching the real implementation described above).
- **Required components**: `Skeleton`/`ChartSkeleton` (loading),
  `UnavailableMetric` (empty and unavailable).
- **Tokens**: `--color-border`/`--color-border-strong` (skeleton shimmer
  and dashed border).
- **Data-quality behaviour is this pattern's entire purpose** — see the
  table above.
- **Accessibility**: `Skeleton` is `aria-hidden` (shape only, nothing to
  announce); `UnavailableMetric`'s badge + text is always readable
  content, never colour-only.
- **Known exceptions**: LIMITED is shown via `DataQualityBadge` inline in
  the two production screens that currently exercise it (Performance's
  summary), not via the dedicated (but production-unused)
  `LimitedDataNotice` component — both paths are legitimate per the
  component's own documented status, not a new finding.
- **Open decisions**: none new.

## 8. Coverage Footer

- **Purpose**: the historical-coverage metadata line at the bottom of
  every screen.
- **Classification**: REUSABLE.
- **React**: a `<footer>` composing `SectionHeader` + `DataCoverageBadge`,
  repeated (not shared as one component) at the bottom of
  `OverviewPage.tsx`, `PerformancePage.tsx`, `HoldingsPage.tsx`.
  **Storybook**: `DataCoverageBadge.stories.tsx` for the badge itself; no
  combined footer story.
- **Figma**: `05 Patterns` → `10 Historical / Portfolio States > Coverage
  Footer`.
- **Required components**: `SectionHeader` (or equivalent heading text),
  `DataCoverageBadge`.
- **Typography/placement**: `--text-meta` heading, `--text-meta`
  body-equivalent for the coverage line itself (`DataCoverageBadge` uses
  `--text-meta`/`--color-text-muted` directly, no `Badge` wrapper).
- **Data-quality meaning — the rule this pattern exists to enforce**:
  coverage ("30 Sept 2020 – 30 June 2026 · 24 valuation observations ·
  quarterly source data") is metadata *about the dataset*, never a
  performance figure. Confirmed: `DataCoverageBadge` applies **no**
  sign colour, no `Badge` tone, nothing that could read as "good" or
  "bad" — it is plain, neutral text, deliberately never styled as
  positive/negative financial information, exactly per this step's
  instruction.
- **Responsive**: no page-level breakpoint changes this pattern; it's a
  single line of text that wraps naturally.
- **Accessibility**: plain text, always present (never hidden behind a
  disclosure) — the one place data-completeness is stated up front on
  every screen.
- **Known exceptions**: not a shared component, same as Page Header.
- **Open decisions**: none new.

## 9. Methodology Disclosure

- **Purpose**: let a user understand what a number represents (TWRR
  methodology, the TWRR/XIRR distinction, data limitations) without the
  explanation overwhelming the primary metric.
- **Classification**: DOMAIN-SPECIFIC.
- **React**: `data-quality/MethodologyPopover/MethodologyPopover.tsx`,
  used by `MethodologyPanel.tsx` (Performance screen) beneath the TWRR
  and XIRR `MetricValue`s. **Storybook**: `MethodologyPopover.stories.tsx`.
- **Figma**: `05 Patterns` → `08 Methodology > Methodology Disclosure`,
  showing the popover's open state.
- **Required components**: a primary metric (`MetricValue`, shown
  separately in the Metric Group / Performance summary), a
  `MethodologyPopover` beneath it.
- **The disclosure remains secondary — confirmed, not just asserted**:
  the popover's trigger is a plain, small (`--text-meta`) text line, and
  the panel only appears on demand (click, not always-visible) — nothing
  about this pattern makes the explanation compete visually with the
  metric it explains. **Not turned into a large explanatory panel** on
  every metric, per this step's explicit instruction — only TWRR/XIRR
  carry one today, matching the real `MethodologyPanel` implementation.
- **Content — restated from the existing methodology documentation, not
  rewritten**: "Sub-period linked" (TWRR) / "Cash-flow adjusted" (XIRR),
  with the exact same explanatory sentences `MethodologyPanel.tsx`
  renders (`twrrMethodology.twrr_methodology_note`/
  `cash_flow_adjustment_note` from the API's own methodology payload —
  **not a Figma-invented paraphrase**).
- **Tokens**: `--color-surface-raised`, `--color-border`,
  `--shadow-medium`, `--text-meta`/`--text-body`, `--space-2/3`,
  `--radius-medium`.
- **Responsive**: the panel is `position: absolute`, sized independent of
  viewport — no distinct mobile behaviour exists to represent.
- **Accessibility**: `aria-expanded`, `aria-controls`, `role="note"` on
  the panel, closes on Escape — keyboard-operable, not hover-only.
- **Data-quality behaviour**: the methodology explanation is itself how
  the product discloses a *limitation* (this dataset cannot compute true
  TWRR, only a documented sub-period-linked approximation) — the
  disclosure pattern **is** the data-quality mechanism for this
  particular nuance, rather than a `DataQualityBadge`.
- **Known exceptions**: none.
- **Open decisions**: none new.

## 10. Reconciliation Disclosure

- **Purpose**: let a user trust that a period's return decomposition adds
  up, with the underlying figures available on demand.
- **Classification**: DOMAIN-SPECIFIC.
- **React**: `ReturnDecomposition.tsx` (Performance screen) — a `Badge` +
  a clickable summary line, expanding (local `useState`, not
  `MethodologyPopover`) into a `<dl>` of
  `attributed_change`/`actual_change`/`residual`/`tolerance` —
  Phase 4's own exact vocabulary, never re-terminologised.
  **Storybook**: no dedicated story (page-specific composition, not a
  shared component).
- **Figma**: `05 Patterns` → `09 Reconciliation > Reconciliation
  Disclosure`.
- **The known semantic issue, restated exactly, not fixed**: the badge
  showing `PASS` is a generic `Badge` `Tone=positive` instance, whose
  Figma-baked label reads "Actual" rather than "Explained" (the real
  copy `ReturnDecomposition.tsx` renders). This is the same finding
  Step 3 made and Step 4 confirmed and left open (open decisions #10,
  #15, #16 in `docs/design-system-decisions.md`). **Not fixed in this
  step either** — per this step's own explicit instruction: "Do NOT fix
  the semantic issue during Step 5. Document it as an existing open
  decision." No reconciliation-specific colour or terminology was
  invented to work around it.
- **Required components**: a status `Badge`, the expandable detail row.
- **Tokens**: `Badge`'s tone colours (currently the Financial Sign
  family, per the known issue above), `--color-background` (detail
  panel), `--text-figure`/`--text-meta`.
- **Responsive**: the detail row (`attributed_change`/`actual_change`/
  `residual`/`tolerance`, 4 columns) has no distinct mobile
  reflow implemented — not invented here.
- **Accessibility**: the summary line is a clickable text trigger;
  `aria-expanded` semantics are the real component's, not separately
  re-verified in this step (out of scope — Part 16 permits documentation
  only, no production accessibility change).
- **Data-quality behaviour**: `PASS`/`FAIL`/`LIMITED` is a distinct
  fourth semantic axis from data quality, financial sign, and capability
  (per `docs/design-semantics.md` §4) — correctly still not merged with
  any of the other three in this step.
- **Known exceptions**: the badge label mismatch (above).
- **Open decisions**: none new (references existing #10/#15/#16).

## 11. Fully-Divested / Historical-Still-Available

- **Purpose**: formalise the product state where current holdings are
  empty but historical data remains fully available — this real
  portfolio's actual current condition, not a hypothetical edge case.
- **Classification**: DOMAIN-SPECIFIC.
- **React**: `HoldingsPage.tsx` — the "Holdings" section shows
  `UnavailableMetric` ("No current holdings — this portfolio is fully
  divested to cash. Historical holdings remain available via allocation
  history and security detail below.") while the "Allocation over time"
  section on the *same screen* continues to render 7 years of real data,
  and `/holdings/:code` continues to show a divested security's full
  history. **Storybook**: no dedicated story (a cross-section product
  state, not a single component).
- **Figma**: `05 Patterns` → `10 Historical / Portfolio States > Fully
  Divested / Historical-Still-Available`, showing an `UnavailableMetric`
  instance (current state) directly above a still-populated allocation
  band (historical state) with an explicit connecting label.
- **The three states this pattern must keep distinct — the core of Part
  13**:
  1. **"No current holdings"** — a real, valid, present-tense fact about
     today's portfolio. Rendered via `UnavailableMetric` with that exact
     wording.
  2. **"No historical data"** — a different claim entirely (there is no
     data at all, ever) — **never implied** by state 1; the same screen
     that shows state 1 simultaneously shows populated historical charts,
     proving the two are not conflated in the real implementation.
  3. **"Data unavailable"** — a capability/computation failure (e.g.
     `Allocation: Unavailable`), which co-occurs with state 1 on this
     real portfolio (no current holdings → nothing to allocate → the
     *current* allocation endpoint reports unavailable) but is a
     *different* fact from state 1 itself — one is about holdings, the
     other about a derived calculation.
- **Required components**: `UnavailableMetric` (current-state message),
  a historical chart/table still rendering real data alongside it.
- **Tokens**: inherited from `UnavailableMetric` and the historical chart
  shown.
- **Data-quality behaviour**: this pattern is the sharpest real-world
  test of the "unavailable ≠ zero" and "empty ≠ no-historical-data"
  rules this entire document insists on — verified against the live
  application (not a hypothetical mock) during Phase 5.7's own browser
  verification, restated here as a formal pattern rather than an
  incidental screen behaviour.
- **Known exceptions**: none — this is the one pattern where the "real
  example" *is* the current production state, not a constructed
  illustration.
- **Open decisions**: none new.

---

## Reference screens: pattern composition breakdown

Per this step's own request — the explicit hierarchy from screen down to
tokens, for each of the 3 reference screens (unaltered, used only for
validation):

```
Overview
  ↓
Page Header, Metric Group, Chart + Period Selector, Section (×4:
  Contributions, Income, Allocation, Top Holdings), Coverage Footer
  ↓
MetricValue, Tabs, TimeSeriesChart, Card, SectionHeader, AllocationChart,
  Table, UnavailableMetric, DataCoverageBadge
  ↓
Figma Variables (Color, Spacing, Radius) + Text Styles

Performance
  ↓
Page Header, Metric Group, Chart + Period Selector, Section (Return
  Decomposition, Methodology), Reconciliation Disclosure, Methodology
  Disclosure, Data Table (Calendar), Coverage Footer
  ↓
MetricValue, Tabs, TimeSeriesChart, Badge, MethodologyPopover, Table,
  DataQualityBadge, Card, SectionHeader, DataCoverageBadge
  ↓
Figma Variables + Text Styles

Holdings
  ↓
Page Header, Metric Group (snapshot), Chart + Table (allocation), Data
  Table (holdings), Fully-Divested / Historical-Still-Available,
  Coverage Footer
  ↓
MetricValue, AllocationChart, Table, UnavailableMetric,
  AllocationHistoryChart, Card, SectionHeader, DataCoverageBadge
  ↓
Figma Variables + Text Styles
```

No discrepancy was found between this breakdown and the live Figma
`06 Screens` compositions built in Step 3 — each screen's Figma reference
already uses exactly these patterns/components, re-confirmed via
`get_metadata` during this step's audit.

## Groups with nothing in them

Per this step's own numbered `FIGMA ORGANISATION` list, three groups
were intentionally left without a pattern:

- **01 Navigation / Page Structure** — explicitly excluded per this
  step's Part 3 instruction ("Do not turn AppShell navigation into part
  of the Page Header pattern"); `AppShell` remains Infrastructure, not a
  pattern (see `docs/figma-component-map.md`).
- **02 Page Header** — folded into the `03 Section` group instead of its
  own numbered group in the actual Figma canvas, since Page Header and
  Section are adjacent, both-required-on-every-screen patterns that sit
  side by side spatially in the existing Step 3 layout; moving Page
  Header into a physically separate group would have meant relocating an
  existing, working frame for organisational purity alone — not done,
  per this step's own instruction to avoid unnecessary Figma-file churn.
  The classification table above still lists Page Header as its own
  pattern with its own row; only the Figma group numbering folds it in
  with Section.
- **11 Responsive Examples** — no dedicated Figma section was built for
  this. Responsive behaviour is documented in text, per-pattern, above
  (see each pattern's own "Responsive" field) rather than built as
  separate mobile-width mockups, since building genuine new
  responsive-state frames for 11 patterns was judged to be net-new visual
  construction beyond this step's audit-and-formalise scope, and no
  pattern's mobile behaviour was left undocumented as a result.
