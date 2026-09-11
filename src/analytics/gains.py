"""Realised and unrealised gains, and gain attribution (sec 18-20).

Every figure here is read from Phase 2's cost-basis engine -- realised gains
from disposals, unrealised from current holdings against their cost basis.
No cost-basis calculation happens in this module; that would duplicate Phase
2, which the spec explicitly forbids (sec 18: "Phase 4 must not introduce a
separate cost-basis calculation").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.database.repository import Repository
from src.engine.holdings import HoldingsEngine
from src.engine.ledger import Ledger
from src.engine.prices import PriceSource
from src.engine.state import StateEngine

ZERO = Decimal("0")


@dataclass(frozen=True)
class RealisedGainSummary:
    period_start: date
    period_end: date
    realised_gain: Decimal    # sum of positive disposals
    realised_loss: Decimal    # sum of negative disposals (negative number)
    net_realised_gain: Decimal


@dataclass(frozen=True)
class SecurityRealisedGain:
    security_id: str
    code: str | None
    units_sold: Decimal
    proceeds: Decimal
    cost_basis: Decimal
    realised_gain: Decimal


def realised_gains(ledger: Ledger, start: date | None = None,
                   end: date | None = None,
                   holdings_engine: HoldingsEngine | None = None
                   ) -> RealisedGainSummary:
    """Replays the ledger up to `end` and reads off each security's disposals
    that fall within [start, end] -- the same Position.disposals Phase 2
    already computes during cost-basis tracking."""
    engine = holdings_engine or HoldingsEngine()
    boundary = end or (ledger.end or date.today())
    positions = engine.positions_at(ledger, boundary)

    gain = loss = ZERO
    for position in positions.values():
        for disposal in position.disposals:
            gain += max(disposal.realised_gain, ZERO)
            loss += min(disposal.realised_gain, ZERO)
    # Disposals aren't individually dated in Position (only accumulated), so a
    # start-bounded summary re-derives from the delta between two replays --
    # exact, since realised gain only ever accumulates forward.
    if start is not None:
        prior = engine.positions_at(ledger, start - _ONE_DAY)
        prior_gain = sum((max(d.realised_gain, ZERO)
                          for p in prior.values() for d in p.disposals), ZERO)
        prior_loss = sum((min(d.realised_gain, ZERO)
                          for p in prior.values() for d in p.disposals), ZERO)
        gain, loss = gain - prior_gain, loss - prior_loss

    return RealisedGainSummary(
        period_start=start or (ledger.start or boundary), period_end=boundary,
        realised_gain=gain, realised_loss=loss, net_realised_gain=gain + loss)


from datetime import timedelta as _timedelta
_ONE_DAY = _timedelta(days=1)


def realised_gains_by_security(repo: Repository, ledger: Ledger,
                               start: date | None = None, end: date | None = None,
                               holdings_engine: HoldingsEngine | None = None
                               ) -> list[SecurityRealisedGain]:
    """Per-security disposal detail (sec 18's second table)."""
    engine = holdings_engine or HoldingsEngine()
    boundary = end or (ledger.end or date.today())
    positions = engine.positions_at(ledger, boundary)
    codes = {r["security_id"]: r["code"] for r in repo.rows(
        "SELECT security_id, code FROM securities")}

    out = []
    for security_id, position in positions.items():
        if not position.disposals:
            continue
        units = sum((d.units for d in position.disposals), ZERO)
        proceeds = sum((d.proceeds for d in position.disposals), ZERO)
        cost = sum((d.allocated_cost for d in position.disposals), ZERO)
        gain = sum((d.realised_gain for d in position.disposals), ZERO)
        out.append(SecurityRealisedGain(
            security_id=security_id, code=codes.get(security_id),
            units_sold=units, proceeds=proceeds, cost_basis=cost,
            realised_gain=gain))
    return sorted(out, key=lambda r: (-r.realised_gain, r.code or ""))


@dataclass(frozen=True)
class UnrealisedGainSnapshot:
    security_id: str
    code: str | None
    asset_class: str
    market_value: Decimal | None
    cost_basis: Decimal
    unrealised_gain: Decimal | None
    unrealised_gain_pct: Decimal | None


def unrealised_gains(state_engine: StateEngine, ledger: Ledger, on: date,
                     asset_classes: dict[str, str] | None = None
                     ) -> list[UnrealisedGainSnapshot]:
    """Current unrealised position for every held security -- straight from
    Phase 2's SecurityState, which already handles the zero-cost-basis case
    without producing infinity or NaN (sec 19's own concern, solved in Phase 2)."""
    state = state_engine.state_at(ledger, on)
    classes = asset_classes or {}
    return [UnrealisedGainSnapshot(
        security_id=s.security_id, code=s.code,
        asset_class=classes.get(s.code or "", "unknown"),
        market_value=s.market_value, cost_basis=s.cost_basis,
        unrealised_gain=s.unrealised_gain,
        unrealised_gain_pct=s.unrealised_gain_pct)
        for s in state.securities if s.units != ZERO]


@dataclass(frozen=True)
class GainAttribution:
    """Realised, unrealised and income, kept explicitly non-overlapping (sec
    20): a disposal's gain is realised and stops being part of unrealised the
    moment it's sold, and income is never counted as either."""
    unrealised_gains: Decimal
    realised_gains: Decimal
    income: Decimal

    @property
    def total(self) -> Decimal:
        return self.unrealised_gains + self.realised_gains + self.income


def gain_attribution(state_engine: StateEngine, ledger: Ledger, on: date) -> GainAttribution:
    from src.engine.cash import CashEngine

    state = state_engine.state_at(ledger, on)
    # Matches Phase 2's own income figure (dividends + distributions +
    # interest) rather than PortfolioState.dividends/distributions alone,
    # which omits interest -- income here means every source, per the
    # spec's own worked example (sec 20).
    income = CashEngine().flows(ledger, end=on).income
    return GainAttribution(
        unrealised_gains=state.unrealised_gain,
        realised_gains=state.realised_gain,
        income=income)
