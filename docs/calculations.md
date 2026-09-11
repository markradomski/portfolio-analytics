# Calculations

Every figure the engine reports, and exactly how it is produced. Where a
calculation is an approximation, the reason is stated rather than hidden.

Configuration lives in `src/engine/config.py`. Defaults: AUD, average cost,
event-frequency valuation, 2dp rounding, $0.05 reconciliation tolerance,
returns net of fees.

---

## Conventions that everything else depends on

**A trade appears twice in the source data.** The investment table records it on
the **trade date**, with an amount already **net of brokerage**. The cash ledger
records the same trade on the **settlement date**, at **gross**, with brokerage
as a separate `FEE` row.

The engine therefore reads each side for exactly one purpose:

| | Source | Date used |
| --- | --- | --- |
| Holdings, cost basis, realised gains | `BUY` / `SELL` rows | trade date |
| Cash balances and flows | `TRANSFER` + `FEE` rows | settlement date |

Using both sides for either double-counts brokerage on every trade. This is
asserted by `test_brokerage_is_not_deducted_twice`.

**External versus internal.** Only `DEPOSIT` and `WITHDRAWAL` cross the
portfolio boundary. Everything else moves money inside it. A deposit is never
performance, and a withdrawal is never a loss.

**Opening cash.** The ledger is seeded with the earliest statement's opening
balance. Reconstructing from zero would understate cash permanently for any
statement set that does not begin at inception. It is zero for this portfolio,
which opened within the first statement period.

---

## Holdings

**Definition.** Units of each security held on a date.

**Formula.** `closing = opening + purchased − sold + corporate actions`

**Inputs.** `BUY`, `SELL`, `CORPORATE_ACTION` events, applied in ledger order.

**Dates.** Trade date, matching the statements: a trade placed before period end
appears in that period's holdings even when it settles afterwards.

**Missing data.** A sale exceeding units held disposes of what is held and
reports the excess rather than going negative.

---

## Cost basis

**Definition.** What the currently held units cost.

**Methods.** Configurable, both implemented:

- **Average cost** — all units share one pooled cost per unit. Default.
- **Tax lot** — FIFO parcels, each keeping its own acquisition cost.

**Fees.** Brokerage paid on acquisition forms part of what the units cost, since
`BUY.net_amount` is already gross plus brokerage.

**Limitation.** Neither is a tax calculation. Australian CGT requires
identifying the actual parcels disposed of, so **average cost must never be
reported as a tax position**. That belongs in a separate tax module built on the
tax-lot method.

---

## Realised and unrealised gains

```
realised_gain   = proceeds − allocated_cost        (on disposal)
unrealised_gain = market_value − remaining_cost_basis
unrealised_pct  = unrealised_gain / remaining_cost_basis
```

**Zero-cost holdings** return `None` for the percentage rather than infinity or
NaN — units received without consideration have no cost to divide by.

---

## Valuation

```
portfolio_value = Σ (units × price) + cash
```

**Prices.** Quarter-end closing prices printed on the statements — about 23
dates across six years. Today's price is never used to value a historical date.

**Every value is labelled with how it was obtained:**

| Quality | Meaning |
| --- | --- |
| `reported` | Vanguard stated the figure directly |
| `calculated` | units × a price actually quoted on that date |
| `estimated` | units × the most recent earlier price |
| `unavailable` | no price at or before that date |

Prices are carried forward, never interpolated and never filled from a later
date. A portfolio's quality is the weakest among its holdings.

**Reconciliation adds a third term.** Vanguard's reported portfolio value also
includes *income declared but not yet received*, which sits in neither holdings
nor cash. Comparisons against reported figures add it back; the engine's own
`total_value` does not include it.

---

## Cash

```
opening + deposits + income + sale proceeds
        − purchases − withdrawals − fees − taxes = closing
```

Keyed on settlement date. `BUY`/`SELL` rows are excluded (see conventions).

---

## Income

**Tracked.** Dividends (companies), distributions (ETFs and funds), interest
(cash account). Classification follows the security type.

**Franking credits** come from the annual tax reports, which state them at two
different grains — and the difference is not cosmetic:

| Source | Grain | Result |
| --- | --- | --- |
| Dividends (companies) | per payment, with ex date | attached to the individual income event |
| Trust distributions (ETFs, funds) | annual total per security | held per security per financial year |

Distributions carry no payment dates in the tax report, so their credits cannot
be attributed to individual payments and are never split up to look as if they
could be.

**Matching.** A tax report row is matched to an income event on security and
amount, within a seven-day window — the statements and the tax reports disagree
about payment dates by a day or two. A row matching nothing, or more than one
event, is left alone and reported as `TAX_DIVIDEND_UNMATCHED`.

**Franking credits are not cash.** They are a tax offset. `gross_income` is what
reached the account; `grossed_up_income` adds the credits and is what the ATO
assesses. Keeping them apart is why the cash reconciliation still balances.

**Self-checking.** Each report states both its breakdown and its totals, so they
validate each other: a row the parser missed appears as a shortfall against the
stated total.

**Still absent.** Ex dates exist only for dividends, never for distributions.

---

## Return decomposition

```
capital_growth = realised_gain + unrealised_gain
income         = dividends + distributions + interest
total_gain     = capital_growth + income − fees
```

Fees are deducted because Vanguard reports "return after withholding tax and
fees"; netting them off is what makes the numbers comparable. Configurable via
`returns_net_of_fees`.

Percentages use **average capital** — the mean of each sub-period's Modified
Dietz denominator — so contributions do not distort the base.

---

## Time-weighted return (TWRR)

**Question answered.** How did the investments perform, ignoring when money was
added or removed? This is what you compare against a benchmark.

**Formula.** Modified Dietz within each sub-period, chained across sub-periods:

```
r_period = (V_end − V_begin − F) / (V_begin + Σ wᵢFᵢ)
wᵢ       = (days remaining after flow i) / (days in period)
TWRR     = Π (1 + r_period) − 1
```

**Why Modified Dietz.** True TWRR revalues the portfolio at every external cash
flow. That needs a price on each flow date, and only quarter-end prices exist.
Modified Dietz weights each flow by the fraction of the period it was invested
for, which is the standard approximation when valuations are periodic. **It is
exact when no flows occur mid-period.**

**Unmeasurable periods** return `None` rather than zero, so "flat" is
distinguishable from "no capital at risk", and are skipped when chaining.

**Known limitation.** Measurement starts at the first date the portfolio can be
valued (2020-09-30), not the first transaction (2020-09-07). Return earned in
that opening gap is not captured, because there is no valuation to measure from.

---

## Money-weighted return (XIRR)

**Question answered.** What did the investor actually earn, given when they put
money in and took it out?

**Formula.** The rate at which the dated cash flows net to zero:

```
Σ CFᵢ / (1 + r)^(daysᵢ/365) = 0
```

**Sign convention** is the investor's: money paid in is negative, money received
positive, and the closing portfolio value is a final receipt.

**The opening value is included as an outflow** at the start of the window.
Without it, contributions made before the first valuation date would be missing
while the gains they produced still counted — which overstated this portfolio's
return by more than nine percentage points before it was fixed.

**Solved by bisection**, not Newton's method: bisection cannot diverge and takes
the same steps for the same input, which keeps the engine deterministic. Returns
`None` when flows run in only one direction, since no rate solves that.

**TWRR and XIRR are not interchangeable.** For this portfolio TWRR annualises to
11.71% while XIRR is 9.00%; the gap is the cost of contribution timing.

---

## Attribution

```
contribution_i = profit_i / average_capital
profit_i       = realised + unrealised + income − fees
```

Because the parts of profit sum to the whole, **contributions sum exactly to the
portfolio return** — there is no residual. Cash is treated as a position: it
earns interest and pays the account fees.

**Limitation.** This is a profit-share attribution, consistent with the
money-weighted return, not the time-weighted one. It answers "how much money did
VAS make for this portfolio", which is a different question from "how did VAS
perform". A Brinson decomposition into allocation and selection effects needs
benchmark weights and belongs with the benchmark work.

---

## Reconciliation

Calculated figures are compared against Vanguard's reported ones at every
reported valuation date: portfolio value, cash balance, and units per security.
Differences beyond `reconciliation_tolerance` ($0.05) are reported with both
numbers.

**Nothing is ever forced to match.** A discrepancy is output, not corrected.

Current status: **201 of 201 checks pass**.

---

## Determinism

Same inputs and configuration always produce the same output. The engine reads
no clock, no live price and no random source, and event ordering is fully
determined by `(date, type, id)` rather than by database row order — asserted by
shuffling the input in `test_result_does_not_depend_on_input_ordering`.

---

## Rounding

Money and units are `Decimal` throughout, and stored as exact decimal strings.
No rounding is applied inside calculations; `rounding_precision` governs
presentation only. Cost basis is cleared to exactly zero when a position closes,
so rounding dust cannot accumulate.

---

## Privacy

The engine requires no investor name, account number or address, and none exists
in the dataset it reads. Securities and accounts are internal IDs throughout.
