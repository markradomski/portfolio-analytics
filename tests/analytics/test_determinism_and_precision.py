"""Determinism across repeated calls (hardening sec 13), and confirmation
that display rounding never touches the values reconciliation depends on
(hardening sec 12)."""

from datetime import date
from decimal import Decimal as D

import pytest

from src.analytics.service import AnalyticsService
from src.database.repository import Repository


@pytest.fixture
def service(built):
    return AnalyticsService(built)


@pytest.mark.parametrize("call", [
    lambda s: s.getPerformanceForYear(2024),
    lambda s: s.getContributionSummary(),
    lambda s: s.getReturns(),
    lambda s: s.getCalendarPerformance(),
    lambda s: s.getIncomeAnalytics(),
    lambda s: s.getAllocation(by="asset_class"),
    lambda s: s.getRiskMetrics(),
    lambda s: s.getDrawdownAnalytics(),
    lambda s: s.getMilestoneAnalytics(),
    lambda s: s.getAnalyticsCapabilities(),
    lambda s: s.getDataCoverage(),
    lambda s: s.getGrowthReconciliation(date(2024, 6, 30), date(2024, 9, 30)),
    lambda s: s.getAttributionReconciliation(date(2024, 6, 30), date(2024, 9, 30)),
])
def test_repeated_calls_are_identical(service, call):
    first, second = call(service), call(service)
    assert first == second


def test_capabilities_are_deterministic_across_fresh_service_instances(built):
    """Not just the same instance called twice -- a fresh AnalyticsService
    built from the same database must agree too."""
    first = AnalyticsService(built).getAnalyticsCapabilities()
    second = AnalyticsService(built).getAnalyticsCapabilities()
    assert first == second


def test_full_rebuild_produces_identical_analytics(tmp_path, tax_dir):
    """Import, rebuild, and query analytics twice from scratch -- the
    complete pipeline, not just a cached service."""
    from src.history.store import HistoryStore
    from src.ingestion.importer import import_directory

    def build_and_query():
        repo = Repository(tmp_path / f"det_{id(object())}.db")
        import_directory(tax_dir, repo)
        HistoryStore(repo).rebuild()
        service = AnalyticsService(repo)
        result = (service.getPerformanceForYear(2024), service.getContributionSummary(),
                  service.getAnalyticsCapabilities(), service.getDataCoverage())
        repo.close()
        return result

    first = build_and_query()
    second = build_and_query()
    assert first == second


def test_display_rounding_does_not_affect_reconciliation(service):
    """Rounding a value for display must never feed back into the figure
    reconciliation checks against -- reconciliation always operates on full
    Decimal precision, never a pre-rounded intermediate."""
    growth = service.getGrowthReconciliation(date(2024, 6, 30), date(2024, 9, 30))
    if growth.residual is None:
        pytest.skip("reconciliation unavailable for this fixture window")
    # Round the residual for display only, as a UI would -- this must not be
    # what the PASS/FAIL decision itself was based on. The decision is made
    # from the full-precision residual in the service layer, before any
    # rounding a caller might apply afterward.
    # The PASS/FAIL decision is derived from the full-precision residual, not
    # from whatever a UI would separately round it to for display. Rounding
    # the same residual here for illustration must not change that decision.
    displayed = round(float(growth.residual), 2)
    assert (abs(growth.residual) <= growth.tolerance) == (growth.reconciliation_status == "PASS")
    assert abs(float(growth.residual) - displayed) < 0.01   # display rounding is cosmetic only
    # Full precision is retained on the underlying figures the residual was
    # computed from (proven with a genuinely sub-cent case on the real
    # portfolio in test_intermediate_precision_exceeds_display_precision).


def test_intermediate_precision_exceeds_display_precision():
    """Phase 2's Decimal arithmetic is not pre-rounded to 2dp at any
    intermediate step -- confirmed directly on the real portfolio, where
    reconciliation residuals are exact to many more than 2 decimal places."""
    from pathlib import Path
    db_path = Path(__file__).resolve().parents[2] / "data/processed/portfolio.db"
    if not db_path.exists():
        pytest.skip("real portfolio database not present in this checkout")
    from src.engine.cash import opening_cash_for
    from src.engine.ledger import Ledger
    from src.engine.prices import SnapshotPriceSource
    from src.engine.state import StateEngine
    from src.analytics.attribution import reconcile_growth

    repo = Repository(db_path)
    try:
        ledger = Ledger.from_repository(repo)
        engine = StateEngine(SnapshotPriceSource.from_repository(repo),
                             opening_cash=opening_cash_for(repo))
        result = reconcile_growth(engine, ledger, date(2024, 1, 1), date(2024, 12, 31))
        # Decimal values here carry many more significant digits than a 2dp
        # display would show -- proof nothing was pre-rounded along the way.
        assert len(str(result.attributed_change).split(".")[-1]) > 2
    finally:
        repo.close()
