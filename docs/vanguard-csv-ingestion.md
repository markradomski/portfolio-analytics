# Vanguard structured CSV ingestion (Step 9B)

> **Status: Stage 5 MVP release complete.** Reconciled CSV data is promoted
> into the active accounting projection running the real application.
> Stages 6–7 (full historical/analytics migration audit, import-run
> orchestration) remain deferred. The real-data reconciliation report this
> stage produced lives only in the private development repository, since it
> narrates figures from a real account.

## Stage 5 — privacy fix: Deposit descriptions could carry a bank name or initials

`redact()` only strips digit runs. A cash-CSV Deposit row's description can
read `"Off-System BSB Direct Entry Deposit - <source>"` where `<source>` is
a free-text bank name or the investor's own initials — alphabetic, so
`redact()` never touched it, and both were found in this real export.
`sanitise.strip_deposit_source()` now drops the whole trailing `" - ..."`
clause on Deposit rows specifically (applied in `cash.py`, both to the
`CashSourceRecord.product_name` used downstream and to the
`sanitised_cells` diagnostic copy) — the sending bank/person is never an
economic fact the ledger needs. Withdrawal rows are unaffected (their
destination clause was already digit-redacted and the date within it is
useful reconciliation evidence). Regression-tested against the real export.

## Stage 5 — reproducing the promotion

```
# 1. snapshot the current (PDF-only or previously-promoted) ledger
cp data/processed/portfolio.db data/processed/portfolio.pre-csv-promotion.db

# 2. parse, match, build candidates, reconcile, and (only if
#    promotion_ready) promote -- see build_promotion_plan / apply_promotion
#    in src/ingestion/vanguard_csv/promote.py for the exact sequence

# 3. rebuild history and re-verify through the existing CLI
python -m src.cli rebuild-history --db data/processed/portfolio.db
python -m src.cli analyse --db data/processed/portfolio.db --out data/processed
```

`portfolio.pre-csv-promotion.db` is the local, gitignored baseline the
guarded real-data tests in `tests/ingestion/vanguard_csv/` promote against,
so they keep validating against a genuine "before" state even once
`portfolio.db` itself is the already-promoted release artifact.

## Stage 4 correction to the fee model (supersedes the Stage 1 profile above)

Stage 1 read the cash CSV's 49 `Fees and Charges` rows as uniformly
`OngoingAdminChargeByValue`. That was materially wrong. Inspecting the rows
themselves (Stage 4) shows three distinct kinds, told apart by `Product
Name`:

| `Product Name` | Count | `CashClass` | Meaning |
|---|---|---|---|
| `OngoingAdminChargeByValue` | 18 | `ADMIN_FEE` | quarterly account admin fee |
| `... Transaction fee for <security> <Buy\|Sell>` | 30 | `TRADE_BROKERAGE_CASH` | **trade brokerage** — the cash leg of the investment CSV's `Brokerage` column |
| `Reversal: OngoingAdminChargeByValue` | 1 | `FEE_REVERSAL` | explicit fee reversal/refund |

**Brokerage is a separate cash-CSV row, not absent.** Stage 2's finding that
`abs(cash Buy/Sell Total) == investment Value` (brokerage excluded from the
*trade* cash amount) still stands — brokerage settles as its **own** row,
matched to its trade by security name + side + a date window + exact
amount, and becomes a standalone `FEE` candidate
(`source_semantic=TRADE_BROKERAGE`) linked via
`TradeCandidate.brokerage_fee_id`. All 30 real brokerage rows matched 30/30.

`TradeCandidate` gained `net_amount`, following the rule found in the PDF
ledger itself (not fabricated): `BUY net = gross + brokerage`,
`SELL net = -(gross - brokerage)` — the cost-basis/proceeds convention the
existing engine already uses for PDF-derived trades.

## Stage 3 — canonical candidates + idempotent staging

`build_candidates(match, investment_records, cash_records, resolver) → CandidateSet`
renders the two exports in the app's own `TxnType` vocabulary as **candidates**
— never written to `transactions`, never promoted over the PDF ledger, no
accounting rule changed. `StagingStore.stage()` holds them by canonical id.

### Source identity vs canonical economic identity (§14)

- **source identity** = `SourceRef(kind, file_sha256, row_number, raw_type, …)`
  — one sanitised Vanguard row.
- **canonical economic identity** = `sha256` of economic fields + a group
  ordinal — one economic event. A matched trade's canonical id derives from
  the *agreed* economics of **both** sources, not either row number, and never
  from a filename, account number or timestamp.

### BUY / SELL construction

One `MatchedTradeCandidate` → **one `TradeCandidate`** (never a BUY plus a
separate cash transaction; the candidate set contains **zero** `TRANSFER`
rows). Investment CSV is preferred for existence / type / security / trade
date / units / price / gross value / brokerage; cash CSV for the signed
`cash_effect` and `cash_effective_date`. `trade_date` and `cash_effective_date`
are kept as distinct fields even though all 76 real trades are same-day.

### Gross value vs cash effect vs brokerage (§4)

Three distinct fields, never merged: `gross_amount` (investment `Value`),
`cash_effect` (signed cash CSV `Total`, proven `== ∓gross`), `raw_brokerage` /
`canonical_brokerage`. **Brokerage is not folded into `cash_effect`**, and no
`net_amount` is fabricated — the engine read-model leaves `net_amount=None` on
BUY/SELL so the engine applies its own `abs(units×price)` rule. Brokerage's
cash/accounting treatment is a Stage 4B/5C question.

### Brokerage preservation

`SOURCE_VALUE` → `canonical_brokerage` = the source value. Blank →
`canonical_brokerage = 0.00`, `raw_brokerage = None`,
`brokerage_source_status = SOURCE_BLANK_INTERPRETED_AS_ZERO`, and the
provenance `SourceRef.raw_brokerage` is the literal string `"null"` — the
"source blank" vs "source observed zero" distinction is never lost.

### Deposit reversal candidates (§6)

Positive `Deposit` rows → ordinary `DEPOSIT` candidate,
`classification_status = CLASSIFIED`. **Negative `Deposit` rows** →
`type = DEPOSIT` (raw type kept), signed amount kept,
`classification_status = NEEDS_RECONCILIATION`,
`source_semantic = DEPOSIT_REVERSAL_CANDIDATE`. Not a withdrawal, not counted
as contributed capital, not netted — Stage 4A decides.

### Income normalisation (§8)

`Distribution` rows are normalised by canonical security type
(`classification_method = SECURITY_TYPE_NORMALIZATION`): a listed company/share
→ `DIVIDEND`, an ETF/fund → `DISTRIBUTION`, via the existing
`income_type_for()`. Security is resolved by `Product ID` when present, else by
the long name through a table seeded from the investment CSV's own
name↔code pairs (same export, same account) and the repo securities table — no
fuzzy matching. Unresolvable → `UNRESOLVED_SECURITY`, never guessed.
**Real data: 86 → 15 DIVIDEND (RIO/BHP/WTC) + 71 DISTRIBUTION (ETFs), 0
unresolved** — the split is derived, not hardcoded, and matches the PDF ledger.

### Interest / fees

`Interest` → `INTEREST` (already in `TxnType`; no schema change). Negative
`Fees and Charges` → `FEE`. **Positive `Fees and Charges`** → `type = FEE`,
sign kept positive, `NEEDS_RECONCILIATION`,
`source_semantic = POSITIVE_FEE_CANDIDATE` (rebate/refund/adjustment — Stage 4B).

### Idempotency, overlap, corrections (§17–19)

`StagingStore` is keyed on canonical id — a re-stage of the identical set is a
no-op (recognised by id, not a DB constraint). A wider later export
re-recognises shared events and adds only new ones. A candidate that occupies
the same economic *slot* (`type` + `security` + `date`) as a staged event but
with a changed financial field is flagged `SOURCE_CHANGED`, keeps **both**
provenances, and links `supersedes` — never a silent overwrite. Full
supersession/versioning is deferred to the Data Lifecycle step.

### Staging vs authority

Stage 3 produces candidates only. The PDF-derived ledger remains the
persisted canonical authority; CSV is not globally promoted. `engine_projection.py`
builds a throwaway in-memory `Ledger` from candidates alone to prove they are
consumable by the *existing* `HoldingsEngine` / `CashEngine` — it drops the 6
`NEEDS_RECONCILIATION` events and adds no opening balance, so its cash figure
is deliberately not the reconciled closing cash (Stage 5).

## Stage 2 — deterministic cross-file BUY/SELL matching (`trade_match.py`)

`match_trades(investment_records, cash_records)` pairs each `InvestmentSourceRecord`
with the cash CSV's `Buy`/`Sell` row for the same economic trade. It builds **no
canonical transactions**, does not read the ledger, and does not promote source
authority — Stage 2 is evidence only.

**Matching fields, strongest first:** normalised side (BUY↔`Buy`, SELL↔`Sell`)
→ `Product ID` (must be equal when both present; long name is confirmation, and
the fallback only when the cash side has no `Product ID`) → gross value
(`abs(cash Total)` vs investment `Value`, cent tolerance) → trade date
(cash date within a ±5-day window; the delta is always recorded) → quantity
(`abs(cash Units)` vs canonical units, when the cash side carries units).

**Gross-cash semantics.** The cash match amount is `abs(cash Total)` vs the
investment `Value` (the gross consideration). **Brokerage is never part of the
comparison** — the matcher does not look for `Value ± Brokerage`. `raw_brokerage`
(may be `None`), `canonical_brokerage` and `brokerage_source_status` ride along
on the candidate for Stage 3; the cash accounting treatment of brokerage is a
Stage 4B/5C question.

**Determinism.** Inputs are sorted by a stable economic key before matching;
candidate selection is set-based; a source row wanted by more than one row on
the other side is `AMBIGUOUS` for everyone involved — never resolved by row
order, filename, timestamp or account field. Re-running on reordered input
gives the identical result (`match_id`s included).

**One-to-one.** A successful match consumes exactly one record on each side;
`assert_one_to_one()` enforces uniqueness of matched rows. Two genuinely
identical same-day same-size trades with two identical cash legs are
`AMBIGUOUS` (the source gives no way to bind leg to order) — and ambiguity
blocks promotion.

**Match classifications:** `MATCH`, `MATCH_WITH_MINOR_DIFFERENCE` (value within
tolerance but not exact, or a non-zero date delta), `UNMATCHED_INVESTMENT`,
`UNMATCHED_CASH`, `AMBIGUOUS`, `VALUE_MISMATCH`, `DATE_MISMATCH`,
`SECURITY_MISMATCH`, `QUANTITY_MISMATCH`. Detailed `match_reasons` are kept
separately from the primary `status`.

**Match identity:** `sha256("TRADEMATCH" | side | product_id | trade_date |
units | gross_value | cash_date | cash_total | group_ordinal)[:16]` — a one-way
digest of sanitised economic fields, never a row number / filename / account
number. (A hash prefix can contain incidental digit runs; like every ID column
it is exempt from the free-text identifier scan.)

**Real-data result (current exports):**

| | value |
|---|---|
| investment side | BUY 52 / SELL 24 |
| cash side | BUY 52 / SELL 24 |
| matched | BUY 52 / SELL 24 / **76 total** |
| unmatched / ambiguous / security / quantity / value mismatch | **0 / 0 / 0 / 0 / 0** |
| date relation | **all 76 SAME_DAY** (max \|delta\| 0 days) |
| gross value | **all 76 exact** (max residual 0.00) |
| one-to-one | ✓ |

The two exports describe the **same 76 economic trades**. **GO** for Stage 3.

## Stage 1 — privacy-safe CSV parsers (`src/ingestion/vanguard_csv/`)

`parse_investment_csv()` and `parse_cash_csv()` produce **sanitised source
records** (`InvestmentSourceRecord` / `CashSourceRecord`) — not canonical
transactions. `sanitise.redact()` is the single choke point: it replaces every
non-date run of 4+ digits with `#`, and the `Account number` column is dropped
before any record exists. File identity is `sha256` of the sanitised,
account-free rows — never the filename.

Every input row becomes either a record or a `QuarantinedRow` (unknown type,
bad date, bad numeric, zero quantity, sign mismatch). `assert_all_rows_accounted()`
enforces `rows_in == records_out + quarantined`. Nothing is silently dropped.

**Real-data parse (current exports):** investment 76/76 records, 0 quarantined,
0 warnings (BUY 52 / SELL 24; brokerage 46 blank→zero, 30 source-value). Cash
295/295 records, 0 quarantined, **6 sign-anomaly warnings** — 5 `Deposit` rows
with a *negative* `Total` and 1 `Fees and Charges` row with a *positive*
`Total`. These are reversed/dishonoured entries; they are kept (flagged, not
dropped) and are the first leads for the Stage 4A deposit-count investigation
(PDF 34 vs CSV 31). PII survivors across all parser output: **0**.

## Purpose

Migrate the portfolio's *preferred* transaction source from PDF text
extraction to Vanguard's structured CSV exports, **without touching** the
accounting engine, historical engine, analytics, API or frontend. Only the
`src/ingestion` → `src/normalisation` → canonical-ledger boundary changes.

PDF ingestion is **retained** as an independent reconciliation / fallback
source.

## Supported Vanguard exports

Two local CSV exports, referred to generically throughout as:

| Generic name | Contents | Row count (current export) |
|---|---|---|
| **investment transactions CSV** | Buy/Sell order execution history | 76 data rows |
| **cash transactions CSV** | cash-account ledger: deposits, withdrawals, buy/sell cash effects, distributions, interest, fees | 295 data rows |

The account-number-bearing filenames are **never** repeated in code, logs,
tests, fixtures or documentation.

## Privacy rules (enforced, tested — §45)

Account-identifying data present in the source, and how it is handled:

| Location | Field / pattern | Handling |
|---|---|---|
| investment CSV | `Account number` column | **dropped at parse time** — never read into a record |
| cash CSV | `Withdrawal` description: `"One-off Cash Withdrawal to <dest-acct> on <date>"` | destination account digits **redacted** before storage; keep `"One-off Cash Withdrawal"` + the date |
| cash CSV | `Deposit` description: `"Off-System BSB Direct Entry Deposit - <ref>"` | reference digits **redacted**; keep `"Off-System BSB Direct Entry Deposit"` |
| filenames | account number in filename | never persisted; file identity is a **content hash of the sanitised rows**, not the filename |

Sanitisation rule: in any free-text description carried into a record, every
run of 4+ digits that is **not** part of a recognised `dd-Mon-yyyy` date is
replaced with `#`. Transaction identity never includes the account number,
the filename, a row number alone, or an import timestamp.

## Source profile — investment transactions CSV

Columns: `Account number` (dropped), `Investment`, `Product ID`,
`Product Type`, `Trade Date`, `Type`, `Unit Price`, `Quantity`, `Value`,
`Brokerage`.

| Property | Finding |
|---|---|
| Date format | `dd-Mon-yyyy` (e.g. `18-Sep-2020`) |
| Date coverage | 2020-09-18 → 2026-05-01 |
| `Type` vocabulary | `Buy Trade` (52), `Sell trade` (24) — note inconsistent casing |
| `Product Type` | `ETF` (70), `Share` (6) |
| `Product ID` | always present: `VAS VGS VGAD VAF VGE BHP RIO WTC` |
| `Quantity` sign | **BUY > 0, SELL < 0** (52 pos, 24 neg) |
| `Unit Price` / `Value` | plain decimal, no currency symbol, no thousands separator |
| `Value` | positive on both buy and sell (gross trade value, unsigned) |
| `Brokerage` | `9` (30 rows) or **blank** (46 rows). Blank spans the early ETF purchases; `9` appears from the later Share trades. **Blank ≠ 0** — see below. |
| Malformed rows | none detected |
| Duplicates | none (no two rows share type+security+date+units+value) |

## Source profile — cash transactions CSV

Columns: `Date`, `Type`, `Product Type`, `Product Name`, `Product ID`,
`Units`, `Total`.

| Property | Finding |
|---|---|
| Date format | `dd-Mon-yyyy` |
| Date coverage | 2020-09-11 → 2026-07-02 |
| `Type` vocabulary | `Distribution` (86), `Buy` (52), `Fees and Charges` (49), `Interest` (35), `Deposit` (31), `Sell` (24), `Withdrawal` (18) |
| `Product Type` | `Cash account` (133), `Share` (92), `ETF` (70) |
| `Product ID` | present on trades/distributions for the 8 known tickers + `CASH`; **blank on 86 rows** (all `Distribution` rows — distributions are identified by `Product Name` only) |
| `Units` | present only on `Buy`/`Sell` (76 rows); blank on the other 219 |
| `Total` sign | **credit > 0, debit < 0**: Deposit/Sell/Distribution/Interest positive; Withdrawal/Buy/Fees negative |
| `Product Name` | for trades/distributions: the security's long name (`"Rio Tinto Limited"`, `"Vanguard Australian Shares Index ETF"`); for cash events: a description string (see privacy table) |
| Fees | `Product Name` = `OngoingAdminChargeByValue` (all 49) — an **account admin fee**, not trade brokerage (see fee reconciliation) |
| Malformed rows | none detected |

## The dual-source relationship (§10)

Every economic trade appears in **both** files:

```
investment CSV  "Buy Trade"/"Sell trade"  (76 rows)  → the TRADE (units, price, security, brokerage)
cash CSV        "Buy"/"Sell"              (76 rows)  → the CASH EFFECT of that trade
```

These must be **joined into ONE canonical `BUY`/`SELL`**, carrying provenance
from both source rows. The cash CSV `Buy`/`Sell` rows must **never** become
independent transactions.

Baseline cross-check against the existing PDF-derived ledger (which already
models this split): PDF ledger has **BUY 52 / SELL 24** and **76 `TRANSFER`
rows** (the cash legs) — an exact structural match to the two CSVs.

## Transaction mapping

### investment transactions CSV → canonical trade

| CSV | Canonical | Notes |
|---|---|---|
| `Type` `Buy Trade` (case-insensitive) | `TxnType.BUY` | |
| `Type` `Sell trade` | `TxnType.SELL` | |
| `Quantity` | `units` = `abs(Quantity)`; raw signed value kept in provenance | existing ledger stores unsigned units + type |
| `Unit Price` | `price` | |
| `Value` | `gross_amount` | validated against `abs(units) × price` within rounding tolerance (§7) |
| `Brokerage` blank | `fees = None` (**unavailable**, not 0) | |
| `Brokerage` `9` | `fees = Decimal("9")` | |
| `Trade Date` | `trade_date` | holdings change here |
| `Product ID` | `security_id` via existing `normalise_code` + securities table | |

### cash transactions CSV → canonical cash events

| CSV `Type` | Canonical `TxnType` | `external_cash_flow` | Notes |
|---|---|---|---|
| `Deposit` | `DEPOSIT` | **true** | external capital in — not investment return |
| `Withdrawal` | `WITHDRAWAL` | **true** | external capital out — not investment loss |
| `Distribution` | `DISTRIBUTION` (ETF/fund) or `DIVIDEND` (Share) | false | split by security type via existing `income_type_for`; matches the PDF ledger's 71 DISTRIBUTION + 15 DIVIDEND = 86 |
| `Interest` | `INTEREST` | false | cash-account interest income |
| `Fees and Charges` | `FEE` | false | account admin fee |
| `Buy` | **cash side of canonical `BUY`** — joined, not a new txn | — | |
| `Sell` | **cash side of canonical `SELL`** — joined, not a new txn | — | |

## Trade matching algorithm (§11)

Deterministic join between investment-CSV trade rows and cash-CSV `Buy`/`Sell`
rows. Match key, strongest first:

1. `type` (BUY↔Buy, SELL↔Sell)
2. `security_id` (investment `Product ID` ↔ cash `Product ID`, both present on trades)
3. `abs(units)` exact
4. trade gross value: investment `Value` ≈ `abs(cash Total)` within $0.01 × units rounding tolerance
5. date proximity: cash `Date` within a small window of investment `Trade Date` (T+0..T+2)

- Multiple candidates → **`AMBIGUOUS`**, not silently resolved.
- No candidate → **`UNMATCHED`** (investment-only or cash-only), imported with a quality flag.
- The account number is never a matching key.
- Row order is never a matching key.

Reported statistics: matched / unmatched-investment / unmatched-cash /
ambiguous / value-mismatch / date-mismatch / security-mismatch.

## Trade date vs cash date (§12)

`trade_date` (from investment CSV) drives holdings. `cash_effective_date`
(from cash CSV `Date`) drives cash. Both are preserved on the canonical
trade. They are **not** collapsed even when equal. If settlement semantics
cannot be proven from the data, `timing_quality` records the uncertainty.

## Brokerage semantics (§8, §30)

- `Brokerage` blank on 46/76 investment rows. Blank spans exactly the early
  ETF purchases (Vanguard's brokerage-free ETF platform era); `9` appears on
  later Share trades. This is consistent with "blank = genuinely no brokerage
  charged" — **but the export does not state that**, so blank is stored as
  `fees = None` (UNAVAILABLE) and the reconciliation layer confirms it against
  statements rather than the importer assuming `0`.
- The cash CSV `Fees and Charges` rows are all `OngoingAdminChargeByValue` —
  a periodic percentage-of-value admin fee, **distinct** from trade brokerage.
  No double-count: trade brokerage lives on the trade (`fees`), admin fees are
  their own `FEE` transactions. Confirmed by description + amount + cadence.

## Distribution → security mapping (§16)

Cash-CSV `Distribution` rows have a blank `Product ID` and identify the
security by `Product Name` only. Deterministic mapping:
`Product Name` → canonical security via a name/alias table seeded from the
`Investment` column of the investment CSV (which pairs long name ↔ ticker)
and the existing securities table. No fuzzy matching. Unmappable →
`security_id = None` + quality flag; never a guessed security, never a
duplicate security row.

## Provenance (§20)

Every CSV-derived canonical transaction carries:
`source_type=VANGUARD`, `source_document_type` (`INVESTMENT_TXN_CSV` /
`CASH_TXN_CSV`), `extraction_method=STRUCTURED_CSV`, sanitised `source_row`,
`source_transaction_type` (raw Vanguard label), `import_run_id`,
`imported_at`, `quality`, `reconciliation_status`. Joined trades carry
**both** `investment_csv_source_row` and `cash_csv_source_row`.

## Transaction identity & idempotency (§21, §37, §38)

Stable fingerprint from non-PII economic fields:

- **trades**: `hash(type, security_id, trade_date, units, price, gross_amount)`
- **cash events**: `hash(type, effective_date, amount, security_or_description_slug)`
- a per-document ordinal disambiguates genuinely identical same-day rows
  (same approach the PDF parser already uses)

Consequences: re-importing the same export is a no-op; a later wider-range
export (2020–2027) re-matches existing fingerprints and adds only new rows;
file identity is `content_hash(sanitised rows)`, independent of filename.

Corrections (a re-exported row with changed economics) are **detected and
recorded**, not silently overwritten — full supersession/versioning is
deferred to the Data Lifecycle step (§39).

## Import workflow (§57)

```
python -m src.cli import-csv statements/ --db data/processed/portfolio.db
```

One command: profiles both CSVs, imports investment + cash, runs the
trade-matching join, reconciles against the existing PDF-derived ledger,
rebuilds history + analytics, and writes a sanitised reconciliation report.
PDF import (`python -m src.cli import`) is unchanged.

## Known limitations / deferred

- Correction supersession/versioning — deferred to Data Lifecycle step.
- Full import-run orchestration — minimal run model only.
- `market_gain_loss` dollar split — unrelated API gap (Step 9A).
- Automated Vanguard sync — explicitly out of scope (§60).

## Implementation plan (stages)

| Stage | Deliverable |
|---|---|
| **0 ✅** | source profiling, frozen baseline, this contract |
| 1 | `src/ingestion/vanguard_csv/` — deterministic parsers for both CSVs (+ sanitisation), synthetic fixtures, parser tests |
| 2 | normalisation → canonical candidate events; trade-matching join; `STRUCTURED_CSV` provenance; dual-source trade test (§48) |
| 3 | idempotent import into the repo; file-hash reimport detection; overlapping-export test (§47) |
| 4 | CSV ↔ PDF event reconciliation layer + classifications (§23, §49) |
| 5 | rebuild security + cash ledgers through the **existing** engine; per-security + cash + external-flow + income + fee reconciliation (§25–30) |
| 6 | quarter-end statement reconciliation (§31); old-vs-new ledger comparison (§32); analytics before/after (§41, §55) |
| 7 | `import-csv` CLI command; privacy tests (§45); docs finalised; real-data run (§50–54) |
