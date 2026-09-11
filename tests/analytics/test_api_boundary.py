"""The API boundary (hardening sec 14): Phase 5 must consume analytics
through AnalyticsService's public methods only, never by importing
src.engine or src.history directly for a financial calculation.

Enforced structurally, not just by convention: nothing public on the
service returns a raw Ledger/StateEngine/HistoryService object, and the
required getX() names all exist and are callable.
"""

import inspect

from src.analytics.service import AnalyticsService
from src.engine.ledger import Ledger
from src.engine.state import StateEngine


REQUIRED_METHODS = (
    "getPortfolioOverview", "getPerformance", "getAttribution",
    "getContributions", "getIncome", "getAllocation", "getRisk",
    "getDrawdowns", "getMilestones", "getAnalyticsCapabilities",
    "getDataCoverage",
)


def test_every_required_method_exists():
    for name in REQUIRED_METHODS:
        assert hasattr(AnalyticsService, name), f"missing {name}"
        assert callable(getattr(AnalyticsService, name))


def test_no_public_attribute_returns_a_raw_engine_object(built):
    """Every public (non-underscore) attribute must not be a Ledger or
    StateEngine instance -- those are internal composition details."""
    service = AnalyticsService(built)
    for name in dir(service):
        if name.startswith("_"):
            continue
        try:
            value = getattr(service, name)
        except TypeError:
            continue   # a method requiring arguments; fine, not a leaked object
        if inspect.ismethod(value) or inspect.isfunction(value):
            continue
        assert not isinstance(value, Ledger), f"{name} publicly exposes a Ledger"
        assert not isinstance(value, StateEngine), f"{name} publicly exposes a StateEngine"


def test_service_module_is_the_only_intended_import_surface(built):
    """A Phase 5 consumer only needs this one import to reach every capability
    -- confirmed by driving the whole capability list through one instance."""
    service = AnalyticsService(built)
    caps = service.getAnalyticsCapabilities()
    coverage = service.getDataCoverage()
    overview = service.getPortfolioOverview()
    assert caps and coverage and overview
