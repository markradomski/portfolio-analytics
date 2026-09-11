# Phase 4 — portfolio analytics

Phase 3 answers *what was my portfolio worth?* Phase 4 answers *why did it
change?* Nothing in this layer calculates a new financial fact — every figure
here reads from Phase 2 (the accounting engine) or Phase 3 (the historical
series). Where a genuinely new assumption was needed (a turnover convention, a
risk-free rate, a benchmark), it is named, configured in
`src/analytics/config.py`, and never buried inside a calculation.

```bash
./venv/bin/python -m src.cli analytics                 # summary report
./venv/bin/python -m src.cli analytics --year 2022
```

---

## Why quarterly risk metrics

Prices exist on 24 dates across six years. Computing "daily volatility" from
Phase 3's daily series — 92% carried-forward values — would report a number
with false precision: near-zero on every flat day, then an artificial spike
whenever a real price lands.

Every risk calculation (`volatility`, `sharpe_ratio`, `sortino_ratio`, `beta`,
`correlation`) operates on the **quarterly TWRR series** from Phase 3's
`period_summaries` — the finest frequency this data can honestly support,
since this portfolio's statements are themselves quarterly. `DAILY`/`WEEKLY`/
`MONTHLY` are supported by the config interface for a data source that has
real prices at that frequency; against this one, they report `UNAVAILABLE`
rather than a fabricated figure.

## Sharpe and Sortino need a risk-free rate you supply

`sharpe_ratio()`/`sortino_ratio()` report `UNAVAILABLE` until
`AnalyticsConfig.risk_free_rate_annual` is set. An assumed 0% is a real,
material choice — silently defaulting to it would misrepresent the ratio, not
simplify it.

## No benchmark is loaded by default

`beta()`/`correlation()`/`compare_to_benchmark()` report `UNAVAILABLE` until a
`Benchmark` is registered via `AnalyticsService.registerBenchmark()`. This
codebase has never integrated an external price feed — fabricating a
benchmark return with no real data would be worse than admitting there isn't
one.

**Benchmark caveats** (sec 23): `BenchmarkDefinition.return_methodology` is
`"price_return"` or `"total_return"`, and comparing the portfolio's total
return (income included) against a benchmark's *price* return (dividends
excluded) understates outperformance. `compare_to_benchmark()` detects this
mismatch and attaches an explicit note rather than comparing silently.

---

## Two double-counting bugs, both caught by building the reconciliation checks the spec required

Growth decomposition (sec 6) and security attribution (sec 7) must reconcile
to portfolio value exactly (sec 41, 42) — and building those checks found real
bugs, not edge cases:

**Brokerage subtracted twice.** Phase 2 capitalises brokerage into cost basis
(an acquisition cost) and nets it out of sale proceeds (a disposal cost) — the
correct accounting treatment, and already reflected in `realised_gain`/
`unrealised_gain`. `growth_decomposition`'s separate fee line must therefore
exclude trade brokerage and report only account-level fees, or a trade's
brokerage is deducted a second time. Confirmed on the real portfolio: **every
year from 2020–2026 now reconciles to the cent** (previously off by exactly
the year's brokerage total — $54.00 in 2024, $117.00 in 2023).

**A fee reversal treated as a second charge.** `Reversal:
OngoingAdminChargeByValue` is a credit (positive `net_amount`) refunding an
earlier charge. Summing `abs(amount)` per transaction before totalling turns
that credit into another debit instead of cancelling the original — $9.31
became $18.62 of "fees" instead of $0. Fixed by summing signed amounts first,
then taking the magnitude of the total.

Both are exercised as regression tests in
[test_attribution.py](../tests/analytics/test_attribution.py), alongside a
test that reconciles all seven years of the real portfolio and would fail the
moment either regressed.

## A third bug: opening cash silently defaulted to zero

`AnalyticsService` and several analytics functions constructed a fresh
`StateEngine` without seeding `opening_cash` — unlike `PortfolioService` and
`HistoryGenerator`, which read it from the earliest statement. This portfolio's
own opening cash happens to be $0 (it was observed from inception), so the gap
was invisible against real data; the synthetic test fixture (which opens on
$100) caught it immediately. Fixed by extracting the lookup into a single
shared `opening_cash_for()` helper (`src/engine/cash.py`) used everywhere a
`StateEngine` is constructed, rather than three separate copies drifting apart.

---

## Two return questions, and a third that only sounds like one

**TWRR** measures the investments, ignoring flow timing. **XIRR** measures
what the investor actually experienced, including it. Sec 4's own definitions
are returned as data by `getReturnMethodology()`, so a UI can display them
next to the figures instead of leaving the distinction implicit.

**Contribution efficiency is not a return.** `investment_gain /
net_contributions` doesn't account for *when* money arrived — mislabelling it
"return" would overstate performance for a portfolio funded late and
understate one funded early. `ContributionEfficiency` states its own
methodology explicitly rather than being called a return of any kind.

---

## A label almost lied about its own granularity

`best_worst_periods()`'s "day" bucket, built naively, reported a **91-day**
quarterly jump as `best_day: +25.18%`. The number wasn't wrong — the label
was. Fixed to check the actual gap between consecutive real valuations first:
when it exceeds a few days, `"day"` reports `unavailable` with the actual gap
stated, rather than implying daily-level precision the data doesn't have.

---

## What's honestly unavailable, and why

| Metric | Status | Reason |
| --- | --- | --- |
| Daily/weekly/monthly volatility | `UNAVAILABLE` | only quarterly prices exist |
| Sharpe / Sortino (default config) | `UNAVAILABLE` | no risk-free rate configured |
| Beta / correlation (no benchmark registered) | `UNAVAILABLE` | no external price feed integrated |
| Forward income yield | `UNAVAILABLE` | no distribution forecast in Vanguard statement data |
| Allocation by sector / geography / currency | `UNAVAILABLE` | Vanguard prints a product name and ticker only |
| Income growth decomposition (by cause) | not attempted | would need a counterfactual holding-and-rate breakdown the source data can't support |
| "Best/worst day" against quarterly pricing | `UNAVAILABLE` | consecutive valuations are ~90 days apart |
| Standard periods shorter than the pricing gap | `UNAVAILABLE` | would misrepresent a quarter's movement as a shorter window's |

Every one of these has an interface ready for the data that would unblock it —
a market-data price source, a configured risk-free rate, a registered
benchmark, security sector metadata — without touching a single calculation.

---

## Layout

```
src/analytics/
├── config.py         AnalyticsConfig -- every assumption, named
├── result.py         Metric / DataQuality -- the metadata envelope every figure carries
├── performance.py     overview, return methodology, standard periods (sec 3-5)
├── attribution.py     growth decomposition, security attribution, tree, reconciliation (sec 6,7,36,41,42)
├── contributions.py   contribution summary and efficiency (sec 8-9)
├── income.py           income by period/security/class, yield, growth (sec 10-12)
├── allocation.py       allocation, drift, concentration (sec 13-15)
├── trading.py           turnover, trading activity (sec 16-17)
├── gains.py             realised/unrealised gains, gain attribution (sec 18-20)
├── benchmark.py          portfolio-vs-benchmark comparison (sec 21-23)
├── risk.py               volatility, Sharpe, Sortino, beta, correlation, drawdown/HWM (sec 24-28)
├── rolling.py             rolling return/volatility/yield (sec 29)
├── calendar.py            calendar performance, best/worst, milestone context (sec 30-32)
├── costs.py               efficiency metrics, fees, tax (sec 33-35)
└── service.py             AnalyticsService -- the getX() façade (sec 37)
```

Every `getX()` on `AnalyticsService` maps to a section of the spec. Nothing
above `src/engine/` or `src/history/` performs a financial calculation of its
own — this layer packages, decomposes and labels what those two already
produced.

---

# Hardening pass (pre-Phase 5)

A dedicated validation pass before starting the frontend, per the principle:
Phase 4's job is to accurately communicate both what the portfolio knows and
what it doesn't. No new financial logic was introduced — every change either
adds metadata to an existing figure, tightens a semantic distinction, or
closes a gap in test coverage.

## Risk metric sample-size honesty

Every risk `Metric` now carries `observations`, `confidence`
(`HIGH`/`MEDIUM`/`LOW`/`NONE`), and `annualisation_factor` alongside
`data_quality`. A new `DataQuality.LIMITED` status marks a metric that is
technically computable but from a sample too small to trust as stable — below
12 quarterly observations, `volatility`/`sharpe_ratio`/`sortino_ratio`/`beta`/
`correlation` report `LIMITED` rather than `CALCULATED`, distinguishing "we
computed this, treat it as indicative" from "we computed this with
confidence." The real portfolio's 23 observations clear that bar (`CALCULATED`,
`MEDIUM` confidence).

## TWRR methodology metadata

`twrr_methodology_metadata()` states the method explicitly: `SUBPERIOD_LINKED`
(chained Modified Dietz between consecutive *real* valuations) rather than
true TWRR (which would revalue at every cash-flow date — this data source
can't, since valuations only exist where Vanguard priced the portfolio).
`cash_flow_adjustment_method` is `EXACT_DATED` — a flow is weighted by its
exact date within the sub-period it falls in, even though the valuation
bracketing that sub-period is not exact to that date. `cash_flow_observation_quality`
is `LIMITED` below 12 valuations, `SUFFICIENT` above.

Tested directly against the spec's own scenario: a $50,000 contribution
landing exactly halfway through a period with no valuation on that date. The
contribution is weighted by its exact date without ever requiring — or
fabricating — an intermediate valuation.

## Attribution reconciliation contract

`ReconciliationResult` now carries the spec's exact vocabulary —
`attributed_change`, `actual_change`, `residual`, `tolerance`,
`reconciliation_status` (`PASS`/`FAIL`/`LIMITED`) — with `reconciliation_status`
always *derived* from `residual` and `tolerance`, never set independently. A
result cannot claim `PASS` without `abs(residual) <= tolerance`; `LIMITED`
covers the case where a residual couldn't be computed at all (missing data),
distinct from a residual that was computed and failed. Old field names
(`.status`, `.difference`) remain as aliases so existing callers are
unaffected.

## Cash represented explicitly in the attribution tree

`attribution_tree()` previously folded interest income anonymously into the
generic income bucket, with no `"cash"` node at all. It now carries its own
entry (`interest_income`, `fees`, `profit`, `data_quality`), sourced from the
same profit-share `Contribution` the security figures already come from — cash
is a position, not an absence of one, and was never silently excluded from the
underlying calculation, only from how it was surfaced.

## "Other" vs "Unknown" — a real semantic bug, not just terminology

`classify()` returned `AssetClass.OTHER` both when a security was genuinely
unclassifiable *and* when it fell through the type fallback — collapsing "we
positively decided this belongs elsewhere" and "we have no idea" into one
label. Added `AssetClass.UNKNOWN` and changed every unclassified fallback
(ticker not mapped, security type not mapped) to use it. `OTHER` is now
reserved for an actual classification decision, which nothing in this
codebase currently makes — so every unmapped security correctly shows
`UNKNOWN`, not `OTHER`.

## Analytics capability registry

`getAnalyticsCapabilities()` — one call, 27 metrics, each an
`{available, reason}` pair checked against the dataset's actual state (not
assumed): valuation counts, transaction presence, configured risk-free rate,
registered benchmarks, sample-size floors. This is the single place Phase 5
should ask "can I show this chart" — it must never make that determination
itself.

## Data coverage model

`getDataCoverage()` returns `valuation_start/end`, `valuation_observation_count`,
`transaction_start/end`, `price_observation_count`, and a breakdown of
`actual`/`carried_forward`/`estimated`/`unavailable` observation counts. On the
real portfolio: 24 valuations, 2020-09-30 to 2026-06-30, 1,920 carried-forward
days out of 2,123 — exactly the numbers a UI needs to say "24 valuation
observations · quarterly data" instead of implying daily precision.

## Benchmark comparison detail

`BenchmarkComparison` now carries `benchmark_id`, `benchmark_name`,
`benchmark_return_method`, `benchmark_data_source`, `benchmark_frequency`, and
`benchmark_coverage` (paired observations actually used) — so a comparison
identifies *which* benchmark and *how much* of it was usable, not just that
one existed.

## API boundary, enforced structurally

`AnalyticsService._ledger_`/`_state_engine_` were renamed from public
properties to (double-underscore-marked) internal ones — nothing on the
service's public surface returns a raw `Ledger` or `StateEngine` object.
Added the exact `getX()` names sec 14 lists as aliases over the richer
existing names (`getContributions`, `getIncome`, `getRisk`, `getDrawdowns`,
`getMilestones`), plus a new `getPortfolioOverview()`. A structural test
(`test_api_boundary.py`) walks every public attribute and asserts none of them
is a `Ledger`/`StateEngine` instance.

## New regression coverage

- **Dedicated reinvestment test** (`test_reinvestment.py`): the full
  dividend→cash→reinvestment→units→later-gain chain, parametrised over both
  `DIVIDEND` and `DISTRIBUTION`, checking all seven points the hardening spec
  lists — income recognised once, cash recognised once, reinvestment not an
  external flow, no artificial return, units correctly affect later value,
  capital gain correct, total growth reconciles.
- **Determinism** (`test_determinism_and_precision.py`): 13 service methods
  called twice and compared for equality, plus a full import→rebuild→query
  cycle run twice from scratch.
- **Precision**: confirmed the PASS/FAIL reconciliation decision is made from
  full Decimal precision, never a pre-rounded display value; the real
  portfolio's reconciliation residuals carry more than 2 decimal digits,
  proving nothing was rounded along the way.
- **API boundary**: structural tests that the service exposes every required
  method and leaks no internal engine object.

## What remains honestly unavailable

Unchanged from the original Phase 4 pass — nothing here was invented to fill
a gap:

| Metric | Status | Reason |
| --- | --- | --- |
| Daily/weekly/monthly volatility | `UNAVAILABLE` | only quarterly prices exist |
| Sharpe / Sortino (no configured rate) | `UNAVAILABLE` | risk-free rate is not assumed |
| Beta / correlation (no benchmark) | `UNAVAILABLE` | no external price feed integrated |
| Forward income yield | `UNAVAILABLE` | no distribution forecast in source data |
| Sector / geography / currency allocation | `UNAVAILABLE` | no such metadata in Vanguard statements |
| Income growth decomposition by cause | not attempted | needs a counterfactual the data can't support |
