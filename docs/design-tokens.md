# Design Tokens

Step 2 of the Figma + Storybook Foundation phase: a canonical inventory of
every design token that actually exists in code today, at
`web/src/design-system/tokens.css` (the single file every colour/spacing/
radius/shadow/motion value in the app reads from — confirmed by inspection,
not assumed). This document maps what exists; it does not add, rename, or
remove a single token. Where a category the phase brief anticipated has no
token in code, that is stated as a gap rather than filled in.

All tokens are plain CSS custom properties on `:root`, redefined once
under `@media (prefers-color-scheme: dark)` and again under
`:root[data-theme="dark"]` (an explicit override, for a future manual
theme toggle) — no component ever branches on theme itself; every
component only ever references the token name.

## Colour

### Surface / text / border (theme-aware)

| Token | Light value | Dark value |
|---|---|---|
| `--color-background` | `#fafaf9` | `#17140f` |
| `--color-surface` | `#ffffff` | `#201c17` |
| `--color-surface-raised` | `#ffffff` | `#26221c` |
| `--color-border` | `#e7e5e4` | `#35302a` |
| `--color-border-strong` | `#d6d3d1` | `#453f37` |
| `--color-text` | `#1c1917` | `#f2efe9` |
| `--color-text-muted` | `#78716c` | `#a39a8d` |
| `--color-text-faint` | `#a8a29e` | `#786e60` |

### Semantic action / status

| Token | Light value | Dark value |
|---|---|---|
| `--color-positive` | `#15803d` | `#4ade80` |
| `--color-positive-bg` | `#f0fdf4` | `#0f2417` |
| `--color-negative` | `#b91c1c` | `#f87171` |
| `--color-negative-bg` | `#fef2f2` | `#2c1414` |
| `--color-warning` | `#b45309` | `#fbbf24` |
| `--color-warning-bg` | `#fffbeb` | `#2a2110` |
| `--color-accent` | `#1d4ed8` | `#60a5fa` |
| `--color-accent-bg` | `#eff6ff` | `#12203a` |

### Data quality (financial-semantic — see "Semantic separation" below)

| Token | Light value | Dark value |
|---|---|---|
| `--color-quality-actual` | `#15803d` | `#4ade80` |
| `--color-quality-calculated` | `#1d4ed8` | `#60a5fa` |
| `--color-quality-estimated` | `#a8a29e` | `#786e60` |
| `--color-quality-limited` | `#b45309` | `#fbbf24` |
| `--color-quality-unavailable` | `#d6d3d1` | `#453f37` |
| `--color-unknown` | `#a8a29e` | `#786e60` |

### Chart palette (categorical, colour-blind-legible)

| Token | Light value | Dark value |
|---|---|---|
| `--chart-series-1` | `#1d4ed8` | `#60a5fa` |
| `--chart-series-2` | `#b45309` | `#fbbf24` |
| `--chart-series-3` | `#15803d` | `#4ade80` |
| `--chart-series-4` | `#7c3aed` | `#a78bfa` |
| `--chart-series-5` | `#be185d` | `#f472b6` |
| `--chart-series-6` | `#0e7490` | `#22d3ee` |
| `--chart-grid` | `#eeece9` | `#2a2620` |
| `--chart-axis` | `#a8a29e` | `#786e60` |

**Observation**: `--color-positive` and `--color-quality-actual` share the
same value by coincidence of this particular palette (both `#15803d` in
light mode), and likewise `--color-accent`/`--color-quality-calculated`.
This is **not** a sign that the two token families are the same concept —
see the semantic-separation section below. Do not collapse them into one
token merely because their current values match; a future palette change
to one must not accidentally change the other.

## Typography

Three font families:

| Token | Value |
|---|---|
| `--font-display` | `"Fraunces", Georgia, "Times New Roman", serif` |
| `--font-body` | `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif` |
| `--font-mono` | `"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace` |

Nine composite type styles (each a full CSS `font` shorthand: weight/size/
line-height/family):

| Token | Value | Used for |
|---|---|---|
| `--text-display` | `700 clamp(2.25rem, 1.8rem + 2vw, 3.5rem)/1.05 var(--font-display)` | Not currently used by any component — see gap below |
| `--text-h1` | `600 1.75rem/1.2 var(--font-body)` | Page `<h1>` (Overview, Performance, Holdings) |
| `--text-h2` | `600 1.375rem/1.3 var(--font-body)` | **Correction (verified against source during the pre-Step-3 audit)**: this token *is* referenced — by `AppShell.module.css`'s `.brand` rule, for the "Portfolio" nav wordmark. That wordmark renders as a `<p>`, not an `<h2>`, and its `font-family` is immediately overridden to `--font-display` in the same rule, so only the token's weight/size/line-height actually apply. `SectionHeader`'s `<h2>` (the component that owns every actual `<h2>` element in the app) uses `--text-meta` instead, deliberately, for its small-caps label look — see gap below |
| `--text-h3` | `600 1.0625rem/1.4 var(--font-body)` | `Card` title, `UnavailableMetric` title |
| `--text-body` | `400 0.9375rem/1.55 var(--font-body)` | Default paragraph/description text |
| `--text-body-strong` | `600 0.9375rem/1.55 var(--font-body)` | `Button`, `Tabs` tab labels, emphasised inline text |
| `--text-meta` | `500 0.75rem/1.4 var(--font-body)` | `SectionHeader` titles, `Badge`, captions, footnotes |
| `--text-figure` | `600 1rem/1.3 var(--font-mono)` | Numeric table cells, chart tooltip values |
| `--text-figure-lg` | `600 1.5rem/1.15 var(--font-mono)` | `MetricValue`'s default-size figure |

**Gaps to flag**:
- `--text-display` exists in the token file but **no component references
  it** — it was defined for a future hero/display treatment (e.g. the
  portfolio's headline value in extra-large type) that hasn't been built.
  `MetricValue`'s `large` size uses its own inline `clamp()` calculation
  (`600 clamp(1.75rem, 1.3rem + 1.5vw, 2.75rem)/1.1 var(--font-mono)` in
  `MetricValue.module.css`) rather than `--text-display` — a real
  duplication worth reconciling in Figma foundations (Step 4), not
  resolved here.
- `--text-h2` **is used**, but not for a heading — see the corrected row
  above. `SectionHeader` (the component that owns every actual `<h2>`
  element in the app) styles its title with `--text-meta` instead,
  deliberately, for the small-caps section-label look. So the token's
  name (`h2`) and its actual usage (a brand wordmark rendered as a `<p>`)
  don't match — a naming/usage mismatch to resolve in Step 4, not an
  unused token to remove.

## Spacing

An 8-step, 4px-based scale — every margin/padding/gap in the app reads
from this list:

| Token | Value (px equiv.) |
|---|---|
| `--space-1` | `0.25rem` (4px) |
| `--space-2` | `0.5rem` (8px) |
| `--space-3` | `0.75rem` (12px) |
| `--space-4` | `1rem` (16px) |
| `--space-5` | `1.5rem` (24px) |
| `--space-6` | `2rem` (32px) |
| `--space-7` | `3rem` (48px) |
| `--space-8` | `4rem` (64px) |

The scale is not perfectly geometric (4-8-12-16-24-32-48-64 — doubling
only kicks in after `--space-4`), which is a deliberate, existing choice,
not a gap.

## Sizing

**No dedicated sizing-scale tokens exist.** Component dimensions (chart
heights of `260`/`280`/`320`/`340`px, table cell widths, icon sizes) are
set as literal numbers per component, not drawn from a shared `--size-*`
scale. This is a real gap relative to a fully-tokenized system, flagged
for a decision in Step 4 rather than resolved by inventing values now —
the actual heights in use today are:

| Context | Height |
|---|---|
| Overview's main value chart | 340px |
| Performance's return-history chart | 280px |
| Holdings' allocation-over-time chart | 260px |
| Security detail's value/units/weight chart | 280px |
| `ChartContainer`'s own default | 320px |

## Radius

| Token | Value |
|---|---|
| `--radius-none` | `0` |
| `--radius-small` | `4px` |
| `--radius-medium` | `8px` |
| `--radius-large` | `14px` |

**Gap**: `--radius-large` is defined but **not referenced by any
component** today — every current radius usage is `small` (badges,
buttons, chart legend swatches) or `medium` (cards, unavailable-metric
boxes, popovers). Flagged, not removed.

## Border

**No dedicated border-width token exists.** Every border in the app is a
literal `1px` (occasionally `2px` for a focus ring or a chart's dashed
carried-forward stroke) — only border *colour* is tokenized
(`--color-border`, `--color-border-strong`). A `--border-width-*` scale
was not introduced in this phase, per the "do not add tokens the
implementation doesn't already have" constraint.

## Shadow

| Token | Light value | Dark value |
|---|---|---|
| `--shadow-low` | `0 1px 2px rgba(28, 25, 23, 0.06)` | `0 1px 2px rgba(0, 0, 0, 0.3)` |
| `--shadow-medium` | `0 4px 16px rgba(28, 25, 23, 0.08)` | `0 4px 20px rgba(0, 0, 0, 0.4)` |

Used sparingly by design (`Card`'s `raised` elevation, `ChartTooltip`,
`MethodologyPopover`'s panel, `Tooltip`'s panel) — most of the app is
`flat` elevation with a border, not a shadow.

## Breakpoint

**No breakpoint tokens exist.** Every responsive media query in the
codebase hard-codes its own pixel width directly:

| File | Breakpoint | Purpose |
|---|---|---|
| `AppShell.module.css` | `900px` | Nav collapses from a sidebar to a horizontal-scrolling top row |
| `OverviewPage.module.css` | `860px` | Two-column metric grid collapses to one column |
| `PerformancePage.module.css` | `860px` | Same collapse, plus the methodology grid and reconciliation-detail grid |

Two different values (`900px`, `860px`) are in use for conceptually
similar "desktop → mobile" transitions, and no `Holdings` page-level
breakpoint currently exists as a distinct value (Holdings' own responsive
behaviour comes entirely from `Table`'s `overflow-x: auto` and
`MetricValue`'s flex-wrap, not a page-level media query). This is a real
inconsistency worth a `--breakpoint-*` decision in Step 4 — not resolved
here, per this step's instruction to map before changing.

## Motion

| Token | Value | Used for |
|---|---|---|
| `--motion-hover` | `120ms ease-out` | Colour/border-colour transitions on hover (`Button`, `Tabs`, `Badge`) |
| `--motion-transition` | `180ms cubic-bezier(0.4, 0, 0.2, 1)` | Defined, but **not referenced by any component today** — see gap below |
| `--motion-chart` | `260ms cubic-bezier(0.4, 0, 0.2, 1)` | Defined, but **not referenced by any component today** — no chart currently animates a transition (data changes re-render instantly); this token was set up in anticipation of chart-transition animation that hasn't been built |

`Skeleton`'s shimmer animation (`1.4s ease infinite`) is defined as a
literal `@keyframes` duration in `Skeleton.module.css`, not via a
`--motion-*` token — a minor inconsistency, flagged not fixed.

`prefers-reduced-motion: reduce` is respected in exactly one place today
(`Skeleton`'s shimmer stops, falling back to a static `0.6` opacity) — no
other animated/transitioning element currently checks this media query.

## Icons

**No icon system exists.** There is no icon component, icon font, or SVG
icon set anywhere in `web/src`. The single icon-like glyph in the entire
app is a literal Unicode `ⓘ` character inside `MethodologyPopover`'s
trigger button, styled with `font-size: 0.9em`. `SectionHeader`'s
"View X →" links use a literal `→` character the same way. Neither is a
token or a component — both are inline text content. This is a complete
gap, not a partial one, and Step 4 (Figma foundations) should decide
whether an icon system is in scope for this design-system phase at all
(the phase brief explicitly says "do not over-engineer" — introducing an
icon system was not requested and is not assumed here).

## Semantic separation: data quality vs. financial sign vs. capability

The phase brief is explicit that these three vocabularies must never
collapse into each other. Confirmed by inspection that the implementation
already keeps them structurally separate — this section documents that
separation as it exists today, it does not newly enforce it.

### 1. Data quality (`DataQuality` / `ValuationStatus`)

Values: `actual`, `calculated`, `estimated`, `limited`, `unavailable`.
Tokens: `--color-quality-actual/calculated/estimated/limited/unavailable`.
Rendered exclusively via `DataQualityBadge` (which maps each value to its
own token + label) or directly as a `Badge` `tone` prop
(`quality-actual`, etc.). This says **how sure the system is that a
figure is correct** — nothing about whether the figure is good or bad
news.

### 2. Financial sign (`positive` / `negative` / `neutral`)

Tokens: `--color-positive`/`--color-positive-bg`,
`--color-negative`/`--color-negative-bg`. Determined by
`formatting/money.ts`'s `sign()` function, purely from a value's
arithmetic sign (`> 0`, `< 0`, `=== 0` or unparseable → `neutral`) — never
from a data-quality value. Rendered via `MetricValue`'s `rawValue` prop
(colours the figure) and via `Badge` tones `positive`/`negative` (used
directly, e.g. `ReturnDecomposition`'s reconciliation-status badge, which
is a **different** kind of positive/negative — see caveat below).

**Confirmed in code**: an `estimated`-quality figure and a `negative`-sign
figure are independent axes that can co-occur — e.g. `TimeSeriesChart`'s
carried-forward (estimated) segment renders dashed/faded regardless of
whether the value itself is up or down, and `MetricValue`'s
`unavailableReason` path renders an italic message with **no** colour at
all (neither positive/negative/neutral), specifically so "unavailable"
is never visually confused with "zero" (a genuine `0` value still gets
`sign()`'s `neutral` colour, which is the app's default text colour, not
a distinct "zero" treatment — there is no separate "zero" token, by
design, since a real zero is just a number like any other).

**Caveat worth flagging**: `Badge`'s `positive`/`negative`/`warning` tones
are reused for two conceptually different things in the current
implementation — a financial gain/loss sign, and (in
`ReturnDecomposition`) a reconciliation **status**
(`PASS`→positive/"Explained", `FAIL`→negative/"Discrepancy found",
`LIMITED`→warning/"Limited"). A reconciliation `FAIL` is not a financial
loss, and reusing the negative-tone badge for it is a real, if minor,
semantic overlap between "this is bad news" and "this doesn't reconcile" —
noted here for Step 4/13 to decide whether reconciliation status deserves
its own token family, not resolved in this phase.

### 3. Capability / availability (`Capability.available` + `reason`)

Not a colour token at all — a boolean + a string, surfaced as
`disabled`/`disabledReason` on a `Tabs` item, or as `UnavailableMetric`'s
`title`/`reason`. This is **never** rendered via a data-quality colour
token; a disabled tab uses `--color-text-faint` (a neutral, "this option
doesn't apply" treatment), not `--color-quality-unavailable` (which is
reserved for a *value* whose provenance is unavailable, not a *feature*
that isn't offered). The two "unavailable" concepts — an unavailable
*metric value* vs. an unavailable *capability/period* — are kept visually
distinct in code today, and should stay that way in Figma.

### Non-collapsing rules confirmed present in the implementation

- `estimated` never renders with `--color-negative` or any warning tone —
  confirmed: `--color-quality-estimated` is a neutral grey in both
  themes, structurally incapable of reading as "bad news."
- `unavailable` (data quality) never renders as `0` — confirmed:
  `MetricValue`'s `unavailableReason` path replaces the value entirely
  with a message, it does not fall through to a numeric `0`.
- `limited` never renders as `negative` — confirmed: `--color-quality-
  limited` uses the warning-family colour (`--color-warning`/amber), not
  `--color-negative` (red), in both `DataQualityBadge` and
  `LimitedDataNotice`.
