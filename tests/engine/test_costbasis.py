from datetime import date
from decimal import Decimal as D

import pytest

from src.engine.config import CostBasisMethod
from src.engine.costbasis import AverageCostTracker, TaxLotTracker, tracker_for

WHEN = date(2024, 1, 1)
LATER = date(2024, 6, 1)


def test_average_cost_pools_purchases():
    t = AverageCostTracker()
    t.acquire(D("100"), D("8000"), WHEN)     # $80.00
    t.acquire(D("100"), D("10000"), LATER)   # $100.00
    assert t.units == D("200")
    assert t.average_cost == D("90")


def test_average_cost_partial_sale_allocates_proportionally():
    """100 units at $80; sell 40 at $110 -> allocated cost 3200, gain 1200."""
    t = AverageCostTracker()
    t.acquire(D("100"), D("8000"), WHEN)
    disposal = t.dispose(D("-40"), D("4400"), LATER)
    assert disposal.allocated_cost == D("3200")
    assert disposal.realised_gain == D("1200")
    assert t.units == D("60")
    assert t.cost == D("4800")


def test_selling_everything_clears_the_cost():
    t = AverageCostTracker()
    t.acquire(D("10"), D("1000"), WHEN)
    t.dispose(D("-10"), D("1500"), LATER)
    assert t.units == 0
    assert t.cost == 0
    assert t.average_cost is None


def test_tax_lots_consume_oldest_first():
    """Same trades as the average-cost case, different allocated cost."""
    t = TaxLotTracker()
    t.acquire(D("100"), D("8000"), WHEN)      # $80
    t.acquire(D("100"), D("10000"), LATER)    # $100
    disposal = t.dispose(D("-120"), D("13200"), date(2024, 9, 1))
    # 100 units at $80 plus 20 at $100
    assert disposal.allocated_cost == D("10000")
    assert t.units == D("80")
    assert t.cost == D("8000")


def test_methods_disagree_which_is_why_it_is_configurable():
    average, lots = AverageCostTracker(), TaxLotTracker()
    for tracker in (average, lots):
        tracker.acquire(D("100"), D("8000"), WHEN)
        tracker.acquire(D("100"), D("12000"), LATER)
    sale = (D("-100"), D("11000"), date(2024, 9, 1))
    assert average.dispose(*sale).allocated_cost == D("10000")
    assert lots.dispose(*sale).allocated_cost == D("8000")


def test_selling_more_than_held_is_reported_not_invented():
    t = AverageCostTracker()
    t.acquire(D("10"), D("1000"), WHEN)
    disposal = t.dispose(D("-25"), D("2500"), LATER)
    assert disposal.units == D("10")          # only what was actually held
    assert t.units == 0


def test_factory_returns_the_configured_method():
    assert isinstance(tracker_for(CostBasisMethod.AVERAGE_COST), AverageCostTracker)
    assert isinstance(tracker_for(CostBasisMethod.TAX_LOT), TaxLotTracker)
