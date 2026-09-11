# Historical dataset

Phase 3 turns the accounting engine's answers into a time series. It performs no
financial calculation of its own: it asks Phase 2 for state on each date and
records what comes back, along with how much that answer can be trusted.

```bash
./venv/bin/python -m src.cli rebuild-history          # full rebuild
./venv/bin/python -m src.cli rebuild-history --from 2024-01-01
./venv/bin/python -m src.cli history                  # summary
./venv/bin/python -m src.cli export-history --format csv
```

---

## The constraint that shapes everything

The statements quote prices on **24 dates across six years**. Cash,
contributions, withdrawals, income, fees and realised gains are exact on every
one of 2,123 days, because they come from the ledger. **Market value is not.**

Every row says which it is:

| Status | Meaning | Days |
| --- | --- | --- |
| `actual` | Vanguard reported this portfolio value for this date | 19 |
| `calculated` | units × a price quoted on this date | 76 |
| `estimated` | units × the most recent earlier price | 1,920 |
| `unavailable` | a holding exists with no price at or before this date | 108 |

On `unavailable` days `total_value` is **NULL, not zero**. A partial sum would
understate the portfolio while looking like a real figure. The gap stays visible.

Prices are carried forward, never interpolated, and never taken from a later
date. Every estimated row records the date its price came from.

---

## Two different drawdowns

This portfolio shows a **62% value drawdown in August 2024 on a day its
investments were at an all-time high** — because most of it had just been
withdrawn. Value-based drawdown cannot tell a withdrawal from a loss.

So both are recorded:

| Column | Measures | Use for |
| --- | --- | --- |
| `drawdown_pct` | portfolio value against its high-water mark | "how much is in the account versus its peak" |
| `return_drawdown_pct` | a flow-neutral growth index | "how far are my investments down" |

Drawdown **episodes** are detected on the index, because that is the question
people mean. The index is chained Modified Dietz between valuation dates, using
the same Phase 2 functions the performance figures use, and is flat in between.

The two real episodes are the 2022 bear market (−14.4%, Dec 2021 to Sep 2022,
recovered after 457 days) and a −8.1% dip in early 2026.

---

## Returns over standard windows

A window is only reported when the underlying valuations can actually measure
it. With quarterly pricing:

```
1D         n/a    both ends valued on 2026-06-30; no market movement observable
1M         n/a    nearest valuations span 91 days, too far outside the 30-day window
3M         TWRR  25.18%
1Y         TWRR  15.07%
INCEPTION  TWRR  89.07%    XIRR  9.00%
```

A window whose start falls between two valuations is **snapped to the nearest
valuation date** within a tolerance proportional to its length, and the
effective interval is reported. Without that, missing a quarter boundary by one
day would silently stretch a six-month measurement across nine months.

`INCEPTION` reproduces Phase 2 exactly (89.07% / 9.00%), which is the check that
the two layers agree.

---

## Tables

Daily rows are the canonical grain. Weekly, monthly, quarterly and yearly views
are **derived from them**, so a monthly figure always agrees with the days
inside it.

| Table | Grain |
| --- | --- |
| `portfolio_daily` | one row per day: value, cash, flows, gains, drawdowns, status |
| `holding_daily` | one row per security per day: units, price, allocation, asset class |
| `income_daily` | dividends, distributions and interest as paid |
| `period_summaries` | month, quarter and year summaries with TWRR and XIRR |
| `performance_periods` | 1D through since-inception |
| `drawdown_episodes` | peak, trough, recovery |
| `milestones` | thresholds, highs, largest movements |
| `history_runs` | what ledger each build came from |

Calendar summaries are materialised because they chain sub-period returns.
They carry a `granularity` column rather than living in three near-identical
tables.

**Asset classes are configured in `src/history/config.py`, not in the engine.**
How a portfolio is grouped for reporting is a presentation decision.

---

## Rebuilding

```bash
rebuild-history                    # everything
rebuild-history --from 2024-01-01  # only from that date
```

An incremental rebuild **must produce exactly what a full rebuild would**, and
is tested at several boundaries. Two things make that work, both of which were
bugs first:

- High-water marks are carried across the boundary from the last row before it.
  `MAX()` is deliberately not used — these are decimal strings, and SQL would
  compare them lexicographically, where `"9,999"` beats `"10,000"`.
- The growth index seeds its carry-forward from the last valuation *before* the
  window, or a partial rebuild would read as unpriced until the next valuation.

Derived tables always recompute from the complete series: a high-water mark
cannot be updated from a fragment.

`history_runs` records a fingerprint of the ledger each build came from, so
`is_stale()` can tell when new statements have been imported since.

---

## Reconciliation

Every date Vanguard reported a value is compared against the stored history,
adding back income declared but not yet received. **24 of 24 pass.** Nothing is
ever adjusted to match.

---

## Privacy

The historical tables hold financial data and internal IDs only. Exports are
scanned before writing and refuse to emit a column that looks like identity or
a description carrying an unredacted identifier.
