"""Allocation, drift and concentration must never claim a dimension the
source data doesn't support (sec 13-15)."""

from datetime import date
from decimal import Decimal as D

from src.analytics.allocation import allocation, allocation_drift, concentration


def test_sector_geography_currency_are_honestly_unavailable(history):
    """Vanguard statements print a product name and ticker only -- no sector,
    geography or currency metadata exists to classify by."""
    for dimension in ("sector", "geography", "currency", "account"):
        result = allocation(history, by=dimension)
        assert result["status"] == "unavailable"


def test_asset_class_allocation_sums_to_one(history):
    result = allocation(history, by="asset_class", on=date(2024, 9, 30))
    assert result["status"] == "ok"
    total = sum(D(v) for v in result["allocation_pct"].values() if v)
    assert abs(total - D("1")) < D("0.0001")


def test_drift_is_pure_configuration_never_touching_stored_data(history):
    """Passing a target must not write anything -- it's a caller-supplied
    comparison point, not an accounting concept."""
    before = allocation(history, by="asset_class", on=date(2024, 9, 30))
    allocation_drift(history, {"cash": D("1.0")}, on=date(2024, 9, 30))
    after = allocation(history, by="asset_class", on=date(2024, 9, 30))
    assert before == after


def test_drift_reports_none_for_a_dimension_with_no_data(history):
    rows = allocation_drift(history, {"vas": D("0.5")}, by="sector")
    assert rows[0].actual_weight is None
    assert rows[0].drift is None


def test_concentration_with_one_holding_matches_its_share_of_the_portfolio(history):
    """Weight is measured against total portfolio value (cash included),
    matching Phase 3's own allocation convention -- a sole holding is not
    100% concentrated while cash sits alongside it. With one holding, HHI
    (sum of squared weights) reduces to weight^2."""
    snapshot = concentration(history, on=date(2024, 9, 30))
    securities_value = D("1500.00")
    total_value = D("1890.00")   # 1500 securities + 390 cash
    expected_weight = securities_value / total_value
    assert snapshot.holding_count == 1
    assert snapshot.largest_holding_pct == expected_weight
    assert snapshot.top_5_pct == expected_weight
    assert snapshot.herfindahl_index == expected_weight * expected_weight


def test_concentration_with_no_holdings_reports_none_not_zero(history):
    snapshot = concentration(history, on=date(2024, 6, 30))
    assert snapshot.holding_count == 0
    assert snapshot.largest_holding_pct is None
