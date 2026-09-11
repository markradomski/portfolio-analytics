# Design System Decisions

Task D of the pre-Step-3 hardening pass, and the record of every Task C
(safe token consistency) finding. This is a decision register, not an
implementation plan — "Open Decisions" are recorded so Step 3 (Figma
structure) and any later phase can see what was deliberately left
unresolved and why, not solved here.

## Confirmed / existing

Established facts about the current implementation, verified during
Steps 1–2 and the Task A audit — not choices being made now, but things
already true that this phase's constraints require preserving:

- CSS Modules are the styling mechanism; no Tailwind, CSS-in-JS, or
  utility framework exists anywhere in `web/src`.
- `src/design-system/tokens.css` is the single canonical token source —
  confirmed zero raw hex colours exist in any component's CSS or TSX
  outside that one file.
- Semantic data-quality colours are structurally separate from financial
  sign (see `docs/design-semantics.md` §1–2) — confirmed no component
  derives one from the other.
- Capability/availability state is structurally separate from data
  quality (§3) — confirmed `Tabs`/`useCapabilityTabs`/`usePeriodTabs`
  never reach for a `--color-quality-*` token.
- Dark mode is entirely token-driven — every colour token is redefined
  once under `prefers-color-scheme: dark` and again under
  `[data-theme="dark"]`; no component branches on theme itself.
- Spacing uses the existing 8-step, 4px-based scale
  (`--space-1`…`--space-8`) — confirmed the only literal spacing values
  in use are the recurring `2px` micro-gap (see Task A) and a handful of
  chart-legend layout widths (`4.5rem`/`7rem`) that are alignment
  specifics, not spacing-scale candidates.
- Charts are hand-built D3 primitives, not a charting library.
- React owns chart state (hover, selection); D3 owns geometry (scales,
  paths, axis generation) — confirmed the one exception,
  `Axis`, is a deliberately-sanctioned imperative `d3.select` wrapper,
  not a violation of the rule.
- Every chart requires an `accessibleSummary` (`ChartContainer`'s prop is
  non-optional) — confirmed no chart-bearing section skips it.
- No raw hex values exist in component CSS where a semantic token already
  exists — confirmed via `grep` across `web/src` during this audit.

## Open decisions

Unresolved issues, recorded without being solved. Each carries the
current state, why it matters, the options as they stand today, and a
recommendation only where one is already obvious from the facts (not a
new design preference).

### 1. Breakpoint token strategy

- **Current state**: no `--breakpoint-*` token exists. Three hard-coded
  values are in use: `900px` (`AppShell` nav collapse), `860px`
  (`OverviewPage`/`PerformancePage` metric-grid collapse — the same
  value, used identically, in two separate files). `HoldingsPage` has no
  page-level breakpoint at all; its responsiveness comes entirely from
  `Table`'s `overflow-x: auto` and `MetricValue`'s flex-wrap.
- **Why it matters**: two different pixel values (`900`, `860`) for
  conceptually the same "desktop → mobile" transition is a real
  inconsistency a Figma frame-size convention would need to either
  reflect or reconcile.
- **Options**: (a) leave as three independent literals, documented; (b)
  introduce one shared `--breakpoint-mobile` (or similar) token and
  reconcile `860`/`900` to it; (c) keep them deliberately distinct (nav
  chrome vs. content grid may legitimately want different collapse
  points).
- **Recommendation**: none — this requires a visual decision (does the
  nav really need to collapse 40px later than the content grid, or is
  that accidental?) that wasn't made deliberately in the first place and
  shouldn't be guessed at here.
- **Status**: open.

### 2. Sizing / fine-spacing token strategy

- **Current state**: no `--size-*` scale exists (chart heights, table
  cell widths are per-component literals). Separately, a literal `2px`
  micro-spacing value (below `--space-1`'s 4px) recurs in 8 places for
  the same "tight label-to-value gap" purpose (see Task A audit).
- **Why it matters**: the `2px` recurrence is clearly deliberate, not
  accidental — a future `--space-0` or hairline token could formalise it,
  but doing so now would be adding a token because it "might be useful,"
  which this phase's constraints explicitly forbid.
- **Options**: (a) leave as a documented literal convention; (b) add
  `--space-0: 2px` (or similar) once a second, unrelated use case
  confirms the value is genuinely a scale step and not a coincidence.
- **Recommendation**: (a) for now.
- **Status**: open.

### 3. Border-width token strategy

- **Current state**: no `--border-width-*` token exists. `1px` is the
  border width everywhere a border is drawn; `2px` is used consistently
  for focus-visible outlines and a small number of emphasis strokes
  (`Tabs`' active-tab underline, chart crosshair dot stroke, flow-marker
  lines). `UnavailableMetric`'s dashed border is the only non-solid
  border style in the app.
- **Why it matters**: the 1px/2px split is consistent enough that it
  reads as a deliberate two-step scale already, even without a token
  formalising it.
- **Options**: (a) leave as literals (current); (b) introduce
  `--border-width-default: 1px` / `--border-width-emphasis: 2px`.
- **Recommendation**: none forced — the pattern is stable and legible as
  literals; tokenising it would change zero visual output and is
  optional polish, not a fix for an actual inconsistency.
- **Status**: open.

### 4. Display typography vs. `MetricValue` large typography

- **Current state**: `--text-display` (`700`, `--font-display` = Fraunces
  serif, `2.25rem`–`3.5rem`) is defined and unused anywhere.
  `MetricValue`'s `size="large"` uses its own literal
  (`600`, `--font-mono` = IBM Plex Mono, `1.75rem`–`2.75rem`).
- **Investigation (per this phase's explicit instruction not to merge
  automatically)**: these are **not** the same typographic role.
  `--text-display` is weight 700 in the editorial display serif —
  intended for a headline/hero treatment. `MetricValue large` is weight
  600 in the tabular monospace — intended specifically so a large figure's
  digits align and read with numeric precision, which a serif display
  face does not provide. Different weight, different family, different
  size range, different underlying intent (editorial vs. data precision).
- **Decision**: **left unchanged**, per the phase's own instruction to
  leave semantically-different tokens alone rather than force a
  consolidation. `--text-display` remains an unused foundation token,
  reserved for a genuine display/headline use case that hasn't been
  built (e.g. a marketing-style hero treatment), not a substitute for
  `MetricValue`'s numeric figure style.
- **Status**: resolved — no code change; documented as intentionally
  distinct, not consolidated.

### 5. `--text-h2` naming vs. usage

- **Current state**: corrected during this audit (see
  `docs/design-token-component-audit.md`) — `--text-h2` **is** used, by
  `AppShell.module.css`'s `.brand` rule for the "Portfolio" nav wordmark
  (rendered as a `<p>`, with `font-family` overridden to
  `--font-display` in the same rule). No actual `<h2>` element in the app
  uses this token; `SectionHeader` (which owns every real `<h2>`) uses
  `--text-meta` instead.
- **Why it matters**: a token named for a heading level, used for a
  brand wordmark instead, is a naming/usage mismatch that would confuse a
  Figma text-style library built by name alone (`Type / H2` implying "use
  this for a second-level heading," when in the one place it's actually
  used, it isn't one).
- **Options**: (a) rename the token to reflect its actual role (e.g.
  `--text-brand` or `--text-wordmark`) and leave `SectionHeader`'s h2s on
  `--text-meta` as they already are; (b) leave the name as-is and
  document the mismatch (current state); (c) introduce a real `<h2>`
  usage that matches the name and repurpose `.brand` to something else.
- **Recommendation**: (a) is the cleanest resolution once this reaches
  implementation, since it removes the misleading name without changing
  any rendered pixel — but renaming a token is exactly the kind of change
  this phase's constraints (#5: "do not replace existing tokens with a
  new naming convention") defer to a later, deliberate pass.
- **Status**: open.

### 6. `--radius-large` usage

- **Current state**: confirmed unused by any component (`grep` finds it
  only in `tokens.css` itself). Every current radius usage is `small`
  (badges, buttons, chart-legend swatches use an even smaller literal
  `2px`) or `medium` (cards, popovers, unavailable-metric boxes).
- **Why it matters**: nothing — it's a complete foundation token with no
  consumer yet, most likely reserved for a future larger-surface
  treatment (a modal, a full-bleed panel) that doesn't exist in this app
  today.
- **Recommendation**: keep; do not remove (per the "Tokens Removed:
  NONE" expectation) and do not force a usage onto an existing component
  merely to consume it.
- **Status**: open (dormant, not blocking).

### 7. Motion token usage

- **Current state**: `--motion-hover` (120ms) is actively used (`Button`,
  `Tabs`, `AppShell` nav links). `--motion-transition` (180ms) and
  `--motion-chart` (260ms) are both defined and **confirmed unused** by
  any component (`grep` finds each only in `tokens.css`). No chart
  currently animates a data transition — a re-render simply redraws the
  new state instantly.
- **Why it matters**: nothing is broken; these are reserved for future
  work (a chart transitioning smoothly between periods, a section
  expanding/collapsing) that hasn't been built. Per this phase's explicit
  instruction, no animation was added merely to consume them.
- **Recommendation**: keep both; do not add chart transition animation in
  this phase.
- **Status**: open (dormant, not blocking).

### 8. Reduced-motion policy

- **Current state**: `prefers-reduced-motion: reduce` is checked in
  exactly **one** place — `Skeleton`'s shimmer animation, which stops and
  falls back to a static `opacity: 0.6` under that media query. No other
  transitioning/animated element in the app (hover transitions on
  `Button`/`Tabs`/nav links, which are all sub-200ms colour fades) checks
  it.
- **Why it matters**: the existing hover-colour transitions are short
  enough (120ms, a colour fade, not motion/parallax) that they're
  unlikely to trigger vestibular discomfort the way `Skeleton`'s
  continuous 1.4s shimmer loop could — so the current, narrower policy
  (only guard genuinely continuous/looping animation) may already be the
  right one, not an oversight. This wasn't a deliberate documented policy
  before this audit, though.
- **Options**: (a) formalise "only continuous/looping animation needs a
  reduced-motion guard; brief hover transitions don't" as the documented
  policy (matches current implementation, zero code change); (b) extend
  `prefers-reduced-motion` handling to hover transitions too (a stricter,
  WCAG-adjacent policy some teams prefer).
- **Recommendation**: (a), since it already matches the implementation
  and the current transitions are genuinely brief — but this is a policy
  call, recorded as open rather than decided unilaterally here.
- **Status**: open.

### 9. Icon system

- **Current state**: no icon system exists at all — no icon component,
  icon font, or SVG icon set. The two icon-like glyphs in the app are
  literal Unicode characters: `ⓘ` (`MethodologyPopover`'s trigger) and `→`
  (`SectionHeader`'s "View all" link). Neither is a token or component.
- **Why it matters**: a Figma component library conventionally wants
  real icon assets for things like an info-disclosure trigger or a
  forward-navigation arrow, but introducing one wasn't requested by any
  actual screen need — two literal characters currently serve the
  purpose completely adequately.
- **Options**: (a) no icon system (current) — keep using literal
  characters where the current two suffice; (b) introduce a minimal
  icon system only if/when a screen genuinely needs an icon a Unicode
  character can't represent (e.g. a distinct up/down sort indicator
  beyond `Table`'s current `▲`/`▼` literal characters, which are the
  same pattern as `ⓘ`/`→` and were not separately flagged in Step 2 but
  are the same gap).
- **Recommendation**: (a) — do not introduce an icon system speculatively,
  per this phase's explicit constraint against novelty additions.
- **Status**: open (dormant, not blocking).

### 10. Reconciliation-status semantic colours

- **Current state**: `ReturnDecomposition`'s reconciliation badge reuses
  `Badge`'s `positive`/`negative`/`warning` tones (the financial-sign
  family) for `PASS`/`FAIL`/`LIMITED`, which are not financial-sign
  concepts — see `docs/design-semantics.md` §4 for the full argument.
  `ErrorBoundary` has the same category of reuse (a software error, not a
  financial loss, rendered with `--color-negative`).
- **Why it matters**: conflating "this reconciles" with "this portfolio
  did well" (or "this application is broken" with "this investment lost
  money") is a real, if subtle, semantic leak between two of the axes
  Task B/`docs/design-semantics.md` says must stay independent.
- **Options**: (a) leave as-is (current — no visual regression, but the
  semantic leak persists); (b) introduce a dedicated
  `--color-status-pass/fail/limited` (or similarly named) token family,
  visually distinct from financial sign, and repoint both
  `ReturnDecomposition` and `ErrorBoundary`; (c) keep reconciliation on
  the sign family deliberately, on the argument that "did this add up"
  and "did this go well" are close enough in practice that a shared
  visual language (green = good, red = bad, amber = caution) is more
  legible to a user than a fourth colour family to learn.
- **Recommendation**: none forced — this is exactly the kind of
  visual-design judgement call the phase brief says not to resolve
  without exploration.
- **Status**: open — marked explicitly as a **future semantic decision**,
  not a bug.

### 11. `AllocationChart` fixed width vs. `ChartContainer`

- **Current state**: every other chart primitive is rendered inside a
  `ChartContainer` render-prop and receives `{width, height}` from
  `ResizeObserver`-driven measurement. `AllocationChart` instead takes a
  `width` prop directly, and both current call sites hard-code `640`.
- **Why it matters**: this is the one chart in the family that doesn't
  respond to its actual container width — on a narrower card or a future
  denser layout, it would either overflow or leave dead space rather
  than adapting, unlike every sibling chart.
- **Options**: (a) leave as-is (current — works today because both call
  sites happen to sit in a wide-enough card); (b) wrap `AllocationChart`
  in `ChartContainer` like the rest of the family, removing the
  hard-coded `640` in both callers.
- **Recommendation**: (b) is clearly the more consistent long-term shape,
  but changing it now would touch `AllocationChart`'s public API and two
  call sites for a problem that isn't currently causing a visible defect
  — deferred rather than done speculatively in a hardening-only phase.
- **Status**: open.

### 12. Should unused primitives appear in the primary Figma library?

- **Current state**: `Tooltip`, `LimitedDataNotice`, `BarChart`, and
  `DrawdownChart` are fully built, tested, and story'd, but none is
  currently consumed by any feature page.
- **Why it matters**: Step 3's Figma library could either (a) include
  them now, on the grounds that they're finished, documented design-
  system members regardless of current usage, or (b) place them in a
  clearly-marked "not yet in production" section/page (the brief's own
  `99 — Archive` page, or a dedicated area) so the library doesn't imply
  they're in active use when a Figma reader checks the real app.
- **Recommendation**: (b) — mirror their real status accurately rather
  than implying production usage that doesn't exist yet. This is a
  structural decision for Step 3, not implemented here.
- **Status**: open, deferred to Step 3.

### 13. Do domain-specific data-quality components belong in the same
    Figma hierarchy tier as generic primitives?

- **Current state**: in code, `data-quality/` is already a distinct
  directory from `design-system/`, with its own `index.ts` barrel — a
  structural signal that these are treated as a related-but-separate
  family, not flattened into the same primitive tier.
- **Why it matters**: Step 3's Figma page structure (`03 — Components`,
  `04 — Charts`, etc.) needs to decide whether data-quality components
  get their own section/page or a clearly-labelled subsection within
  Components — a purely organisational question with no visual
  consequence.
- **Recommendation**: mirror the code's own separation (a distinct
  subsection, not a separate top-level page, since the brief's page list
  doesn't allocate one) — but this is Step 3's call to make concretely,
  not pre-decided here.
- **Status**: open, deferred to Step 3.

### 14. Duplicated metric-group CSS across three feature files

- **Current state**: identified in the Task A audit — the exact same
  6-line "metric group flex-wrap + min-width:0 fix" CSS block is
  independently repeated in `OverviewPage.module.css`,
  `PerformancePage.module.css`, and `HoldingsPage.module.css`, rather
  than shared.
- **Why it matters**: this is implementation duplication, not a token
  gap — three copies of the same fix mean a future change to it (e.g. a
  different `flex-basis`) has to be applied three times correctly.
- **Options**: (a) leave as-is (current); (b) extract a shared
  `.metricRow`/`.metricGroup` class (CSS Modules `composes`, or a
  genuinely new `MetricGroup` component, matching the pattern the
  original Overview phase brief speculated about).
- **Recommendation**: (b) is worth doing in a future implementation
  phase, since Step 7 (Figma composition patterns) will want to name a
  "Metric Group" pattern regardless — better for the code to have one
  real implementation backing that name before Figma commits to it. Not
  done in this phase (creating a new component is explicitly out of
  scope for a hardening-only pass).
- **Status**: open.

### 15. Figma component properties can't be added after `combineAsVariants`

- **Current state**: discovered in Step 4 while attempting to add a real
  `TEXT` component property ("Label") to the `Badge` component set, so an
  instance's displayed text could be overridden without detaching — e.g.
  to fix the Reconciliation Disclosure pattern's badge showing "Actual"
  instead of "Explained" (see decision below, and
  `docs/figma-component-library.md`'s Badge entry). The Figma Plugin API
  rejected it: `addComponentProperty` can only be called on a component
  *before* `figma.combineAsVariants()` — once variants are combined, each
  variant's children are no longer eligible for new property
  definitions. Badge (and every other variant-based component in this
  library) was already built and combined in Step 3.
- **Why it matters**: this is a Figma API/tooling constraint, not a
  design decision — it means "add a Label property to an existing
  variant set" is a rebuild operation (detach → recreate with the
  property → recombine), not an incremental edit. Any future Step that
  wants text-overridable badges (or any other variant-based primitive)
  needs to plan for that rebuild cost up front, or build the property in
  from the very first construction pass.
- **Options**: (a) leave `Badge` etc. as baked-text variants (current);
  (b) rebuild the affected component sets from scratch with the property
  included from the start, next time a change touches them anyway (avoid
  a rebuild solely to add this).
- **Recommendation**: (b), opportunistically — do not rebuild solely to
  add this property; do it the next time an unrelated change already
  requires touching the component set.
- **Status**: open.

### 16. Reconciliation Disclosure pattern instance shows a mismatched label

- **Current state**: the `05 Patterns` page's Reconciliation Disclosure
  composition uses a `Badge` `Tone=positive` instance for a `PASS`
  reconciliation status. That variant's baked-in label is "Actual" (a
  data-quality-oriented word, reused for convenience when the pattern was
  built), not "Explained" (the actual copy `ReturnDecomposition.tsx`
  renders for a `PASS` status). This is separate from — but a concrete
  illustration of — open decision #10 (reconciliation status reusing
  Financial Sign tones): here the *colour family* being shared is the
  known issue, but the *specific label text* being wrong is a new,
  narrower finding of its own, and is blocked from a clean fix by open
  decision #15 above.
- **Why it matters**: as it stands, the one Figma reference for this
  pattern shows text a reader could mistake for the real product's
  copy.
- **Options**: (a) leave as-is, documented (current); (b) manually
  detach that one instance and hand-edit its text (a one-off fix that
  would drift from the master component on any future Badge update); (c)
  rebuild `Badge` with a Label property (see #15) and then this fixes
  itself for free.
- **Recommendation**: (c), whenever #15 is actioned. Not (b) — a detached,
  hand-edited instance is worse than a documented, honest limitation,
  since it silently stops tracking the master component.
- **Status**: open.
