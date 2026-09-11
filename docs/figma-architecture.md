# Figma Architecture

Step 3 deliverable. A real Figma file was created and populated — **Portfolio
Design System** at
`https://www.figma.com/design/hiY0QY46GswjnIsV3iqwoU/Portfolio-Design-System`
— via the Figma Plugin API (`use_figma`), not faked. This document is the
map of what's in it, why, and how it relates to `docs/design-system-
inventory.md`, `docs/design-tokens.md`, `docs/design-semantics.md`,
`docs/design-system-decisions.md`, and `docs/figma-component-map.md` (all
Step 1/2 inputs, unchanged by this step except one small addition — see
"Component mapping updates" at the end).

Nothing here redesigns the application. Every colour, spacing value,
typography spec, and component state shown is the one already implemented
in `web/src`, cross-checked against source during Steps 1–2.

## Page structure

| Page | Contents |
|---|---|
| `00 Cover` | Title, one-paragraph description, version/date, and the Storybook/React relationship statement (Figma is a reference, not a second source of truth — restated per this step's own instruction) |
| `01 Foundations` | Typography (9 real text styles), Colour (Light/Dark columns bound to real variables, 6 semantic groups incl. Financial Sign restated separately from Action/Status), Chart Palette, Spacing, Radius, Shadow, Motion (doc-only), Responsive (doc-only, flagged open), Icons (doc-only, flagged open) |
| `02 Tokens` | A developer-facing intro explaining this page's purpose, and the "Data quality ≠ financial sign ≠ capability" diagram with the three axes side by side |
| `03 Components` | 8 primitives + 5 domain components, each a real Figma `COMPONENT`/`COMPONENT_SET` with a `description` carrying purpose/props/Storybook link |
| `04 Charts` | 9 chart-family reference cards (ChartContainer, ChartTooltip, Crosshair, Axis, TimeSeriesChart, AllocationChart, AllocationHistoryChart, BarChart, DrawdownChart) |
| `05 Patterns` | 9 composition patterns, most built from real instances of the Components-page components (Page Header, Metric Group, Section, Data Table, Loading/Empty/Unavailable, Coverage Footer, Fully-Divested/Historical-Still-Available, Methodology Disclosure, Reconciliation Disclosure) |
| `06 Screens` | 3 reference compositions: Overview, Performance, Holdings |
| `99 Archive` | An index (not a duplicate) of the 4 components that are built and story'd but not yet consumed by any production screen: `Tooltip`, `LimitedDataNotice`, `BarChart`, `DrawdownChart` |

## Foundations → Figma variables

Real Figma variable collections were created, bound to real shapes, and
code-linked back to the exact CSS custom property:

- **Color** collection — 30 variables, Light/Dark modes, exact hex values
  from `tokens.css` for both modes. Grouped `Surface/*`, `Border/*`,
  `Text/*`, `Action-Status/*`, `Data Quality/*`, `Chart/*`. Each has
  `codeSyntax.WEB` set to `var(--color-*)`.
- **Spacing** collection — 8 variables (`Space/1`…`Space/8`), single mode
  (not theme-dependent), values 4/8/12/16/24/32/48/64px, scoped to
  `GAP`/`WIDTH_HEIGHT`.
- **Radius** collection — 4 variables (`Radius/None/Small/Medium/Large`),
  scoped to `CORNER_RADIUS`.
- **9 text styles** (`Type/Display` … `Type/Figure Large`) — real fonts
  resolved: Fraunces (Display), Inter (H1–Body/Meta), IBM Plex Mono
  (Figure/Figure Large) — all three families were actually available in
  this Figma environment, so no Inter-fallback substitution was needed.
- **2 effect styles** (`Shadow/Low`, `Shadow/Medium`) — exact
  offset/blur/colour/alpha from `--shadow-low`/`--shadow-medium`.

**What was deliberately not turned into bindable variables**: Motion
(`--motion-*`) and Responsive breakpoints have no direct Figma property to
bind in a static file (no prototype-transition work was in scope), so
these are documented as text specimens on `01 Foundations` instead of
variables — consistent with "do not add a dependency merely because
automation sounds attractive" and this step's explicit "do not introduce a
new breakpoint scale."

## Token ↔ code mapping (the actual mechanism)

Every colour/spacing/radius variable's `codeSyntax` field was set via
`variable.setVariableCodeSyntax("WEB", "var(--token-name)")` at creation
time — this is a real, inspectable Figma API feature (not a made-up
convention): selecting any variable in the Figma variables panel shows its
linked CSS name directly. `02 Tokens`'s intro explains this mechanism in
plain language for a developer who's never opened the plugin console.

No second, competing token system was created — the Figma variables *are*
the CSS tokens, restated in Figma's own data model, not a parallel
vocabulary that could drift from `tokens.css` unnoticed.

## Component mapping (Figma ↔ Storybook ↔ React)

All 13 (8 primitive + 5 domain) components below are real Figma
`COMPONENT`/`COMPONENT_SET` nodes on `03 Components`, each carrying a
`.description` with its React path, Storybook file, and prop summary —
inspectable directly in Figma without this document. Table restates it for
convenience:

| Figma component | Variants built | React | Storybook |
|---|---|---|---|
| Badge | 10 (5 status + 5 quality tones) | `design-system/Badge/Badge.tsx` | `Badge.stories.tsx` |
| Button | 3 (primary/secondary/ghost) | `design-system/Button/Button.tsx` | `Button.stories.tsx` |
| Card | 2 (flat/raised) | `design-system/Card/Card.tsx` | `Card.stories.tsx` |
| Tabs | 3 states (default/selected/disabled), one tab item | `design-system/Tabs/Tabs.tsx` | `Tabs.stories.tsx` |
| MetricValue | 4 states (default/negative/neutral/unavailable) | `design-system/MetricValue/MetricValue.tsx` | `MetricValue.stories.tsx` |
| SectionHeader | 1 (no variant prop exists in code — not invented) | `design-system/SectionHeader/SectionHeader.tsx` | `SectionHeader.stories.tsx` |
| Table | 1 representative 3-row/5-column snippet (not a variant matrix — a table doesn't vary the way a badge does) | `design-system/Table/Table.tsx` | `Table.stories.tsx` |
| Tooltip | 1 | `design-system/Tooltip/Tooltip.tsx` | `Tooltip.stories.tsx` — **unused in production, see Archive** |
| DataQualityBadge | 5 (1:1 with DataQuality values) | `data-quality/DataQualityBadge/DataQualityBadge.tsx` | `DataQualityBadge.stories.tsx` |
| DataCoverageBadge | 1 | `data-quality/DataCoverageBadge/DataCoverageBadge.tsx` | `DataCoverageBadge.stories.tsx` |
| UnavailableMetric | 1 | `data-quality/UnavailableMetric/UnavailableMetric.tsx` | `UnavailableMetric.stories.tsx` |
| LimitedDataNotice | 1 | `data-quality/LimitedDataNotice/LimitedDataNotice.tsx` | `LimitedDataNotice.stories.tsx` — **unused in production, see Archive** |
| MethodologyPopover | 1 (open state shown) | `data-quality/MethodologyPopover/MethodologyPopover.tsx` | `MethodologyPopover.stories.tsx` |

**Scope note, stated plainly**: variant coverage here is representative,
not exhaustive, given this step's time constraints. `Badge`/`Tabs`/
`MetricValue` show every variant/state that exists in code. `Button`/
`Card` show every *variant* but not every `size` × `variant` combination.
`Table` shows one representative composition rather than a sort-state
matrix (sortable-column `aria-sort` states are documented in
`docs/figma-component-map.md`'s contract instead of drawn separately).
Nothing shown is fabricated — every variant/state that *is* shown
corresponds to real, verified code behaviour.

## Chart mapping

`04 Charts` documents all 9 existing chart-family members (no
`LineChart`/`AreaChart`/`StackedBar` invented, per this step's explicit
instruction) as representative cards: a small illustrative visual (built
from real Figma vector/rectangle nodes, using placeholder numbers clearly
in a design-reference context, never claimed as real portfolio data) plus
a documentation block covering purpose, data dimensions, and — where
relevant — the specific implementation facts from
`docs/design-system-inventory.md` (e.g. `AllocationChart`'s fixed-width
sizing architecture, restated rather than normalised; `BarChart`/
`DrawdownChart`'s unused-in-production status).

## Pattern mapping

`05 Patterns` composes 9 of the patterns catalogued in
`docs/figma-component-map.md`'s Composition Patterns tier, built primarily
from real **instances** of the `03 Components` components (not redrawn
copies) — `createInstance()` calls against the actual component nodes, so
a change to the master component would propagate to every pattern
instance, the same relationship Figma always has between a component and
its uses. Not built: **Chart + Tabs** and **Chart + Period Selector** as
their own separate pattern cards (folded into the Screens page instead,
where the real Overview/Performance chart-plus-tabs composition already
demonstrates it more concretely than an isolated pattern card would).

## Screen mapping

Three reference compositions on `06 Screens`, each a single frame built
from the real design tokens (not hard-coded hex/pixel guesses) and
matching the actual application's information hierarchy, figures, and
states as verified live during Phases 5.5–5.7:

- **Overview**: header ($118.42 / +$15,420.33 / +61.5% / $98,765.43),
  historical value chart with period tabs, Contributions + Income cards,
  Allocation ("Unavailable — no allocation computed for 2026-06-30") +
  Top Holdings ("No securities currently held.") cards side by side,
  coverage footer. Verified against the real screenshot captured during
  Phase 5.5 live browser verification — same figures, same hierarchy.
- **Performance**: header, performance summary (four `MetricValue`-shaped
  stats), return-index chart (explicitly labelled "not portfolio value"),
  return decomposition, methodology (TWRR/XIRR), calendar performance row,
  coverage footer.
- **Holdings**: header, portfolio snapshot (0 holdings, $118.42 cash),
  Allocation + Holdings cards both showing their real unavailable/empty
  states side by side, allocation-over-time band (still populated despite
  0 current holdings — the fully-divested pattern made concrete), coverage
  footer.

**Discrepancies found while building these**: none that weren't already
documented. The screens match the implementation's actual current-state
figures (this portfolio's real fully-divested state) rather than an
idealised "populated" mockup, per this step's explicit instruction not to
invent holdings data. One cosmetic issue was found and is disclosed rather
than silently fixed: the Reconciliation Disclosure pattern's status badge
(built as a `Badge` component instance) displays the label text baked into
that specific tone variant ("Actual", from the generic `Tone=positive`
variant reused for convenience) rather than a reconciliation-specific
label like "Explained" — a real illustration of exactly the semantic
overlap `docs/design-semantics.md` §4 already flags as unresolved (open
decision #10): the reconciliation badge and the generic positive/negative
tone share one Figma variant today, the same way they share one `Badge`
tone family in code.

## Validation performed

- Every section was screenshotted via `get_screenshot`/`node.screenshot()`
  during construction and visually checked against the intended token
  values and layout (not just "the script didn't error").
- Colour swatches are bound to the same variables used everywhere else on
  the page — a Light/Dark toggle on the Colour section's frames
  (`setExplicitVariableModeForCollection`) was used to render both themes
  genuinely, not two hand-picked hex pairs.
- No new colour, spacing, or radius value was introduced anywhere in this
  file — every value traces to `tokens.css` via the variable's own
  `codeSyntax`.
- No application code was touched in this step. `git status` in the repo
  shows only new/changed files under `docs/`.

## Component mapping updates (Step 3 additions to `docs/figma-component-map.md`)

Only one addition was made, appended at the end of that file rather than
rewriting it: a short "Figma build status" line per component/chart
confirming it now has a real Figma node, plus the one new fact this step
surfaced that Step 2 couldn't have known — the Reconciliation Disclosure
badge-label overlap described above, which only became visible once an
actual instance was placed in a real composition.

## Step 4 addendum: audit and hardening

Step 4 re-verified every component, variable, and pattern created in Step
3 against the live Figma file (`get_metadata`), the React source, and the
Storybook stories — rather than assuming Step 3's own documentation was
correct. Full detail lives in `docs/figma-component-library.md` (the new
Step 4 deliverable); this section summarises what changed and what was
deliberately left alone.

**Figma mutations made in Step 4** (both additive, non-destructive):

1. **Dark-mode spot-check**: a new frame (`Dark mode spot-check (Step
   4)`, on `03 Components`) places live instances of `Badge`
   (`Tone=positive`), `Card` (`Elevation=raised`), and
   `DataQualityBadge` (`Quality=limited`) with the Color collection's
   Dark mode explicitly set via `setExplicitVariableModeForCollection`.
   Screenshotted and confirmed: every surface, border, shadow, and
   quality colour resolved correctly through the same variables used in
   Light mode — no separate dark-mode component variants were needed or
   created, exactly as the architecture requires.
2. **Attempted, blocked, and documented rather than forced**: adding a
   `Label` `TEXT` component property to the `Badge` component set (so an
   instance's text could be overridden without detaching — this would
   have directly fixed the Reconciliation Disclosure label mismatch
   found in Step 3). The Figma Plugin API rejected this:
   `addComponentProperty` only works on a component *before*
   `combineAsVariants`, and `Badge` was already combined in Step 3.
   Rather than detach and rebuild the component set (real, unnecessary
   Figma-file churn this step's own rules argue against), this is
   recorded as open decision #15 in `docs/design-system-decisions.md`,
   with the label-mismatch consequence recorded as open decision #16.

**Confirmed correct, no change needed** (the bulk of the audit): all 13
Primitive/Domain components' variant counts, all 9 chart cards' notes, all
9 pattern compositions' use of real instances, and all 3 screens'
figures — cross-checked against `docs/design-system-inventory.md`,
`docs/design-token-component-audit.md`, and the actual `.tsx`/`.module.css`
source, with zero new discrepancies found beyond the two already known
from Step 3 (the Reconciliation label issue, and the pre-existing
`--text-h2` naming mismatch, neither renamed nor "fixed" per this step's
explicit instruction).

**No new colour, spacing, radius, motion, or typography token was
introduced.** No existing open decision was resolved. No application code
was touched — `git status` after this step shows only documentation
changes plus the two additive Figma-file mutations above (both made via
`use_figma`, not by hand).

## Step 5 addendum: final pattern hierarchy

Full detail lives in `docs/figma-pattern-library.md` (the new Step 5
deliverable). Summary of the finished hierarchy:

```
TOKENS (Figma Variables / CSS custom properties)
  ↓
PRIMITIVES (Badge, Button, Card, MetricValue, SectionHeader, Table, Tabs, Tooltip)
DOMAIN COMPONENTS (DataQualityBadge, DataCoverageBadge, UnavailableMetric,
                    LimitedDataNotice, MethodologyPopover)
  ↓
COMPOSITION PATTERNS (11, classified CORE/REUSABLE/DOMAIN-SPECIFIC):
  Page Header, Section, Metric Group,                    — CORE
  Chart + Period Selector, Data Table,                    — CORE
  Loading / Empty / Unavailable,                          — CORE
  Chart + Table, Coverage Footer,                         — REUSABLE
  Methodology Disclosure, Reconciliation Disclosure,      — DOMAIN-SPECIFIC
  Fully-Divested / Historical-Still-Available             — DOMAIN-SPECIFIC
  ↓
SCREENS (Overview, Performance, Holdings — reference only, unaltered)
```

**Figma mutations made in Step 5** (both additive, composed from real
component instances, never flattened screenshots):

1. Two new patterns built on `05 Patterns`, required by this step's own
   brief and confirmed genuinely missing from Step 3/4: **Chart + Period
   Selector** (`Tabs` + a representative `TimeSeriesChart` line + a
   coverage line, with one tab shown disabled to demonstrate
   capability-driven period availability) and **Chart + Table**
   (a proportional bar + a real `Table` instance sharing one data
   context, per `AllocationSection.tsx`'s actual composition).
2. All 9 existing Step 3 pattern frames were renamed (not moved,
   restructured, or redrawn) to carry their `FIGMA ORGANISATION` group
   prefix (e.g. `Page Header` → `03 Section > Page Header`), and the
   outer section renamed to `05 Patterns — Composition Patterns` — a
   pure labelling change, zero visual or structural difference to any
   existing frame.

No pattern was invented beyond these two, both of which were explicitly
named as required in this step's own Parts 6 and 7 and both of which
correspond to real, currently-shipping compositions (Overview/
Performance's chart+tabs; Holdings' `AllocationSection`).

## Step 6 addendum: chart system formalised as visual contracts

Full detail in the new `docs/figma-chart-library.md` — not repeated
here. No new Figma page, component, or pattern was created in Step 6;
the `04 Charts` reference cards (Step 3) and the `Chart + Period
Selector`/`Chart + Table` patterns (Step 5) were re-verified against a
live browser check (desktop 1280px + mobile 375px, light + dark, on
Overview/Performance/Holdings) rather than rebuilt, and found accurate
with no discrepancies. Six honest implementation gaps were documented
(no keyboard chart interaction, no per-point screen-reader text, no
custom date-tick format, no compact-number axis formatting, no
accessible table alternative for `AllocationChart`, `BarChart`/
`DrawdownChart` still unconsumed) — none fixed, none escalated to a new
numbered open decision (each has an obvious future direction rather than
competing options).
