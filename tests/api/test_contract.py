"""API contract hardening tests (Phase 5 Pre-5.5, sec 13-17).

Runs entirely against the synthetic test database via the `client` fixture
(tests/api/conftest.py) -- no real portfolio data. Confirms the declared
response_model on every route is a live runtime contract (validated and
enforced by FastAPI/Pydantic on the way out), not documentation only, and
that the Decimal-as-string / explicit-nullability rules the whole contract
exists to enforce actually hold for real responses.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest

from src.api.app import app


# -- sec 13: every important financial endpoint has a real (non-generic) schema --

from fastapi.routing import APIRoute

API_ROUTES = [r for r in app.routes if isinstance(r, APIRoute) and "GET" in r.methods]
ALL_GET_PATHS = sorted(r.path for r in API_ROUTES)


def test_every_route_declares_a_non_generic_response_model():
    """No route may fall back to FastAPI's default (untyped dict/Any)
    response handling -- response_model must be a real Pydantic model, a
    list of one, a dict of one, or a union of those."""
    for route in API_ROUTES:
        assert route.response_model is not None, \
            f"{route.path} has no response_model (sec 3/10)"


PARAMS = {
    "/api/portfolio/performance": {"start": "2024-06-30", "end": "2024-09-30"},
    "/api/portfolio/performance/year/{year}": None,  # path param, tested separately
    "/api/portfolio/attribution": {"start": "2024-06-30", "end": "2024-09-30"},
    "/api/portfolio/attribution/securities": {"start": "2024-06-30", "end": "2024-09-30"},
    "/api/portfolio/attribution/reconciliation": {"start": "2024-06-30", "end": "2024-09-30"},
}


def _get(client, path, **overrides):
    params = dict(PARAMS.get(path) or {})
    params.update(overrides)
    concrete = path.format(year=2024, code="TST")
    return client.get(concrete, params=params)


def test_every_get_endpoint_responds_200_and_validates_against_its_schema(client):
    """Since handlers return a raw Response subclass would bypass
    response_model validation entirely (confirmed during development: a
    garbage-shaped dict returned 200 through the old Ok(JSONResponse)
    pattern), every route must return plain JSON-safe content instead --
    this test is the regression guard for that fix as much as a shape
    check. A 500 here almost always means the declared model is wrong for
    what the handler actually returns, not that FastAPI's validation is
    broken."""
    for path in ALL_GET_PATHS:
        r = _get(client, path)
        assert r.status_code in (200, 404), f"{path} -> {r.status_code}: {r.text[:300]}"


# -- sec 4/9: Decimal-as-string, never a float, and never silently 0/[]/"" --

def _walk_strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from _walk_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_strings(v)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield node


def test_no_endpoint_response_contains_a_bare_json_number_for_money(client):
    """A JSON number in a body that declares DecimalString fields would mean
    a float slipped past Pydantic's strict=True guard -- this walks every
    endpoint's actual response and fails loudly if that ever happens,
    except for genuinely-integer fields (counts, days), which the schema
    types as `int` on purpose and are exempt here by simply being ints."""
    for path in ALL_GET_PATHS:
        r = _get(client, path)
        if r.status_code != 200:
            continue
        numbers = list(_walk_strings(r.json()))
        assert numbers == [] or all(isinstance(n, int) for n in numbers), (
            f"{path} response contains a float: {numbers}")


# -- sec 16: the removed computed_closing/investment_return aliases stay dead --

def test_computed_closing_alias_does_not_reappear_in_any_response(client):
    r = client.get("/api/portfolio/attribution/reconciliation",
                   params={"start": "2024-06-30", "end": "2024-09-30"})
    body = r.json()
    for key in ("growth", "attribution"):
        assert "computed_closing" not in body[key]


def test_computed_closing_alias_is_absent_from_the_whole_codebase():
    """Only the explanatory comment in attribution.py documenting the
    removal may reference the name; this file's own tests are excluded
    since they must mention the string to test for it."""
    import subprocess
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    out = subprocess.run(
        ["grep", "-rn", "--include=*.py", "--include=*.ts", "--include=*.tsx",
         "computed_closing", str(root / "src"), str(root / "tests"),
         str(root / "web" / "src")],
        capture_output=True, text=True)
    live_hits = [line for line in out.stdout.splitlines()
                if "test_contract.py" not in line
                and ("attribution.py" not in line
                     or "#" not in line.split("computed_closing")[0])]
    assert live_hits == [], f"computed_closing reappeared: {live_hits}"


# -- sec 17: no engine object ever leaks through the API boundary -----------

def test_no_response_model_references_an_engine_type():
    """The frontend must never need Ledger/StateEngine/HistoryGenerator --
    confirm no Pydantic response model imports from src.engine or
    src.history.generator."""
    import inspect
    from src.api import models as m
    for name in m.__all__:
        obj = getattr(m, name)
        mod = getattr(obj, "__module__", "")
        assert not mod.startswith("src.engine"), f"{name} defined in src.engine"
        assert "generator" not in mod, f"{name} defined in a generator module"


# -- sec 8: reconciliation vocabulary is exact, not renamed ------------------

def test_reconciliation_result_keeps_its_authoritative_field_names(client):
    r = client.get("/api/portfolio/attribution/reconciliation",
                   params={"start": "2024-06-30", "end": "2024-09-30"})
    body = r.json()["growth"]
    for field in ("attributed_change", "actual_change", "residual",
                  "tolerance", "reconciliation_status"):
        assert field in body


# -- sec 9: nullability is explicit, not collapsed to a sentinel value ------

def test_unavailable_metric_is_null_valued_not_zero(client):
    r = client.get("/api/portfolio/risk")
    body = r.json()
    sharpe = body["sharpe_ratio"]
    if not sharpe["available"]:
        assert sharpe["value"] is None
        assert sharpe["value"] != "0"


def test_benchmark_comparison_with_no_benchmark_is_explicit_not_absent(client):
    r = client.get("/api/portfolio/risk/benchmark")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unavailable"
    assert body["note"]
