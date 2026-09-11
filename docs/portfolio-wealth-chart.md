# Portfolio wealth chart (Overview) & advanced Performance decomposition

Step 9A. Two charts, two questions, two screens:

| Screen | Chart | Question it answers |
|---|---|---|
| **Overview** (`/`) | `PortfolioGrowthChart` (in `PortfolioGrowthSection`) | "How much is my portfolio worth, how much did I put in, and how much came from investment performance?" |
| **Performance** (`/performance`) | `PerformanceDecompositionChart` — **added alongside** every existing Performance section, replacing nothing | "Why did the balance move over this period?" |

The Overview chart is deliberately simpler than anything on Performance.
Performance keeps all of its existing analytics (summary, return index
history, return decomposition / attribution, methodology, calendar,
best/worst, drawdown, data coverage) and gains one more visualisation.

---

## 1. Overview wealth chart

> **Step 9A.2 — this chart was simplified.** It is a *communication layer*,
> not an accounting view. Its one job is that a normal investor gets it at
> a glance:
>
> > **BLUE** = money I put in **GREEN** = money I made
> > **RED** = money I lost **LINE** = what I've got
>
> The full signed decomposition — negative net contributions, the
> `balance = contributions + gain/loss` identity, TWRR/XIRR — lives on
> **Performance**. See §1a for the deliberate split between authoritative
> data and Overview display geometry.

### Purpose

A wealth snapshot understandable in a few seconds. Not an analytics chart
— no event markers, no per-point dots, no TWRR/XIRR, no explanatory
paragraph.

### Visual encoding

| Element | Encoding | Meaning |
|---|---|---|
| **Total Balance** | strong blue line (`--color-accent`, 2.5px), drawn last, on top — **authoritative, never clamped** | total portfolio value (`portfolio_value`) |
| **Contributions** | solid blue area (`--color-accent` @ 0.28), from the **$0 floor** up to `max(net_contributions, 0)` | the contributed capital still represented in the portfolio; withdrawals lower it, and it rests at $0 once everything contributed has been withdrawn |
| **Investment Gain** | solid green area (`--color-positive` @ 0.85) between the blue foundation and Total Balance, **clamped to ≥ $0** | where `Total Balance > displayed contribution foundation` |
| **Investment Loss** | solid red area (`--color-negative` @ 0.85) in the same band, **clamped to ≥ $0** | where `Total Balance < displayed contribution foundation` |
| **$0 baseline** | explicit 1px `--chart-axis` line, distinct from the gridlines | the **hard visual floor** every area rests on |

Investment Gain and Investment Loss are **mutually exclusive at every
point** and are **two separate legend entries** — never merged. Each
contiguous same-sign run is its own filled area.

### 1a. Authoritative data vs Overview display geometry

This is intentional and load-bearing:

| | Authoritative accounting data | Overview display geometry |
|---|---|---|
| `net_contributions` | may be **negative** (cumulative withdrawals > contributions) — **unchanged, never mutated** | drawn as `max(net_contributions, 0)` — the `displayBaseline` in `PortfolioGrowthChart` |
| contribution area | — | `$0 → displayBaseline`; **never below $0** |
| gain / loss areas | `investment_gain = portfolio_value − net_contributions` (server-side, `src/analytics/growth.py`) | the band between `displayBaseline` and Total Balance, both edges **clamped to ≥ $0**; **never below $0** |
| Total Balance line | `portfolio_value` | plotted verbatim, **not clamped** |

- **$0 is a hard visual floor** for the Overview contribution / gain / loss
  areas. No blue, green or red fill is ever drawn beneath the axis.
- This is a **presentation rule only**. `max(x, 0)` is display geometry,
  named `displayBaseline` — it never edits an API value, never changes
  backend contribution/withdrawal classification, never touches TWRR/XIRR.
- Because withdrawals are visually suppressed at the floor, the **displayed
  coloured areas no longer form the signed accounting identity** — and the
  chart deliberately makes no claim that they do (no "blue + green = total"
  labelling). The complete identity is available on Performance / in
  methodology.
- **No financial methodology has changed.** Only how the Overview draws.

### Withdrawals

A withdrawal lowers the blue contribution foundation. Once cumulative
withdrawals reach cumulative contributions the foundation sits at $0;
further withdrawals leave it at $0 (never below). No withdrawal markers on
Overview — that detail is on Performance.

### Net contributions classification

`net_contributions = cumulative external contributions + cumulative
external withdrawals` (withdrawals signed negative). Only transactions the
backend classifies as `DEPOSIT` / `WITHDRAWAL` count. The frontend does no
transaction classification and no aggregation.

### Selected period

Periods: `1M / 3M / 6M / YTD / 1Y / 3Y / 5Y / MAX`. Default **MAX** (the
long-term story is the point of this chart).

The full growth series is fetched once, unbounded, and sliced client-side
by date window (`sliceByPeriod` in `PortfolioGrowthSection.tsx`) — the
same convention every period-controlled chart in this app uses, so
switching periods never re-fetches. Picking a cutoff date is plain date
arithmetic, not a financial calculation.

**The contribution baseline is never re-based to zero at the start of the
visible window.** Each point's `net_contributions` is the authoritative
*cumulative* value the API computed for that date; a point outside the
window is simply not drawn. Selecting `1Y` does not imply $0 was
contributed at the start of the year.

- **YTD** = 1 January of the *current calendar year* through the latest
  available date — not "the last 12 months".
- Every period **gracefully clamps** to the earliest date the series
  actually has, rather than producing an empty chart when less history
  exists than the period asks for. `MAX` is always the full dataset.
- Capability-driven availability is inherited from the API's own period
  reporting; the frontend never hardcodes an unavailable period.

### Headline metrics

Plain investor language, sign-aware:

- **Contributed** · **Withdrawn** — when `OverviewPage` can pass the
  authoritative lifetime `total_contributed` / `total_withdrawn` (from the
  portfolio-overview endpoint it already fetches). `Withdrawn` shows the
  magnitude (a plain positive amount). Neither is coloured green/red — they
  are facts, not performance.
- **Investment gain** / **Investment loss** / **Investment gain/loss** —
  the label follows the actual sign of `investment_gain`; never
  "Investment gain −$X".
- **Total balance** — authoritative `current_value`.
- **Rate of return** — authoritative **time-weighted return since
  inception** (performance-periods endpoint), shown separately, never the
  `balance − contributions` residual as a percentage.

*API gap:* the growth-summary endpoint (`PortfolioGrowthSummary`) exposes
only `net_contributions`. When the lifetime split is unavailable the
headline falls back to a single **Net contributions** figure. Adding
`total_contributed` / `total_withdrawn` to `PortfolioGrowthSummary` would
let the section stand alone.

### Tooltip contract

```
DATE
Total balance        $X
Contributions        $Y        (or "Net contributed  -$Y" when the
Investment gain      +$Z         authoritative net figure is negative)
                                (or "Investment loss  $Z", unsigned)
```

Nothing else. No market/income breakdown, no beginning-balance
decomposition, no contribution-event detail, no TWRR/XIRR. When the
authoritative net-contribution figure for a point is negative the tooltip
labels it **Net contributed** and shows the number in plain language — it
never implies a blue area below the axis.

### Screen-reader wording

The `aria-live` announcement uses the same plain-language semantics:
"Investment loss $4,000" — never "Investment gain negative $4,000". A
negative net-contribution point is announced "Net contributed -$13,000".

### Legend contract

Always visible, never hover-dependent, responsive (wraps on narrow
screens). Swatch colours are defined once in `PortfolioGrowthSection`'s
`LEGEND_ITEMS` and must exactly match what `PortfolioGrowthChart` paints.

```
Total Balance   — strong blue line
Contributions   — solid blue fill
Investment Gain — solid bright green
Investment Loss — solid bright red
```

Plain words only — no "Net", no accounting terminology.

### No explanatory paragraph (Step 9A.2)

The paragraph that used to sit below the chart ("The blue area shows the
total amount you've invested, net of withdrawals…") was **removed**. A
chart that needs a paragraph explaining its geometry has failed the
simplicity goal; the legend and ordinary-language labels carry the
meaning. Methodology detail, if needed for auditability, belongs behind
the existing methodology affordance — not permanently under the chart.

### Data quality

Financial-sign colours (green gain / red loss) are kept strictly separate
from the data-quality, capability and reconciliation-status colour
vocabularies. Estimated data does not become green; unavailable data does
not become red. A null `portfolio_value` is a real gap — the balance line
and the gain/loss areas break there, never a fabricated zero.

### Accessibility

`role="group"` with an accessible name; an `aria-live` region announcing
the focused point's balance / net contributions / gain-or-loss; a
focusable overlay with a visible focus ring and left/right/Home/End
keyboard navigation (the Step 8 `useNearestPoint` convention, unchanged).
Gain vs loss is conveyed by the legend text and the tooltip label, not by
colour alone. Single `<h1>` hierarchy on the page is unaffected.

### Overview → Performance link

`View performance →` is a real `<Link>` to
`/performance?period=<mapped>`, carrying the current growth period
(`MAX → INCEPTION`, everything else 1:1). The Performance screen's
existing `useSelectedPeriod` consumes `?period=` unchanged. Browser
back/forward works because it is plain URL state.

### API contract

The Overview chart consumes the existing Step 9 endpoints — no new
endpoint was added:

- `GET /api/portfolio/growth` → `PortfolioGrowthPoint[]`
  (`date`, `portfolio_value`, `net_contributions`, `investment_gain`,
  `period_investment_gain`, `cash_flow_events`, …). The chart reads
  `portfolio_value`, `net_contributions` and `investment_gain`; it does
  not use `period_investment_gain` or `cash_flow_events`.
- `GET /api/portfolio/growth/summary` → `PortfolioGrowthSummary`
  (`current_value`, `net_contributions`, `investment_gain`, …).
- `GET /api/portfolio/performance/periods` → the inception TWRR for
  `Rate of return` (already fetched by `OverviewPage`).

---

## 2. Advanced Performance decomposition chart

`PerformanceDecompositionChart` — a `Card` titled **"Balance
decomposition"**, inserted **between "Performance history" and "Return
decomposition"** on `/performance`. Every pre-existing Performance section
is unchanged (see the section inventory in the Step 9A report).

### Purpose

The **detailed balance decomposition over time**. This is the analytical
chart that lived on `/` through Step 9: it moved to `/performance` in Step
9A when Overview took the pared-back wealth snapshot (§1) and Performance
kept the full version — a time series, not a single-period snapshot,
showing how the balance, the money put in, and the investment gain/loss on
top of it each moved across the selected window.

It answers "why did the balance move the way it did?" — a **dollar**
decomposition, never a rate of return. TWRR/XIRR remain the authoritative
performance measures in the existing Methodology section; the caption says
so explicitly.

### Visual encoding

The chart is the shared primitive
`components/charts/BalanceDecompositionChart`, wrapped by the feature
component in the standard `ChartLegend` + `ChartContainer` + `Chart |
Table` `Tabs`.

| Element | Encoding | Source field |
|---|---|---|
| **Total Balance** | strong blue line (`--color-accent`, 2.5px), drawn last | `portfolio_value` |
| **Contributions & Withdrawals** | faint blue area (`--color-accent-bg`) anchored to the zero baseline — fills up from 0 when positive, down from 0 when cumulative withdrawals exceed contributions | `net_contributions` |
| **Investment Gain / Investment Loss** | solid green / solid red areas anchored to zero, split into contiguous same-sign runs; an isolated single priced day renders as a narrow bar rather than vanishing | `period_investment_gain` |
| **Net Contributions reference line** | thin solid muted line (no dashes) | `net_contributions` |
| **Contribution / withdrawal markers** | dots on the line, green for a contribution, red for a withdrawal | `cash_flow_events` |
| **Zero baseline** | explicit `--chart-axis` line | — |

Investment Gain and Investment Loss are **two separate legend entries**,
never merged. The hover/keyboard tooltip (`useNearestPoint`, the Step 8
convention) shows the date, any cash-flow event's own amount, portfolio
value, net contributions, that period's gain/loss and the cumulative
investment gain — a contribution is never presented as investment return.

### Data

`GET /api/portfolio/growth` → `PortfolioGrowthPoint[]`
(`usePortfolioGrowth()`, the same unbounded series Overview fetches —
shared cache key, no extra request). `PerformancePage` passes it straight
through; the feature component only **slices** it to the selected window
(`windowStart`/`windowEnd` from the period's authoritative `start_date` /
`end_date` — plain date filtering, never a financial calculation) and
hands it to the primitive, which plots figures the backend computed. No
figure is built from arithmetic on two API fields.

### Views

- **Chart** — the time-series decomposition above.
- **Table** — the authoritative period **bridge** from `GET
  /api/portfolio/performance` (`usePerformanceOverview(start, end)` →
  `PerformanceOverview`): `Beginning balance`, `Contributions`,
  `Withdrawals`, `Net external flow`, `Investment return`, `Income (within
  investment return)`, `Ending balance` — every cell a verbatim field.

Toggled with a `Tabs` control (`Chart | Table`).

### Data states (Step 9A.1 — section always visible)

The section never collapses to a bare heading or `return null`:

- **Chart**, no valued history in the window (`portfolio_value` null on
  every point) → an explicit `UnavailableMetric` ("no valued portfolio
  history in this period yet"), section intact.
- **Table**, a window missing a boundary valuation (`opening_value` /
  `closing_value` null) → an `UnavailableMetric` ("no valuation on one of
  its boundary dates"); the percentage returns above are still available.
- **Loading** → `Skeleton`. **Error** → the `QueryBoundary` error state
  with Retry, inside the card. **Empty growth series** → the
  `QueryBoundary` empty message.

### Period behaviour

Responds to the existing Performance period selector (`useSelectedPeriod`,
`?period=`) — no second period control was introduced. Consumes the
`?period=` state the Overview link may set (`INCEPTION` = full series).

---

## 3. Known / deferred API gaps

- **Market gain/loss vs income, in dollars.** `PerformanceOverview` exposes
  the capital/income split only as *percentages* (`capital_return`,
  `income_return`) and the total `investment_gain` / `income` in dollars.
  The dollar split `market_gain_loss = investment_gain − income` is a
  derivation this frontend layer must not perform, so the decomposition
  Table shows the total investment return plus `income` (verbatim) and
  omits a separate market-gain-loss dollar figure. If that figure is
  wanted, `market_gain_loss` should be added to the `PerformanceOverview`
  API model server-side.
- **Per-period market gain/loss split on the chart.** The time-series
  chart's green/red areas are `period_investment_gain` — total investment
  gain/loss per period, not split into market movement vs income. Splitting
  it would need a per-period `period_income` field on `PortfolioGrowthPoint`.

---

## 4. Figma ↔ Storybook ↔ React

- **Figma:** unchanged. Both charts compose from existing chart primitives
  (`ChartContainer`, `Axis`, `Crosshair`, `ChartTooltip`, `useNearestPoint`,
  `Tabs`, `Table`, `UnavailableMetric`) and use only existing design
  tokens (`--color-accent`, `--color-accent-bg`, `--color-positive`,
  `--color-negative`, `--chart-axis`, `--chart-grid`). No new token was
  introduced. If a real mismatch with a frozen Figma contract is found it
  should be documented before Figma is touched — none was found.
- **Storybook:**
  - `Charts/PortfolioGrowthChart` (`PortfolioGrowthChart.stories.tsx`) —
    the Overview simple wealth chart: contributions + gain, contributions
    + loss, gain→loss crossover, zero gain/loss, large withdrawal,
    contributions withdrawn to zero, **net contributions below zero**
    (proves nothing is drawn below $0), fully divested, sparse history.
  - `Charts/BalanceDecompositionChart`
    (`BalanceDecompositionChart.stories.tsx`) — the Performance detailed
    chart: growth with contribution markers, drawdown below contributions,
    withdrawal markers, negative net contributions, sparse historical data.
  All fixture data is explicitly illustrative / test data.
- **React:** `PortfolioGrowthChart` (Overview), `PortfolioGrowthSection`
  (Overview), `BalanceDecompositionChart` (Performance chart primitive),
  `PerformanceDecompositionChart` (Performance feature wrapper: legend +
  container + Chart/Table toggle), `ChartLegend`.
