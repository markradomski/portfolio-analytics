"""The AnalyticsService façade: every method returns structured data, is
deterministic, and requires no PII (sec 37, 43, 45)."""

from datetime import date
from decimal import Decimal as D

import pytest

from src.analytics.service import AnalyticsService
from tests.fixtures import synthetic

FORBIDDEN = (synthetic.FAKE_NAME, synthetic.FAKE_ADDRESS_1,
             synthetic.FAKE_ACCOUNT, synthetic.FAKE_BSB)


@pytest.fixture
def service(built):
    return AnalyticsService(built)


def test_opening_cash_is_correctly_seeded(service):
    """Regression: the service's StateEngine must read the statement's own
    opening cash balance, not default to zero -- caught this exact gap while
    building Phase 4, since the real portfolio's opening cash is coincidentally
    zero and never exercised it. Uses the private engine accessors
    deliberately -- this is a white-box test of the service's own wiring,
    not an example of how a caller (Phase 5) should ever reach it; Phase 5
    consumes only the public getX() methods (hardening sec 14)."""
    state = service._state_engine_.state_at(service._ledger_, date(2024, 6, 30))
    assert state.cash == D("100.00")


def test_reconciliation_methods_wire_through_to_the_engine(service):
    """The synthetic fixture's trades have no paired TRANSFER row (it was
    built for Phase 1's PDF-parsing edge cases, not full economic
    consistency -- see tests/analytics/test_attribution.py for the real
    reconciliation proof, both on a properly paired ledger and against the
    full six-year real history). Here, just confirm the façade calls the same
    underlying function and doesn't silently substitute a different result."""
    from src.analytics.attribution import reconcile_growth, reconcile_attribution

    start, end = date(2024, 6, 30), date(2024, 9, 30)
    direct_growth = reconcile_growth(service._state_engine_, service._ledger_, start, end)
    direct_attribution = reconcile_attribution(service._state_engine_, service._ledger_, start, end)
    assert service.getGrowthReconciliation(start, end) == direct_growth
    assert service.getAttributionReconciliation(start, end) == direct_attribution


def test_repeated_calls_are_deterministic(service):
    first = service.getPerformanceForYear(2024)
    second = service.getPerformanceForYear(2024)
    assert first == second


def test_no_personal_data_in_any_analytics_output(service):
    """Scans the flattened output of every getX method for the fixture's
    fake identity details -- none of it should ever reach here, since
    analytics reads only internal financial identifiers."""
    import dataclasses

    def flatten(value) -> str:
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return " ".join(flatten(v) for v in dataclasses.asdict(value).values())
        if isinstance(value, dict):
            return " ".join(flatten(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return " ".join(flatten(v) for v in value)
        return str(value) if value is not None else ""

    checks = [
        service.getPerformanceForYear(2024),
        service.getContributionSummary(),
        service.getReturns(),
        service.getCalendarPerformance(),
        service.getIncomeAnalytics(),
        service.getAllocation(by="asset_class"),
        service.getTradingActivity(),
        service.getFeesByYear(),
        service.getTaxAnalytics(),
        service.getMilestoneAnalytics(),
    ]
    text = flatten(checks)
    for secret in FORBIDDEN:
        assert secret not in text, f"{secret!r} leaked into analytics output"


def test_unknown_benchmark_period_label_raises_rather_than_guessing(service):
    with pytest.raises(ValueError):
        service.getBenchmarkComparison("2Y", "asx200")
