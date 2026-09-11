# Trade & cash timing model

Holdings answer "what do I own?" Cash answers "what settled money do I have?"
External cash flows answer "how much did I put in or take out?" These are three
different questions, and the engine keeps them structurally separate rather than
deriving one from another.

## The empirical finding

Before building this, I checked whether a real settlement gap exists in this
data — the statements print a nominal settlement date (T+2 to T+4) on every
trade, separate from the trade date. **It never governs when cash actually
moves.** Across all 76 trades in this portfolio's history, Vanguard's own **Cash
Account ledger** dates a trade's cash entry on the **trade date**, every time —
confirmed against the raw statement text, not just the parsed data:

```
11-Dec-2020 Buy transaction of VGS   2,529.60   2,592.46
30-Dec-2020 Buy transaction of VAF   1,100.40   4,191.93   ← this trade shows as
30-Dec-2020 Closing balance                       198.81      "Not yet settled" in
                                                               the OTHER table, but
                                                               is already reflected
                                                               here
```

The cash ledger's own footnote confirms this is deliberate: *"[the cash ledger]
excludes any unsettled ... transactions"* — if a trade genuinely hadn't cleared,
it wouldn't appear with a delayed date, it simply wouldn't appear at all yet.

**Consequence:** `settlement_date`, as printed in the investment-transaction
table, is exchange/registry metadata. It does not drive Vanguard's own cash
bookkeeping, and the engine must not use it to time a cash effect.

This is checked, not assumed — see `test_this_portfolios_history_has_no_pending_or_gapped_trades`
in [test_settlement.py](../tests/engine/test_settlement.py), which runs against
the real 76-trade history and would fail the moment this stopped being true.

## The model

**Two independent ledgers, reconciled through a shared trade.** A BUY/SELL and
its cash effect are represented as **two separate events**:

```
BUY        -- the security-ledger event. Changes units on trade_date.
TRANSFER   -- the cash-ledger event, for the same trade. Changes cash on its
              own date (which the empirical finding shows always equals the
              trade date, but is never assumed to).
```

This mirrors the "two ledgers reconciled through investment transactions"
framing directly: nothing derives the cash date from the trade's own fields,
because the trade's own fields (`settlement_date`) do not carry it.

## Authoritative dates

Every `Event` exposes two properties, both derived from what's already stored —
no new database columns, since nothing is genuinely different from what Phase 1
already extracted:

```python
event.effective_date        # always trade_date. The authoritative economic
                             # date for every type this model has: trade date
                             # for a trade, and trade_date already holds the
                             # cash-ledger's own date for everything else
                             # (deposit, withdrawal, dividend, fee, tax,
                             # interest) -- those types have no separate
                             # "trade" concept to distinguish it from.

event.cash_effective_date   # None for BUY/SELL/CORPORATE_ACTION (they have no
                             # direct cash effect -- see the paired TRANSFER).
                             # Their own trade_date for everything else.

event.cash_date              # cash_effective_date, non-optional. Raises if
                             # called on a BUY/SELL: there is no single cash
                             # date to return there, and guessing would
                             # silently reintroduce the settlement_date
                             # assumption this module exists to rule out.
```

`settlement_date` is retained on `BUY`/`SELL` purely as **provenance** — the
exchange-settlement date Vanguard printed — and is never read by `CashEngine`.

## Pending settlement

[`src/engine/settlement.py`](../src/engine/settlement.py) pairs every BUY/SELL
with the TRANSFER that carries its cash effect, matched by amount within a
tolerance. The match has to add the trade's fee back: a `BUY`'s `net_amount`
already includes brokerage, while the cash ledger books the principal and the
fee as two separate lines.

```python
pending_settlements(ledger)   # trades with no matching TRANSFER yet -- either
                               # genuinely still open (most recent statement),
                               # or a real gap this portfolio has never shown.
settlement_gaps(ledger)       # trades whose cash effect landed on a DIFFERENT
                               # date than the trade -- would mean the
                               # empirical finding above has broken.
```

Both are empty for the full imported history. `check_trade_settlement_pairing`
in [validation/checks.py](../src/validation/checks.py) runs this on every
import: a pending trade is `INFO` (may simply not have settled yet), a genuine
gap is `ERROR` (the settlement-timing assumption would need revisiting).

**No `pending_cash`/`available_cash` figure is added to portfolio value.**
Manufacturing one would imply a liability/receivable this data source has never
actually produced. If `settlement_gaps()` ever returns something non-empty,
that is the signal to build it — not before.

## External cash flows

Only `DEPOSIT` and `WITHDRAWAL` cross the portfolio boundary
(`EXTERNAL_FLOW_TYPES`). A same-day contribution funding a purchase is never
netted into one event — each keeps its own row, so the contribution is fully
visible to TWRR/XIRR:

```
Contribution   +$10,000
BUY            -$10,000
Net cash             $0
External flow  +$10,000     -- not $0
```

Reinvested distributions are not a second contribution, by construction: a
reinvestment is `DIVIDEND` (income) followed by `BUY`/`TRANSFER` (an ordinary
internal purchase), and `DEPOSIT` is never involved. Verified directly against
the spec's own worked example in
`test_dividend_reinvestment_is_not_a_second_contribution`.

## Same-day ordering

Events on one date apply in a fixed order (`TYPE_ORDER` in
[ledger.py](../src/engine/ledger.py)):

```
CORPORATE_ACTION → DEPOSIT → TRANSFER → BUY/SELL → DIVIDEND/DISTRIBUTION
→ INTEREST → TAX → FEE → WITHDRAWAL
```

Corporate actions first, so a same-day split changes the unit count a trade
then acts on. Deposits before trades, so contributed cash exists before it's
invested. Withdrawals last among cash movements. End-of-day valuation happens
outside this ledger, in the state engine, after every same-day event has
applied — so a same-day buy is already reflected in that day's closing value.

`CORPORATE_ACTION` was previously ordered after `BUY`/`SELL`; there are zero
corporate-action events in the current data, so this was a latent ordering
defect rather than an observed one, now covered by
`test_canonical_same_day_order`.
