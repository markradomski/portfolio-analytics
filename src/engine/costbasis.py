"""Cost basis accounting.

Two methods, behind one interface, so the choice is configuration rather than
something baked into the engine.

Neither is a tax calculation. Australian CGT requires identifying the actual
parcels disposed of, so average cost is valid for performance reporting but
must never be reported as a tax position. That belongs in a separate tax module
built on the tax-lot method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.engine.config import CostBasisMethod

ZERO = Decimal("0")


@dataclass(frozen=True)
class Disposal:
    """The result of selling units: what they cost, and what was made on them."""
    units: Decimal
    proceeds: Decimal
    allocated_cost: Decimal
    realised_gain: Decimal


class CostBasisTracker(ABC):
    """Tracks units and their cost for one security."""

    def __init__(self) -> None:
        self.units = ZERO
        self.cost = ZERO

    @property
    def average_cost(self) -> Decimal | None:
        """Cost per unit, or None when nothing is held."""
        return (self.cost / self.units) if self.units else None

    @abstractmethod
    def acquire(self, units: Decimal, cost: Decimal, when: date) -> None: ...

    @abstractmethod
    def dispose(self, units: Decimal, proceeds: Decimal, when: date) -> Disposal: ...


class AverageCostTracker(CostBasisTracker):
    """All units share one pooled cost per unit."""

    def acquire(self, units: Decimal, cost: Decimal, when: date) -> None:
        self.units += units
        self.cost += cost

    def dispose(self, units: Decimal, proceeds: Decimal, when: date) -> Disposal:
        units = abs(units)
        if self.units <= ZERO:
            # Selling something the ledger says is not held. Report it rather
            # than inventing a cost; validation surfaces it as an invariant break.
            return Disposal(units, proceeds, ZERO, proceeds)
        sold = min(units, self.units)
        allocated = self.cost * (sold / self.units)
        self.units -= sold
        self.cost -= allocated
        if self.units == ZERO:
            self.cost = ZERO          # clear residual rounding dust
        return Disposal(sold, proceeds, allocated, proceeds - allocated)


class TaxLotTracker(CostBasisTracker):
    """First-in, first-out parcels, each retaining its own acquisition cost."""

    def __init__(self) -> None:
        super().__init__()
        self._lots: deque[tuple[date, Decimal, Decimal]] = deque()   # when, units, cost/unit

    def acquire(self, units: Decimal, cost: Decimal, when: date) -> None:
        if units <= ZERO:
            return
        self._lots.append((when, units, cost / units))
        self.units += units
        self.cost += cost

    def dispose(self, units: Decimal, proceeds: Decimal, when: date) -> Disposal:
        remaining = abs(units)
        allocated = ZERO
        taken = ZERO
        while remaining > ZERO and self._lots:
            lot_date, lot_units, unit_cost = self._lots[0]
            used = min(remaining, lot_units)
            allocated += used * unit_cost
            taken += used
            remaining -= used
            if used == lot_units:
                self._lots.popleft()
            else:
                self._lots[0] = (lot_date, lot_units - used, unit_cost)
        self.units -= taken
        self.cost -= allocated
        if self.units <= ZERO:
            self.units = ZERO
            self.cost = ZERO
        return Disposal(taken, proceeds, allocated, proceeds - allocated)


_TRACKERS = {
    CostBasisMethod.AVERAGE_COST: AverageCostTracker,
    CostBasisMethod.TAX_LOT: TaxLotTracker,
}


def tracker_for(method: CostBasisMethod) -> CostBasisTracker:
    return _TRACKERS[method]()
