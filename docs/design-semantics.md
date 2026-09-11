# Design Semantics

Task B of the pre-Step-3 hardening pass. This document formalises the
independent semantic axes that already exist in the implementation
(confirmed by source inspection during the Step 2 token inventory and the
Task A audit) so Figma and Storybook share one vocabulary for them going
forward. Nothing here changes behaviour — this is a naming and boundary
document, not a design change.

The rule underneath all four axes: **the same underlying value can score
independently on more than one of them at once**, and no component may
infer one axis from another. An estimated, negative, available figure
looks different from an estimated, positive, available one only in its
sign colour — never in its data-quality treatment.

---

## 1. Data quality

**Question it answers**: *How trustworthy/provenanced is this value?*

**Values**: `actual`, `calculated`, `estimated`, `limited`, `unavailable`
(the `DataQuality` type; a closely related `ValuationStatus` type used for
daily valuation rows has the same four non-`limited` values plus
`unavailable`, `limited` being specific to analytics metrics rather than
daily price observations).

**Tokens**: `--color-quality-actual`, `--color-quality-calculated`,
`--color-quality-estimated`, `--color-quality-limited`,
`--color-quality-unavailable`.

**Rendered via**: `DataQualityBadge` (the sole component that maps a
`DataQuality` value to a badge), or a chart's own quality-based visual
treatment (`TimeSeriesChart`'s dashed/faded segments for `estimated`,
solid for `actual`/`calculated`).

**Confirmed in code**: `--color-quality-estimated` is a **neutral grey**
in both light and dark themes — it is structurally incapable of reading
as a warning or a loss, which is the whole point: "estimated" is a fact
about *how* a figure was produced (carried forward from the last known
valuation), not a judgement about whether that figure is good news.

---

## 2. Financial sign

**Question it answers**: *What is the arithmetic direction of this
value?*

**Values**: `positive`, `negative`, `neutral`.

**Tokens**: `--color-positive` / `--color-positive-bg`,
`--color-negative` / `--color-negative-bg`. (There is no
`--color-neutral` — the neutral case is simply the absence of a sign
class, which resolves to the ambient `--color-text`.)

**Determined by**: `formatting/money.ts`'s `sign()` function, purely from
a parsed value's arithmetic sign (`> 0` → positive, `< 0` → negative,
`=== 0` or unparseable → neutral) — **never** from a `DataQuality` value.
`MetricValue`'s `rawValue` prop is the only input `sign()` reads.

**The rule, stated explicitly, with the example from the phase brief
confirmed true in code**: an estimated negative number is rendered as
both facts simultaneously, never one overriding the other —

```
quality = estimated   →  dashed/faded line segment (TimeSeriesChart)
                          or a grey "Estimated" badge (DataQualityBadge)
sign    = negative     →  red figure text (MetricValue via sign())
```

Neither component has any code path that lets one axis suppress or
recolour the other. A `MetricValue` showing an `unavailableReason` is the
one deliberate exception: it renders **no** sign colour at all (not even
neutral's default text colour treated as a "sign"), specifically so
"unavailable" can never be mistaken for a real, colourable zero.

---

## 3. Capability / availability

**Question it answers**: *Can this metric or feature be provided at
all?*

**Values**: not an enum — a `{available: boolean, reason: string | null}`
pair (the `Capability` type) surfaced wherever a period, dimension, or
feature might not apply.

**Rendered via**: `Tabs`' `disabled`/`disabledReason` props (a disabled
period tab), or `UnavailableMetric`'s `title`/`reason` (a section that
can't be shown at all).

**This is not the same axis as data quality**, and the implementation
keeps them structurally separate:

- **A disabled 5Y period tab** is a *capability* limitation — the
  question "can I even ask for a 5-year return?" is answered *before* any
  value or its quality ever enters the picture. Rendered with
  `--color-text-faint` (a neutral "this option doesn't apply" treatment),
  never a data-quality token.
- **An existing 5Y metric whose underlying figure is unavailable** (the
  period is offered, the backend attempted to compute it, and the result
  came back with `data_quality: unavailable`) is a *data-quality*
  limitation on a value that capability already said could be asked for.
  Rendered with `--color-quality-unavailable` / `DataQualityBadge`.

**Confirmed in code**: `usePeriodTabs`/`useCapabilityTabs` (the two hooks
that produce `Tabs` items) never reach for a `--color-quality-*` token —
they only ever set `disabled`/`disabledReason` from the backend's own
`status`/`note`/`Capability` fields. Conversely, `DataQualityBadge` has no
`disabled` concept at all; it only ever renders one of the five quality
values. The two vocabularies do not currently share a component, and this
document formalises that they should not.

---

## 4. Reconciliation status — FUTURE SEMANTIC DECISION

**Values in the current implementation**: `PASS`, `FAIL`, `LIMITED`
(`ReconciliationStatus`).

**Where it's used**: `ReturnDecomposition` (Performance screen) — a
`Badge` with tone `positive` (`PASS` → "Explained"), `negative` (`FAIL` →
"Discrepancy found"), or `warning` (`LIMITED` → "Limited").

**The problem, stated plainly**: this reuses the *financial sign* tone
family (§2) for a concept that is not a financial gain or loss. A `FAIL`
reconciliation status means "the attributed change and the actual change
in this period don't add up within tolerance" — a statement about the
*model's internal consistency*, not about the portfolio's performance. A
portfolio can have a great quarter (strongly `positive` sign) with a
`FAIL` reconciliation, or a terrible quarter (strongly `negative` sign)
that reconciles perfectly (`PASS`). Coding `PASS` as the same visual tone
as "the portfolio went up" risks a reader conflating "this number is
good" with "this number adds up" — two different questions.

**This is not changed in this phase.** Per the hardening pass's
constraints, no visual or semantic behaviour is altered without a
resolved design decision, and this one requires exactly the kind of
visual/design exploration this phase is told not to force. It is recorded
as **open decision #10** in `docs/design-system-decisions.md`, with
`Badge`'s existing tone reuse documented as the current (unresolved)
state, not a recommendation.

**Note on `ErrorBoundary`**: the same category of tone reuse exists here
too — a caught rendering exception uses `--color-negative`/
`--color-negative-bg`, the same tokens as a financial loss, for something
that is a software bug, not a portfolio outcome. Documented here rather
than as a fifth axis, since it's the identical underlying issue
(financial-sign tones reused for a non-financial "something is wrong"
signal) rather than a new semantic category.

---

## 5. Unknown vs. Other (asset classification)

**The distinction, as implemented**: `AllocationChart`'s `AllocationSegment`
type has a `kind?: "known" | "unknown"` field, entirely separate from a
segment's `label`. A security or asset class the backend genuinely cannot
classify is `kind: "unknown"` and renders in a fixed, distinct grey
(`--color-unknown`) — **it is never folded into a generic "Other" bucket**,
and "Other" is not even a `kind` value; it would simply be a segment
whose `label` happens to be the literal string `"Other"` (which the
current `ASSET_CLASS_LABELS` maps do include, as one of the seven asset
classes the backend's `AssetClass` enum defines: `australian_equities`,
`international_equities`, `bonds`, `property`, `cash`, `other`,
`unknown`).

**Why this matters**: "Other" is a *known, deliberate* classification —
the backend positively determined this holding belongs to a residual
asset-class bucket. "Unknown" is an *absence of classification* — the
backend could not determine what this holding is. Visually collapsing
these into one grey "misc" treatment would erase a genuine, meaningful
distinction the backend already makes and reports. Confirmed in code:
`other` renders with a normal categorical palette colour (cycled through
`--chart-series-1..6` like any other real asset class), while only
`unknown` gets the dedicated `--color-unknown` treatment.

---

## Summary table

| Axis | Values | Tokens | Component(s) | Independent of |
|---|---|---|---|---|
| Data quality | actual / calculated / estimated / limited / unavailable | `--color-quality-*` | `DataQualityBadge`, chart quality segments | Sign, capability |
| Financial sign | positive / negative / neutral | `--color-positive/negative[-bg]` | `MetricValue`, `Badge` (generic tones) | Data quality, capability |
| Capability | available / disabled + reason | `--color-text-faint` (disabled), none dedicated (available = default) | `Tabs`, `UnavailableMetric` | Data quality, sign |
| Reconciliation status *(open)* | PASS / FAIL / LIMITED | reuses sign tones — **flagged, not resolved** | `Badge` in `ReturnDecomposition` | Should be independent; currently is not |
| Unknown vs. Other | unknown (no classification) / other (a real residual category) | `--color-unknown` vs. categorical palette | `AllocationChart`, `AllocationHistoryChart` | Each other — deliberately distinct |
