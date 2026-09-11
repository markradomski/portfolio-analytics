# API Contract

The HTTP API (`src/api/app.py`) is a read-only, thin translation layer over
`AnalyticsService`/`HistoryService` (Phase 4/3). It performs no financial
calculation of its own — every figure traces to Phase 2 (accounting) or
Phase 3 (historical series). This document covers the API contract itself:
response models, the Decimal/nullability rules the whole thing is built to
enforce, and how to regenerate the TypeScript client after a change.

## Response models

Every route declares a `response_model` from `src/api/models/` (Pydantic
v2), one module per family mirroring `src/analytics/`'s own layout:

| Module | Covers |
|---|---|
| `common.py` | Shared primitives: `DecimalString`, `ISODate`, closed enums (`DataQuality`, `Confidence`, `ValuationStatus`, `ReconciliationStatus`, `AssetClass`, TWRR methodology literals), `Metric`, `Capability`, `DataCoverage`, `ReconciliationResult` |
| `portfolio.py` | Overview, daily history point, holdings-on-a-date state |
| `holdings.py` | Holding row, allocation (point-in-time and history), concentration, unrealised gains snapshot |
| `performance.py` | Performance overview, standard periods, TWRR methodology |
| `income.py` | Income rows, growth, trailing/forward yield |
| `contributions.py` | Contribution summary and history |
| `attribution.py` | Security attribution, the attribution tree |
| `risk.py` | Risk metrics, drawdown analytics, high-water mark, benchmark comparison, rolling series |
| `history.py` | Calendar performance, best/worst periods, milestones, activity, health |
| `capabilities.py` | `AnalyticsCapabilities` |
| `gains.py` | Realised gains |

These are **serialisation contracts only** — no financial calculation lives
in `src/api/models/`. Every model is populated by validating the JSON-safe
dict `src/api/serialize.py`'s `to_json()` already produces from the
underlying Phase 2–4 dataclasses; Pydantic validates and describes that
shape for OpenAPI, it never recalculates it.

### Why handlers don't return a raw `Response`

Early in this hardening pass, routes returned a custom `Ok(JSONResponse)`
subclass. That was found to make `response_model` pure documentation:
**FastAPI skips response-model validation entirely when a handler returns a
`Response` subclass directly** — a deliberately broken shape sailed through
as a 200. Handlers now return `Ok(content)`, a plain function that runs
`content` through `to_json()` (Decimal → str, date → isoformat, Enum →
value, dataclass → dict) and returns the resulting JSON-safe
dict/list/primitive. FastAPI then validates and re-serialises that value
against the route's declared `response_model` for real. `tests/api/
test_contract.py::test_no_response_model_references_an_engine_type` and the
schema-validation smoke test in the same file both regression-guard this.

## Decimal-as-string

Every financial value is transported as `DecimalString` — `Annotated[str,
StringConstraints(strict=True)]`. Pydantic's `strict=True` on a `str` field
rejects a `float`/`int` at validation time instead of silently coercing it.
If a float ever leaks into a money field (a serialisation regression), the
endpoint now returns a `500 ResponseValidationError` instead of quietly
rounding the value through IEEE754 on the way to the frontend. This is the
one rule the whole contract exists to enforce.

## Nullability

`null` (genuinely unavailable/not computable), `0` (a real zero), `[]` (an
empty but real collection), and `"unavailable"`/`"UNAVAILABLE"` (a status
value) are distinguishable and never collapsed into one another:

- A `Metric` always carries `available: bool` and `reason: str | None` —
  availability is never inferred from `value` being `null`.
- `Capability` is the same: `available`/`reason`, always present.
- `AllocationResult.status` is `"unavailable"` (with `weights`/
  `allocation_pct` entirely absent) for a dimension the source data can't
  support, never an empty-but-present dict.
- `BenchmarkComparison` with no benchmark registered returns
  `status: "unavailable"` and a `note`, not an absent/empty object.

## Performance: custom range vs standard periods

`GET /api/portfolio/performance?start=&end=` (`overview_for_range`) and
`GET /api/portfolio/performance/periods` (`standard_periods` →
`performance_periods`) must agree for an identical `[start, end]` window. Both
now:

- **Anchor the opening to the nearest date the portfolio was genuinely valued
  on** (`index_as_at == date`), within a tolerance proportional to the window,
  falling back to the most recent priced row at/before `start`. The portfolio
  is only priced on ~quarterly Vanguard valuation dates, and carry-forward from
  one valuation expires before the next arrives — so the days immediately
  before a quarter-end valuation are routinely unpriced gaps. Taking the row
  *strictly* before `start` with no fallback (the old `overview_for_range`
  behaviour) produced `opening_value: null`, `total_return: null`, and a TWRR
  measured from a stale carried-forward index.
- Measure returns from that anchor date with Modified Dietz (`total_return`,
  `capital_return`, `income_return`), the index ratio (`twrr`), and dated cash
  flows (`xirr`) — the exact functions in `src/engine/returns.py`.

The custom-range endpoint additionally reports dollar figures (`opening_value`,
`closing_value`, `contributions`, `withdrawals`, `investment_gain`, `income`,
`fees`); the periods endpoint reports only ratios. Regression coverage:
`tests/analytics/test_performance_consistency.py`.

## OpenAPI and TypeScript generation

Regenerate both after any `src/api/models/` or `src/api/app.py` change:

```bash
./venv/bin/python -c "import json; from src.api.app import app; \
  json.dump(app.openapi(), open('web/openapi.json', 'w'), indent=2)"
cd web && npx openapi-typescript openapi.json -o src/api/schema.generated.ts
```

`web/src/api/types.ts` is a thin alias layer on top of
`schema.generated.ts`'s `components["schemas"]` — one `export type X =
Schemas["X"]` per response model, keeping the names the rest of the
frontend already imports stable across a regeneration. Presentation-only
types that don't correspond to an API response (e.g. chart-internal marker
types) stay defined where they're used, never in `types.ts`.

Note: a Pydantic model only appears in `components.schemas` if some route's
`response_model` actually references it. `DrawdownEpisode` exists in
`risk.py` for `HistoryService.drawdown_history()`'s row shape but has no
route surfacing it yet, so it is not currently generated or aliased in
`types.ts`.

## API adapter architecture

`web/src/api/client.ts`, `portfolio.ts`, and `analytics.ts` are the only
place `fetch()` is called. Every function maps 1:1 to one endpoint, typed
against `types.ts`. No aggregation, calculation, or independent
availability logic happens in the adapter or anywhere else on the frontend
— a screen that needs a figure this layer doesn't expose gets a new
endpoint here, backed by an existing or new Phase 2–4 function, never a
calculation added client-side. `getAnalyticsCapabilities()` remains the
single source of truth for whether a metric/period/chart can be shown; the
frontend must never recreate that decision with an ad hoc rule.

## Runtime validation on the frontend

Evaluated adding a schema-validation library (e.g. zod) on top of the
generated TypeScript types and decided against it for now: the backend
already validates every response against its Pydantic `response_model`
before it leaves the server (see above), so a client-side re-validation
step would duplicate that guarantee rather than add a new one, for real
API traffic. The place it would earn its cost — catching drift between
`schema.generated.ts` and what the server actually sends — is exactly what
`web/src/api/__tests__/contract.test.ts` and the backend's own contract
tests already do at the fixture level. Revisit if the frontend ever talks
to an API instance this project doesn't control end-to-end.

## Contract testing

- `tests/api/test_contract.py` (backend): every GET route declares a
  non-generic `response_model`; every endpoint returns 200 against the
  synthetic fixture and validates against its declared schema; no response
  contains a bare JSON number where a `DecimalString` is declared; the
  removed `computed_closing`/`investment_return` aliases stay dead across
  `src/`, `tests/`, and `web/src/`; no response model references an
  `src.engine`/`src.history.generator` type; the reconciliation vocabulary
  (`attributed_change`/`actual_change`/`residual`/`tolerance`/
  `reconciliation_status`) is present verbatim; unavailable metrics are
  null-valued, not zero.
- `tests/api/test_app.py` (backend): status codes, Decimal-as-string over
  the wire, capability/coverage/reconciliation shape checks, ordering,
  and 422 on an invalid query param.
- `web/src/api/__tests__/contract.test.ts` (frontend): captured synthetic
  fixture responses (`web/src/api/__fixtures__/*.json`, built from
  `tests/fixtures/synthetic.py` only — never real portfolio data) checked
  against the field names `types.ts` declares, so a renamed/removed
  backend field is caught rather than silently breaking the UI.

## Regenerating after a model change — full checklist

1. Edit the Pydantic model(s) in `src/api/models/`.
2. Update the route's `response_model=` in `src/api/app.py` if the model
   changed shape.
3. `./venv/bin/python -m pytest tests/api/` — confirm the handler's actual
   return value still validates.
4. Regenerate `openapi.json` and `schema.generated.ts` (commands above).
5. `cd web && npx tsc --noEmit` and `npm run build` — confirm nothing that
   consumes the changed type breaks.
6. Update any hand-written fixture in `web/src/api/__fixtures__/` that the
   change affects, and re-run `npx vitest run`.
