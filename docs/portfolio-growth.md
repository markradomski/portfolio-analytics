# Portfolio Growth — Data & Performance Engine (Step 9)

Step 9's brief asked for a "canonical portfolio data model" with clearly
separated ingestion/normalisation/calculation/API/UI layers. That
architecture already existed, built in Phases 1-4 and re-verified rather
than rebuilt this step:

```
src/ingestion/     -- PDF/CSV → parsed documents (statement_parser.py,
                      tax_report_parser.py, pdf_parser.py, importer.py)
src/normalisation/ -- parsed documents → canonical records (transactions.py,
                      securities.py, values.py)
src/models/        -- the canonical model itself (Transaction, Holding,
                      PortfolioValuation, IncomeEvent, StatementPeriod,
                      Provenance, ...) -- Transaction and PortfolioValuation
                      are already two separate dataclasses (sec 2: "a
                      transaction is not a valuation")
src/engine/        -- portfolio calculations (ledger.py, cash.py,
                      costbasis.py, holdings.py, reconciliation.py,
                      returns.py, attribution.py, state.py)
src/history/       -- the daily time series (generator.py, service.py,
                      store.py) -- src/history/schema.py's own comment:
                      "Daily rows are the canonical grain"
src/analytics/     -- performance calculations (performance.py, risk.py,
                      contributions.py, gains.py, income.py, growth.py [new])
src/api/           -- the API/data contract (app.py routes, api/models/)
web/src/           -- UI visualisation only, renders calculated data
```

Step 9's actual new work was narrower than "build the architecture": add
one new analytics module (`growth.py`) that assembles the Portfolio Growth
dataset from data every layer above it already computes, expose it over
three new API routes, and build the redesigned primary chart. No backend
calculation this step invents a new financial concept -- every number in
`growth.py` is either read directly from `portfolio_daily` (Phase 3) or one
of two subtractions Step 9 itself defines (see `src/analytics/growth.py`'s
own docstring).

## 1. Canonical portfolio data model (confirmed, not rebuilt)

`src/models/__init__.py` already separates every concept Step 9 asks for:

| Concept | Type |
|---|---|
| Portfolio | implicit (one `Account` + its `Transaction`/`Holding`/`PortfolioValuation` history) |
| Account | `Account` |
| Holding | `Holding` (point-in-time position) |
| Transaction | `Transaction` (`TxnType`: BUY/SELL/DIVIDEND/DISTRIBUTION/INTEREST/DEPOSIT/WITHDRAWAL/FEE/TAX/TRANSFER/CORPORATE_ACTION/OTHER) |
| Valuation | `PortfolioValuation` -- a **separate dataclass**, never conflated with a transaction |
| Cash | `CashEngine` (src/engine/cash.py) over the ledger's DEPOSIT/WITHDRAWAL/TRANSFER events |
| Contributions/Withdrawals | `TxnType.DEPOSIT` / `TxnType.WITHDRAWAL` -- first-class transaction types, not derived |
| Purchases/Sales | `TxnType.BUY` / `TxnType.SELL` |
| Dividends/Distributions | `TxnType.DIVIDEND` / `TxnType.DISTRIBUTION` |
| Fees | `TxnType.FEE` |

Every record carries a `Provenance` (`document_id`, `page`,
`extraction_method`) — see §6.

## 2. Cash-flow model (confirmed, not rebuilt)

Contributions and withdrawals are already first-class ledger events
(`TxnType.DEPOSIT`/`WITHDRAWAL`), each with a date, amount, account, and
description — exactly the sec-3 shape. Net contributions was already
computed centrally, in two independent places that agree by construction:

```
src/history/generator.py  → portfolio_daily.cumulative_contributions / cumulative_withdrawals (running totals)
src/analytics/contributions.py → ContributionSummary.net_contributed = total_in + total_out
```

`withdrawals` are stored **signed negative** throughout this codebase
(confirmed in `src/history/generator.py`, `contributions.py`, and every
existing `ContributionHistoryRow`/`ActivityRow`) — so `net_contributions =
cumulative_contributions + cumulative_withdrawals` is arithmetically
identical to the spec's "contributions − withdrawals", just consistent
with the sign convention every other screen in this app already uses.
`growth.py` documents this explicitly rather than silently flipping a sign.

## 3. The Portfolio Growth dataset (new: `src/analytics/growth.py`)

```python
GrowthPoint:
    date, portfolio_value, contributions, withdrawals,
    net_contributions, investment_gain, cash_flow_events

GrowthSummary:
    current_value, net_contributions, investment_gain, growth_pct, as_at

ReconciliationCheck:
    date, subject, calculated, source, difference, tolerance, status
```

`portfolio_growth(history, repo, start=None, end=None)` reads
`HistoryService.portfolio_history()` (Phase 3's own daily series, arbitrary
date range already supported) and derives, per day:

- `contributions`/`withdrawals` — that day's own delta of the cumulative
  fields (not running totals) — reuses the exact bucket-delta pattern
  `HistoryService.contribution_history()` already used for yearly buckets,
  applied at daily granularity.
- `net_contributions` — the running total (see §2).
- `investment_gain` — `portfolio_value − net_contributions`, `None`
  whenever `portfolio_value` is `None` (a valuation gap is never papered
  over with a fabricated gain).
- `cash_flow_events` — that day's own DEPOSIT/WITHDRAWAL transaction rows,
  each carrying its own `transaction_id` (provenance, §6).

`portfolio_growth_summary()` does not recompute anything — it re-reads
`contributions.py`'s own `ContributionSummary`/`ContributionEfficiency`
(`gain_per_dollar_contributed` is deliberately *not* called a return; see
that module's own docstring) and reshapes the result.

`growth_reconciliation()` wraps `src/engine/reconciliation.py`'s existing
`Reconciler` — the same engine that already checks calculated portfolio
value/cash against Vanguard's own reported statement figures per date —
filtered to the two subjects relevant to a growth screen (`"portfolio
value"`, `"cash"`; per-security unit checks are Holdings' own concern).

## 4. API contract

```
GET /api/portfolio/growth?start=&end=          -> PortfolioGrowthPoint[]
GET /api/portfolio/growth/summary?as_at=       -> PortfolioGrowthSummary
GET /api/portfolio/growth/reconciliation       -> PortfolioValueReconciliationCheck[]
```

Response models: `src/api/models/growth.py` (`CashFlowEvent`,
`PortfolioGrowthPoint`, `PortfolioGrowthSummary`,
`PortfolioValueReconciliationCheck`), following this project's existing
`DecimalString`-over-the-wire convention (money is transported as an exact
string, never a JSON number) rather than the spec's literal
`number`-typed TypeScript interfaces — adapted to this project's
established precision rule, not copied verbatim (sec 12 explicitly asks
for this adaptation).

Frontend: `portfolioApi.growth/growthSummary/growthReconciliation`
(`web/src/api/portfolio.ts`) and `usePortfolioGrowth` /
`usePortfolioGrowthSummary` / `usePortfolioGrowthReconciliation`
(`web/src/hooks/api/usePortfolioApi.ts`) — one thin wrapper per endpoint,
same convention as every existing hook.

## 5. Reconciliation

`growth_reconciliation()` surfaces, per statement date:

```
calculated   -- what the ledger's own state computes for that date
source       -- what Vanguard's statement reported
difference   -- calculated − source
status       -- PASS | FAIL | SKIP (SKIP = nothing to compare, e.g. no
                reported cash balance on that particular statement --
                distinct from FAIL, a real discrepancy)
```

Never silently adjusted to match — a `FAIL` is returned as data, not
hidden (verified in `tests/analytics/test_growth.py`'s discrepancy case).

## 6. Data provenance

Every `CashFlowEvent` carries its own `transaction_id`, traceable through:

```
source PDF (src/ingestion/) → Transaction (src/normalisation/, src/models/)
   → ledger event (src/engine/ledger.py) → portfolio_daily row
   (src/history/) → GrowthPoint.cash_flow_events (src/analytics/growth.py)
   → CashFlowEvent (API) → the chart's own tooltip/live-region text (UI)
```

The same `transaction_id` the existing `/api/portfolio/activity` endpoint
already surfaces for that transaction — a user (or developer) can cross-
reference a chart event back to the exact transaction row.

## 7. Provider boundary (confirmed, not rebuilt)

`src/ingestion/` already isolates statement parsing (Vanguard PDF
quarterly/tax reports today) from everything downstream:
`src/normalisation/` and `src/models/` know nothing about PDFs, Vanguard,
or any particular source format — they only know the canonical
`Transaction`/`Holding`/`PortfolioValuation` shapes. `src/engine/`,
`src/history/`, `src/analytics/`, and this step's `growth.py` all operate
purely on that canonical model. A future CSV importer or a different
broker's statement format would add a new module under `src/ingestion/`
that produces the same canonical dataclasses — nothing in `growth.py` or
any layer above it would change.

## 8. The Portfolio Growth chart (frontend)

`web/src/components/charts/PortfolioGrowthChart/` — a new chart component
(the redesigned primary visualisation), composed from existing chart
primitives (`Axis`, `Crosshair`, `ChartTooltip`, `useNearestPoint`), not a
new chart-rendering framework:

- **Portfolio Balance** — the dominant series (thick, `--color-accent`).
- **Net Contributions** — a solid, subtle reference line
  (`--color-text-muted`, thinner), always rendered, never behind a toggle.
- **Investment growth fill** — one consistent light-blue area
  (`--color-accent` at low opacity) between the two curves. The fill uses
  a single `d3.area` with `y0`/`y1` set to the two series' values
  regardless of which is numerically larger, so an underwater stretch
  (balance below net contributions) renders the same fill the other way
  around rather than breaking the chart — no signed positive/negative
  colour split, and no third "growth" line.
- **Contribution/withdrawal markers** — small circles at each cash-flow
  date (green = contribution, red = withdrawal), distinct from the fill.
- **Keyboard + hover** — the same Step 8 `useNearestPoint` convention
  (arrow-key navigation, `aria-live` announcement, visible focus ring)
  used by every other time-series chart in this app.
- **Tooltip** — date, portfolio value, net contributions, investment gain,
  plus that date's own contribution/withdrawal amount when present.

`web/src/features/overview/PortfolioGrowthSection.tsx` wraps the chart with
the period selector and the four-metric summary row (Portfolio value / Net
contributions / Investment growth / Growth above contributions).

### Period selector: 1M / 3M / 6M / YTD / 1Y / 3Y / 5Y / MAX

The growth series is fetched once, unbounded, and sliced client-side by
period (`sliceByPeriod`, exported for direct unit testing) — the same
"fetch once, slice locally" convention `usePortfolioHistory`/Performance's
period selector already use, so switching periods never re-fetches.
Picking a cutoff date is plain date arithmetic (never a financial
calculation): `1M`/`3M`/`6M`/`1Y`/`3Y`/`5Y` count back from the series' own
last date; `YTD` starts 1 January of the *current calendar year* (not "the
last 12 months"); every period gracefully clamps to the earliest date the
series actually has rather than producing an empty chart when less
history exists than requested. **`MAX` is the default** — the portfolio's
full growth story is the point of this chart. `Tabs`' existing
`overflow-x: auto` (already present for exactly this reason, per its own
comment) keeps all 8 period buttons usable on narrow screens via
horizontal scroll rather than wrapping.

## 9. Testing

- `tests/analytics/test_growth.py` (14 tests) — a small, fully controlled
  synthetic ledger (hand-built via `Repository.upsert_*`, bypassing PDF
  parsing entirely since it's irrelevant to this module) with known
  contribution/withdrawal dates and amounts: single/multiple contributions
  on different dates, a withdrawal after contributions, net-contributions
  and investment-gain formula verification against independently
  hand-computed figures, cash-flow-event provenance, arbitrary date-range
  requests, full-period historical correctness (no gaps), reconciliation
  (both a perfectly-reconciled case and a deliberately discrepant one), and
  an explicit guard that a large contribution is never presented as
  investment return.
- `tests/api/test_app.py` (+5 tests) — the three new routes' shapes,
  precision, and arbitrary-date-range behaviour.
- `web/src/components/charts/PortfolioGrowthChart/__tests__/` (10 tests) —
  no fabricated zero on a valuation gap, distinct contribution/withdrawal
  markers, the single light-blue fill (not a signed colour), the fill
  still rendering when the balance is underwater, the solid (non-dashed)
  reference line, balance-line visual dominance, keyboard navigation
  surfacing the same figures a hover would, and event amounts never folded
  into investment gain.
- `web/src/features/overview/__tests__/sliceByPeriod.test.ts` (10 tests) —
  every period's cutoff math, including YTD's calendar-year-boundary
  behaviour (via a mocked system clock) and graceful clamping when less
  history exists than the requested period.
- `web/src/features/overview/__tests__/PortfolioGrowthSection.test.tsx`
  (6 tests) — summary rendering, the unavailable `growth_pct` case, MAX as
  the default selected tab, all 8 periods present with no `All` option,
  and period-switching updating the selected tab.

Full suite: 352/352 backend (14 new), 245/245 frontend (30 new), clean
`tsc`, clean production build, clean `oxlint` on every file this step
touched.

## 10. What was deliberately not changed

- No backend/financial-calculation change beyond `growth.py`'s two
  documented subtractions — Phases 1-4's engine, history, and analytics
  layers are unchanged.
- No new chart-rendering framework or D3 pattern — `PortfolioGrowthChart`
  reuses `Axis`/`Crosshair`/`ChartTooltip`/`useNearestPoint` exactly as
  every other chart in this app does.
- `AllocationChart`/`TimeSeriesChart`/`AllocationHistoryChart`/
  `DrawdownChart`/`BarChart` are untouched.
- The Figma design system is unchanged; no Figma tool was invoked.
