# Figma Component Library

Step 4 deliverable: the hardened, audited component library reference.
Every entry below was re-verified against the actual Figma file (via
`get_metadata`), the actual React source, and the actual Storybook story —
not copied forward from `docs/figma-component-map.md` unchecked. Where
Step 4's audit found the Step 3 representation already correct, that's
stated plainly rather than re-explained; where it found something new,
that's called out explicitly.

No application code changed in this step. No new colour, spacing, radius,
or typography token was introduced. No open decision from
`docs/design-system-decisions.md` was resolved.

## How to read this document

Each entry is one reusable Figma component, in the exact shape Step 3
established:

```
Name → Purpose → Variants → States → Slots → Tokens → Auto Layout →
Responsive → Accessibility → React → Storybook → Known exceptions
```

"Known exceptions" is new in Step 4 — it's where a genuine gap between the
Figma representation and the implementation is recorded, rather than
silently smoothed over.

---

## Primitives

### Badge

- **Figma**: `03 Components` → component set `Badge` (10 variants, axis
  `Tone`), verified present via `get_metadata`.
- **Purpose**: the one place any status/tag is rendered.
- **Variants**: `positive`, `negative`, `warning`, `neutral`, `accent`,
  `quality-actual`, `quality-calculated`, `quality-estimated`,
  `quality-limited`, `quality-unavailable` — all 10 confirmed present,
  matching `Badge.tsx`'s `tone` prop exactly.
- **States**: `withDot` on/off exists in code but was not built as a
  second Figma variant axis (would double the variant count for a purely
  visual toggle already demonstrated once per tone) — see "Known
  exceptions."
- **Slots**: label text (currently baked per variant, not a component
  property — see below).
- **Tokens**: bound Color variables for every tone's foreground/
  background (10 pairs), `--space-1/2`, `--radius-small`.
- **Auto Layout**: yes — horizontal, hug-sized, `itemSpacing: 4`.
- **Responsive**: none (inline, intrinsic size) — matches implementation.
- **Accessibility**: the dot is decorative; tone is always paired with
  text, matching the "never colour alone" rule.
- **React**: `design-system/Badge/Badge.tsx`. **Storybook**:
  `Badge.stories.tsx`.
- **Known exceptions**:
  1. **No `Label` component property.** Step 4 attempted to add one
     (a real Figma `TEXT` component property so an instance's displayed
     text could be overridden without detaching) and hit a genuine Figma
     API constraint: `addComponentProperty` can only be called on a
     component *before* `combineAsVariants` — once variants are combined,
     their children are no longer "product components" in the API's
     terms and reject new property definitions. Retrofitting this onto
     the already-built set would require detaching and rebuilding it,
     which is more Figma-file churn than this hardening pass's own rules
     allow ("do not create scripts that mutate the Figma file
     unnecessarily"). **Documented as a new open decision (#15 in
     `docs/design-system-decisions.md`), not resolved.**
  2. **Direct consequence of #1, found in Step 3 and reconfirmed here**:
     the `05 Patterns` Reconciliation Disclosure pattern reuses the
     `Tone=positive` variant instance for a `PASS` status, and that
     variant's baked-in label ("Actual") is not reconciliation-specific
     ("Explained" would be correct). This is a real, visible inaccuracy
     in that one pattern instance. Left as-is per this step's explicit
     instruction not to fix things merely because Step 4 encountered
     them, and because the Label-property fix that would properly solve
     it is blocked by #1.

### Button

- **Figma**: `03 Components` → component set `Button` (3 variants, axis
  `Variant`), confirmed present.
- **Purpose**: single button implementation.
- **Variants**: `primary`, `secondary`, `ghost` — all 3, matching
  `Button.tsx` exactly. `size` (`default`/`small`) was **not** built as a
  second variant axis in Step 3 and was not added in Step 4 either — see
  "Known exceptions."
- **States**: `:disabled`, `:hover`, `:focus-visible` exist in CSS but
  were not modelled as separate Figma states (a static file has no true
  hover/focus state to render meaningfully beyond a colour swap, and this
  step's own rule against variant explosion argues against adding 3 more
  variants per existing variant for states with no distinct layout).
- **Slots**: label text (same baked-text limitation as Badge).
- **Tokens**: `--text-body-strong`, `--space-1/2/3/4`, `--radius-small`,
  colour variables for each variant's bg/fg/border.
- **Auto Layout**: yes — horizontal, hug-sized, centered content.
- **Responsive**: none — matches implementation.
- **Accessibility**: native `<button>` semantics are a React/DOM concept
  with no direct Figma equivalent; documented here rather than modelled:
  `:focus-visible` uses a 2px accent outline, `:disabled` drops opacity to
  0.45.
- **React**: `design-system/Button/Button.tsx`. **Storybook**:
  `Button.stories.tsx`.
- **Known exceptions**: the `size` axis (`default`/`small`) is
  implemented in code and story'd, but not represented as a second Figma
  variant dimension. This is a real, if minor, coverage gap — not fixed
  in this step since it would require rebuilding the component set (same
  `addComponentProperty`-before-`combineAsVariants` ordering constraint
  applies to adding a new variant axis after the fact too). Noted for a
  future pass, not escalated to the open-decisions register since it's a
  coverage gap, not an ambiguous design question.

### Card

- **Figma**: `03 Components` → component set `Card` (2 variants, axis
  `Elevation`), confirmed present.
- **Purpose**: the one section-container shape.
- **Variants**: `flat`, `raised` — both, matching `Card.tsx`'s
  `elevation` prop exactly.
- **States**: none in code, none in Figma — correct match.
- **Slots**: title, subtitle, action (header row), children (body) — the
  Figma instance shows a representative title + body; the `action` slot
  was not separately demonstrated (a genuine, minor coverage gap, not
  fixed here).
- **Tokens**: `--color-surface`, `--color-border`, `--radius-medium`,
  `--space-3/4/5`, `Shadow/Low` effect style (raised only, correctly
  omitted on flat).
- **Auto Layout**: yes — vertical, fixed width (280px in the Figma
  instance — an arbitrary representative width, not itself a token; the
  real implementation has no fixed Card width, it's contextual).
- **Responsive**: Card has no responsive behaviour of its own in the
  implementation (children control reflow) — correctly not modelled as
  one in Figma either.
- **Dark mode**: **spot-checked in this step** — a `raised` Card instance
  was placed with the Color collection's Dark mode explicitly set and
  screenshotted; surface, border, and shadow all resolved correctly with
  no manual colour overrides needed (see `docs/figma-architecture.md`
  Step 4 addendum for the verification note).
- **React**: `design-system/Card/Card.tsx`. **Storybook**:
  `Card.stories.tsx`.
- **Known exceptions**: none beyond the unavailable `action` slot
  demonstration noted above.

### Tabs

- **Figma**: `03 Components` → component set `Tabs (single tab)` (3
  variants, axis `State`), confirmed present.
- **Purpose**: one tab item; the full `Tabs` component is a data-driven
  row of these.
- **Variants/States**: `default`, `selected`, `disabled` — all 3,
  matching the real component's rendered states exactly (`aria-selected`,
  `aria-disabled`).
- **Slots**: label text.
- **Tokens**: `--text-body-strong`, colour variables per state,
  `--space-1/3`.
- **Auto Layout**: yes — vertical (label + underline bar), hug-sized.
- **Responsive**: the *list* of tabs scrolls (`overflow-x: auto`, the
  Phase 5.6 mobile-overflow fix) — this is a property of the tab *list*
  container, not the individual tab item shown here, so it's correctly
  out of scope for this single-tab component and is instead noted in the
  `docs/design-system-inventory.md` Tabs entry and restated in
  `04 Charts`/`05 Patterns` context where relevant.
- **Accessibility**: `role="tab"`/`aria-selected`/`aria-disabled`,
  disabled reason exposed via native `title` — documented, not
  Figma-representable (no tooltip-on-hover was built for the disabled
  variant, since Figma's own hover state isn't a meaningful stand-in for
  a native HTML `title` attribute).
- **React**: `design-system/Tabs/Tabs.tsx`. **Storybook**:
  `Tabs.stories.tsx`.
- **Known exceptions**: none — this is one of the two components (with
  Badge/DataQualityBadge) where Figma variant coverage is fully 1:1 with
  code.

### MetricValue

- **Figma**: `03 Components` → component set `MetricValue` (4 variants,
  axis `State`), confirmed present.
- **Purpose**: the one place a labelled figure is displayed.
- **Variants shown**: `default` (positive sign), `negative`, `neutral`,
  `unavailable`. `size="large"` was **not** built as a second axis — see
  "Known exceptions."
- **Typography — explicitly re-verified per this step's instruction**:
  the `unavailable` variant renders **no** sign colour at all (confirmed
  in the Figma instance's fill — plain muted text colour, not neutral's
  default-text colour either, matching `MetricValue.tsx`'s actual
  behaviour where `unavailableReason` replaces the value entirely).
- **IMPORTANT, per this step's explicit instruction — confirmed, not
  re-litigated**: `MetricValue`'s large-size typography (weight 600,
  `--font-mono`, `clamp(1.75rem, 1.3rem + 1.5vw, 2.75rem)`) remains
  intentionally distinct from `--text-display` (weight 700,
  `--font-display`/Fraunces serif). This was investigated and resolved in
  Step 2, restated (not re-decided) here: different weight, different
  family, different intended role (data precision vs. editorial
  headline). **Not merged.**
- **Tokens**: `--text-meta` (label), `--color-{positive,negative,
  text-muted,text-faint}`.
- **Auto Layout**: yes — vertical, hug-sized.
- **Responsive**: the `large` variant's real `clamp()`-based responsive
  scaling has no direct Figma equivalent (Figma text doesn't support CSS
  `clamp()`) — documented as a representation limitation, not fixed.
- **React**: `design-system/MetricValue/MetricValue.tsx`. **Storybook**:
  `MetricValue.stories.tsx`.
- **Known exceptions**: `size="large"` variant not modelled as its own
  Figma variant (a coverage gap, not a design decision) — the `01
  Foundations` Typography section separately shows the large-figure type
  spec, so the value *is* documented, just not as a `MetricValue`
  component variant specifically.

### SectionHeader

- **Figma**: `03 Components` → single component `SectionHeader`,
  confirmed present.
- **Purpose**: recurring section-hierarchy shape.
- **Variants**: **none** — confirmed correct: no `Compact` variant exists
  in `SectionHeaderProps` (re-verified in this step's source audit, not
  just carried forward).
- **Typography — confirmed, not renamed**: uses `--text-meta` for its
  title, deliberately, **not** `--text-h2` (the token whose name would
  suggest it, per its literal name). Per this step's explicit
  instruction, `--text-h2` was **not renamed** and `SectionHeader` was
  **not forced** onto it. The existing mismatch (`--text-h2` is used
  instead by `AppShell`'s brand wordmark, a `<p>`, not any `<h2>`) remains
  exactly as documented in Step 2/3, restated here as still-open decision
  #5.
- **Slots**: title, subtitle, action, viewAllHref/Label.
- **Tokens**: `--text-meta`, `--color-text-muted/faint`, `--color-accent`,
  `--color-border`, `--space-2/3/4`.
- **Auto Layout**: yes — horizontal, hug-sized.
- **Accessibility**: renders `<h2>` in the real DOM — the one place every
  screen's heading hierarchy is established. Figma has no heading-level
  concept to bind to; documented in text only.
- **React**: `design-system/SectionHeader/SectionHeader.tsx`.
  **Storybook**: `SectionHeader.stories.tsx` (6 stories).
- **Known exceptions**: none.

### Table

- **Figma**: `03 Components` → single component `Table` (one
  representative 3-row × 5-column snippet), confirmed present.
- **Purpose**: the one data-table implementation.
- **Column alignment — re-verified**: text columns left-aligned, numeric
  columns right-aligned in `IBM Plex Mono` (matching `.numeric` CSS's
  `font-variant-numeric: tabular-nums` + `font-family: var(--font-mono)`
  exactly — the Figma snippet uses the same mono family for the same
  reason: tabular-figure alignment).
- **Header styling**: uppercase, `--text-meta`-equivalent size/weight,
  muted colour — matches `.table th` CSS.
- **Sorting indication**: **not shown as a distinct state** in the Figma
  snippet (no `▲`/`▼` sort icon or `aria-sort` visual drawn) — a real,
  acknowledged gap. `Table.tsx`'s actual `aria-sort` mechanism (never
  `role="button"`, preserving native `columnheader` semantics — the
  Phase 5.1–5.4 regression this component exists partly to prevent
  repeating) is documented in text in `docs/design-system-inventory.md`
  and `docs/figma-component-map.md`, but was not re-drawn as a Figma sort
  arrow in this step. Not fixed — a content addition to an existing
  single-instance component, deferred rather than rushed.
- **Row spacing**: `--space-3/4` cell padding, 1px bottom border per row
  — matches `.table th, .table td` CSS.
- **Responsive**: the real `Table` wraps in `overflow-x: auto` (scrolls
  within its own box rather than overflowing the page) — **not shown**
  in the static Figma snippet (a static frame can't demonstrate a
  scroll-clip interaction meaningfully); documented in text instead.
  Confirmed: **not** redesigned into a card-based mobile layout, since
  that is not the real implementation's responsive behaviour (the real
  `Table` only ever scrolls horizontally, at every screen size — per this
  step's explicit "do not redesign into cards unless that is already the
  implemented behaviour").
- **React**: `design-system/Table/Table.tsx`. **Storybook**:
  `Table.stories.tsx`.
- **Known exceptions**: sort-state and horizontal-scroll behaviour are
  documented in text, not drawn as additional Figma states, per the
  scope discipline of this hardening-only step.

### Tooltip

- **Figma**: `03 Components` → single component `Tooltip`, confirmed
  present, section explicitly named "Tooltip (unused in production)".
- **Purpose**: generic hover/focus tooltip for a static trigger.
- **Confirmed, re-verified in this step**: `Tooltip` remains a distinct,
  narrow-purpose component — it was **not** turned into a general-purpose
  popover system in this step, per the explicit instruction. It has one
  variant, one state, matching its actual single-purpose implementation.
- **React**: `design-system/Tooltip/Tooltip.tsx`. **Storybook**:
  `Tooltip.stories.tsx`.
- **Known exceptions**: still not consumed by any production screen
  (confirmed again via source grep in this step — no change since Step 3)
  — every actual disclosure uses `MethodologyPopover` instead. Correctly
  placed on `99 Archive`'s index, not the primary component list.

---

## Domain components

### DataQualityBadge

- **Figma**: `03 Components` → component set `DataQualityBadge` (5
  variants, axis `Quality`), confirmed present.
- **Confirmed distinct from Badge's generic tones**: re-verified the 5
  quality variants (`actual`/`calculated`/`estimated`/`limited`/
  `unavailable`) use the `Data Quality/*` colour variables, not the
  `Action-Status/*` ones, even where the *values* coincide in this
  palette (e.g. `quality-actual`'s green and `positive`'s green are the
  same hex today, but bound to two separate Figma variables — a future
  palette change to one would not silently change the other). This is
  the semantic-separation guarantee from `docs/design-semantics.md` §1–2,
  now structurally enforced in Figma too, not just in CSS.
- **React**: `data-quality/DataQualityBadge/DataQualityBadge.tsx`.
  **Storybook**: `DataQualityBadge.stories.tsx`.
- **Known exceptions**: none — full 1:1 variant coverage.

### DataCoverageBadge

- **Figma**: `03 Components` → single component `DataCoverageBadge`,
  confirmed present.
- **Confirmed**: represents coverage (a plain text line reading real
  `DataCoverage` field values), not financial performance — no colour
  coding at all, correctly matching the real component (which is inert
  text, no `Badge` wrapper).
- **React**: `data-quality/DataCoverageBadge/DataCoverageBadge.tsx`.
  **Storybook**: `DataCoverageBadge.stories.tsx`.
- **Known exceptions**: the "no valuation history available yet" empty
  state was not separately modelled as a second Figma instance (a minor
  coverage gap, not fixed here).

### UnavailableMetric

- **Figma**: `03 Components` → single component `UnavailableMetric`,
  confirmed present.
- **Confirmed communicates "unavailable" distinctly from "zero"**: the
  Figma instance shows a title, an "Unavailable" badge, and a
  plain-language reason — no numeric value, no `0`, anywhere in the
  component. This directly satisfies Part 12's audit requirement.
- **Dashed border confirmed as the one deliberate exception** in an
  otherwise all-solid-border system (re-verified: no other component in
  this library uses a dashed stroke).
- **React**: `data-quality/UnavailableMetric/UnavailableMetric.tsx`.
  **Storybook**: `UnavailableMetric.stories.tsx`.
- **Known exceptions**: the `action` slot (an optional call-to-action)
  was not separately demonstrated.

### LimitedDataNotice

- **Figma**: `03 Components` → single component `LimitedDataNotice`,
  section explicitly named "(unused in production)", confirmed present.
- **Confirmed communicates data limitation, not financial negativity**:
  uses `--color-warning`/amber, never `--color-negative`/red — re-verified
  against both the Figma instance's bound variable and the source CSS.
- **React**: `data-quality/LimitedDataNotice/LimitedDataNotice.tsx`.
  **Storybook**: `LimitedDataNotice.stories.tsx`.
- **Known exceptions**: still unconsumed by any production screen
  (re-confirmed via grep in this step) — correctly placed on `99 Archive`
  index.

### MethodologyPopover

- **Figma**: `03 Components` → single component `MethodologyPopover`,
  shown in its **open** state, confirmed present.
- **Confirmed restrained, not visually dominant**: the panel is a small
  (260px-wide) card with body-text-scale content, positioned as a
  disclosure beneath a plain-text trigger — not a modal, not full-width,
  matching the real component's `position: absolute` inline-disclosure
  behaviour.
- **React**: `data-quality/MethodologyPopover/MethodologyPopover.tsx`.
  **Storybook**: `MethodologyPopover.stories.tsx`.
- **Known exceptions**: the closed state (trigger only, no panel) was not
  separately shown as a second instance — only the open state, since the
  closed state is just the same trigger text without the panel, which
  the "Sub-period linked ⓘ" trigger line alone already demonstrates.

---

## Chart family (light hardening, per Part 16)

All 9 — `ChartContainer`, `ChartTooltip`, `Crosshair`, `Axis`,
`TimeSeriesChart`, `AllocationChart`, `AllocationHistoryChart`,
`BarChart`, `DrawdownChart` — confirmed present on `04 Charts` as
reference cards (not attempted as Figma components with variants, since
D3-driven visual output has no meaningful "variant" the way a Badge tone
does). Each card's documentation text was re-checked against
`docs/design-system-inventory.md`'s Charts section during this audit; no
discrepancy found. `AllocationChart`'s fixed-width sizing architecture
(the one chart that doesn't go through `ChartContainer`) remains
explicitly called out in its card's text, not normalised away.

## Composition patterns (re-verified, per Part 17)

All 9 patterns on `05 Patterns` were re-inspected via `get_metadata` and
confirmed to be composed primarily from real `createInstance()` calls
against the `03 Components` nodes (not redrawn copies) — meaning a future
edit to a master component (e.g. Badge's colour) would propagate to every
pattern instance built from it, the same live relationship Figma always
maintains. No new pattern components were created in this step, and no
pattern was promoted to a standalone reusable component — all 9 remain
compositions, per the explicit "do not create components for every
pattern" instruction.

## Screen validation (Part 18)

Overview, Performance, and Holdings on `06 Screens` were re-checked
against the live application's actual figures and states (not redesigned).
One discrepancy was already identified and documented in Step 3
(the Reconciliation badge label issue, restated above under Badge's
Known Exceptions) — no new discrepancy was found in this step's
re-verification. All three screens still correctly show this portfolio's
real fully-divested state (0 current holdings, $126.88 cash) rather than
an idealised populated mockup.
