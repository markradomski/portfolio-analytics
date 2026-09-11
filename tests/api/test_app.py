"""The HTTP API: correct status codes, precision preserved over the wire,
and every endpoint reachable without touching src.engine/src.history from
the test's own perspective (mirroring how the frontend must consume it)."""

from decimal import Decimal


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_missing_database_returns_503(monkeypatch, tmp_path):
    from src.api import app as app_module
    monkeypatch.setattr(app_module, "DB_PATH", tmp_path / "nonexistent.db")
    from fastapi.testclient import TestClient
    client = TestClient(app_module.app)
    r = client.get("/api/portfolio/overview")
    assert r.status_code == 503


def test_overview_returns_expected_shape(client):
    r = client.get("/api/portfolio/overview")
    assert r.status_code == 200
    body = r.json()
    assert "current_value" in body
    assert "data_coverage" in body


def test_decimal_precision_is_preserved_as_a_string_not_a_float(client):
    """A float would silently round; the API must send the exact string the
    accounting engine produced."""
    r = client.get("/api/portfolio/performance",
                   params={"start": "2024-06-30", "end": "2024-09-30"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["contributions"], str)
    assert Decimal(body["contributions"]) == Decimal("500.00")


def test_capabilities_expose_available_and_reason(client):
    r = client.get("/api/portfolio/capabilities")
    body = r.json()
    for name, cap in body.items():
        assert "available" in cap
        assert isinstance(cap["available"], bool)
        if not cap["available"]:
            assert cap["reason"], f"{name} is unavailable with no reason given"


def test_unavailable_risk_metric_returns_structured_reason_not_a_number(client):
    r = client.get("/api/portfolio/risk")
    body = r.json()
    sharpe = body["sharpe_ratio"]
    assert sharpe["value"] is None
    assert sharpe["available"] is False
    assert sharpe["reason"]


def test_reconciliation_status_is_present_and_consistent(client):
    r = client.get("/api/portfolio/attribution/reconciliation",
                   params={"start": "2024-06-30", "end": "2024-09-30"})
    body = r.json()
    for key in ("growth", "attribution"):
        result = body[key]
        assert result["reconciliation_status"] in ("PASS", "FAIL", "LIMITED")
        if result["residual"] is not None:
            residual = abs(Decimal(result["residual"]))
            tolerance = Decimal(result["tolerance"])
            expected = "PASS" if residual <= tolerance else "FAIL"
            assert result["reconciliation_status"] == expected


def test_coverage_reports_real_observation_counts(client):
    """The synthetic fixture has a single statement, so the growth index
    (which needs >= 2 valuations to chain a return) never activates --
    valuation_observation_count is legitimately 0 here. price_observation_count
    is the meaningful check: one statement still prices its holding once."""
    r = client.get("/api/portfolio/coverage")
    body = r.json()
    assert body["price_observation_count"] >= 1
    assert body["carried_forward_observation_count"] >= 0


def test_activity_is_ordered_most_recent_first(client):
    r = client.get("/api/portfolio/activity")
    dates = [row["trade_date"] for row in r.json()]
    assert dates == sorted(dates, reverse=True)


def test_invalid_granularity_is_a_client_error_not_a_server_error(client):
    r = client.get("/api/portfolio/income", params={"granularity": "fortnightly"})
    assert r.status_code == 422


# -- portfolio growth (Step 9) ------------------------------------------------

def test_growth_returns_the_canonical_fields(client):
    r = client.get("/api/portfolio/growth")
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected at least one growth point from the synthetic fixture"
    row = rows[0]
    for key in ("date", "portfolio_value", "contributions", "withdrawals",
               "net_contributions", "investment_gain", "cash_flow_events"):
        assert key in row


def test_growth_investment_gain_is_the_simple_difference_everywhere_it_is_not_null(client):
    r = client.get("/api/portfolio/growth")
    for row in r.json():
        if row["portfolio_value"] is None or row["investment_gain"] is None:
            continue
        assert Decimal(row["investment_gain"]) == Decimal(row["portfolio_value"]) - Decimal(row["net_contributions"])


def test_growth_accepts_an_arbitrary_date_range(client):
    r = client.get("/api/portfolio/growth", params={"start": "2024-07-20", "end": "2024-07-26"})
    assert r.status_code == 200
    dates = [row["date"] for row in r.json()]
    assert all("2024-07-20" <= d <= "2024-07-26" for d in dates)


def test_growth_summary_returns_expected_shape(client):
    r = client.get("/api/portfolio/growth/summary")
    assert r.status_code == 200
    body = r.json()
    for key in ("current_value", "net_contributions", "investment_gain", "growth_pct", "as_at"):
        assert key in body


def test_growth_reconciliation_returns_calculated_source_and_status(client):
    r = client.get("/api/portfolio/growth/reconciliation")
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected at least one reconciliation check from the synthetic fixture"
    for row in rows:
        assert row["status"] in ("PASS", "FAIL", "SKIP")
        assert "calculated" in row and "source" in row and "difference" in row
