"""Replay the ledger into positions through time.

    closing_units = opening_units + purchased - sold + corporate actions

Positions move on trade date, matching the statements' own snapshots: a trade
placed before period end appears in that period's holdings even when it settles
afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal

from src.engine.config import EngineConfig, DEFAULT_CONFIG
from src.engine.costbasis import CostBasisTracker, Disposal, tracker_for
from src.engine.ledger import Event, Ledger
from src.models import TxnType

ZERO = Decimal("0")


@dataclass
class Position:
    security_id: str
    code: str | None = None
    units: Decimal = ZERO
    cost_basis: Decimal = ZERO
    realised_gain: Decimal = ZERO
    income: Decimal = ZERO
    fees: Decimal = ZERO
    disposals: list[Disposal] = field(default_factory=list)

    @property
    def average_cost(self) -> Decimal | None:
        return (self.cost_basis / self.units) if self.units else None


class HoldingsEngine:
    """Builds positions by replaying events in ledger order."""

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config

    def positions_at(self, ledger: Ledger, when: date) -> dict[str, Position]:
        return self._replay(ledger.up_to(when))

    def positions_over(self, ledger: Ledger, dates: list[date]):
        """Yield (date, positions) for each date, replaying the ledger once.

        Equivalent to calling positions_at for every date, but linear in the
        number of events rather than quadratic.
        """
        positions: dict[str, Position] = {}
        trackers: dict[str, CostBasisTracker] = {}
        events = iter(ledger.events)
        pending = next(events, None)

        for when in dates:
            while pending is not None and pending.trade_date <= when:
                self._apply(pending, positions, trackers)
                pending = next(events, None)
            yield when, {sid: replace(p, disposals=list(p.disposals))
                         for sid, p in positions.items()}

    def _replay(self, events) -> dict[str, Position]:
        positions: dict[str, Position] = {}
        trackers: dict[str, CostBasisTracker] = {}
        for event in events:
            self._apply(event, positions, trackers)
        return positions

    def _apply(self, event, positions: dict[str, Position],
               trackers: dict[str, CostBasisTracker]) -> None:
        """Apply one event to the running positions."""
        if event.security_id is None:
            return

        position = positions.setdefault(
            event.security_id, Position(event.security_id, event.code))
        tracker = trackers.setdefault(
            event.security_id, tracker_for(self.config.cost_basis_method))

        if event.type is TxnType.BUY and event.units:
            # Brokerage paid on acquisition forms part of what the units cost.
            cost = (abs(event.net_amount) if event.net_amount is not None
                    else abs(event.units * (event.price or ZERO)))
            tracker.acquire(abs(event.units), cost, event.trade_date)

        elif event.type is TxnType.SELL and event.units:
            proceeds = (abs(event.net_amount) if event.net_amount is not None
                        else abs(event.units * (event.price or ZERO)))
            disposal = tracker.dispose(event.units, proceeds, event.trade_date)
            position.realised_gain += disposal.realised_gain
            position.disposals.append(disposal)

        elif event.type is TxnType.CORPORATE_ACTION and event.units:
            # Units in without consideration; cost basis is unchanged.
            tracker.acquire(event.units, ZERO, event.trade_date)

        elif event.type in (TxnType.DIVIDEND, TxnType.DISTRIBUTION):
            position.income += event.net_amount or ZERO

        elif event.type is TxnType.FEE:
            position.fees += abs(event.net_amount or ZERO)

        position.units = tracker.units
        position.cost_basis = tracker.cost

    def units_at(self, ledger: Ledger, when: date) -> dict[str, Decimal]:
        return {sid: p.units for sid, p in self.positions_at(ledger, when).items()
                if p.units != ZERO}
