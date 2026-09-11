"""Query interface, aggregation, and the separation of flows from performance."""

from datetime import date
from decimal import Decimal as D

import pytest

from src.history.config import Granularity
from src.history.service import HistoryService


@pytest.fixture
def service(built):
    repo, _ = built
    return HistoryService(repo)


def test_reconciles_against_every_reported_value(service):
    checks = service.reconciliation()
    assert checks
    assert [c for c in checks if c["status"] == "FAIL"] == []


def test_daily_aggregates_up_to_monthly_and_yearly(service):
    daily = service.portfolio_history()
    monthly = service.portfolio_history(granularity=Granularity.MONTHLY)
    yearly = service.portfolio_history(granularity=Granularity.YEARLY)
    assert len(daily) > len(monthly) > len(yearly)
    # Each period takes the value of its closing day, so the last row agrees.
    assert yearly[-1]["total_value"] == daily[-1]["total_value"]
    assert monthly[-1]["total_value"] == daily[-1]["total_value"]


def test_contributions_are_reported_separately_from_returns(service):
    """A portfolio that grew because more was paid in did not earn anything."""
    history = service.contribution_history(Granularity.YEARLY)
    total = history[-1]
    assert D(total["cumulative_contributions"]) == D("500.00")
    assert D(total["cumulative_withdrawals"]) == D("-200.00")
    assert D(total["cumulative_net"]) == D("300.00")


def test_withdrawals_do_not_appear_as_investment_losses(service):
    """Value drawdown includes withdrawals; investment drawdown must not."""
    marks = service.high_water_history(Granularity.DAILY)
    withdrawal_day = next(m for m in marks if m["date"] == "2024-07-25")
    assert withdrawal_day["investment_drawdown_pct"] in (None, "0")


def test_income_history_aggregates_and_carries_franking(service):
    yearly = service.income_history(Granularity.YEARLY)
    assert len(yearly) == 1
    assert D(yearly[0]["gross_income"]) == D("20.00")
    assert D(yearly[0]["franking_credits"]) == D("8.57")


def test_income_can_be_broken_down_by_security(service):
    rows = service.income_history(Granularity.YEARLY, by_security=True)
    assert {r["code"] for r in rows} == {"TST"}


def test_income_by_security_sorts_when_some_rows_have_no_security(service):
    """Interest income has no security_id (code is None), which cannot be
    compared against a code string during sorting -- this must not raise."""
    repo, _ = service.repo, None
    service.repo.conn.execute(
        "INSERT INTO income_daily(date, security_id, kind, amount)"
        " VALUES ('2024-08-01', NULL, 'INTEREST', '1.23')")
    service.repo.commit()
    rows = service.income_history(Granularity.YEARLY, by_security=True)
    assert None in {r["code"] for r in rows}


def test_allocation_history_by_asset_class(service):
    rows = service.allocation_history(by="asset_class",
                                      granularity=Granularity.MONTHLY)
    assert rows
    weights = rows[-1]["allocation_pct"]
    assert "cash" in weights
    assert sum(D(v) for v in weights.values() if v) == pytest.approx(D("1"), abs=D("0.0001"))


def test_holdings_history_is_queryable_for_a_date(service):
    state = service.portfolio_state(date(2024, 9, 30))
    assert state is not None
    assert [h["code"] for h in state["holdings"]] == ["TST"]
    assert D(state["holdings"][0]["units"]) == D("15.00")


def test_missing_dates_return_nothing_rather_than_a_guess(service):
    assert service.portfolio_state(date(1999, 1, 1)) is None
    assert service.portfolio_value(date(1999, 1, 1)) is None


def test_data_quality_is_reported_not_hidden(service):
    quality = service.data_quality()
    assert quality["days"] > 0
    assert set(quality["by_status"]) <= {"actual", "calculated", "estimated",
                                         "unavailable"}
