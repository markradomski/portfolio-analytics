"""Portfolio state at a point in time.

Given every event up to a date, this reconstructs what was held, what it was
worth, and how much of that was gain. The same inputs always produce the same
state: nothing here reads the clock or a live price.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from src.engine.cash import CashEngine
from src.engine.config import DEFAULT_CONFIG, EngineConfig
from src.engine.holdings import HoldingsEngine, Position
from src.engine.ledger import Ledger
from src.engine.prices import PriceQuality, PriceSource, Quote

ZERO = Decimal("0")


@dataclass
class SecurityState:
    security_id: str
    code: str | None
    units: Decimal
    price: Decimal | None
    market_value: Decimal | None
    value_quality: PriceQuality
    price_as_at: date | None
    cost_basis: Decimal
    realised_gain: Decimal
    income: Decimal

    @property
    def unrealised_gain(self) -> Decimal | None:
        if self.market_value is None:
            return None
        return self.market_value - self.cost_basis

    @property
    def unrealised_gain_pct(self) -> Decimal | None:
        """None rather than infinity when there is no cost to compare against."""
        gain = self.unrealised_gain
        if gain is None or self.cost_basis == ZERO:
            return None
        return gain / self.cost_basis


@dataclass
class PortfolioState:
    date: date
    cash: Decimal
    securities: list[SecurityState] = field(default_factory=list)
    realised_gain: Decimal = ZERO
    dividends: Decimal = ZERO
    distributions: Decimal = ZERO
    fees: Decimal = ZERO

    @property
    def securities_value(self) -> Decimal:
        return sum((s.market_value or ZERO for s in self.securities), ZERO)

    @property
    def total_value(self) -> Decimal:
        return self.securities_value + self.cash

    @property
    def cost_basis(self) -> Decimal:
        return sum((s.cost_basis for s in self.securities), ZERO)

    @property
    def unrealised_gain(self) -> Decimal:
        return sum((s.unrealised_gain or ZERO for s in self.securities), ZERO)

    @property
    def value_quality(self) -> PriceQuality:
        """The weakest quality among the holdings, since that bounds the total.
        A portfolio holding nothing (or only NOT_HELD positions) is exact by
        definition -- there is nothing left unpriced."""
        if not self.securities:
            return PriceQuality.NOT_HELD
        qualities = {s.value_quality for s in self.securities}
        for level in (PriceQuality.UNAVAILABLE, PriceQuality.CARRIED_FORWARD,
                      PriceQuality.QUOTED):
            if level in qualities:
                return level
        return PriceQuality.NOT_HELD


class StateEngine:
    def __init__(self, prices: PriceSource, config: EngineConfig = DEFAULT_CONFIG,
                 opening_cash: Decimal = ZERO):
        self.prices = prices
        self.config = config
        self.holdings = HoldingsEngine(config)
        self.cash = CashEngine(opening_cash)

    def state_at(self, ledger: Ledger, when: date) -> PortfolioState:
        positions = self.holdings.positions_at(ledger, when)
        securities: list[SecurityState] = []

        for position in sorted(positions.values(), key=lambda p: (p.code or "", p.security_id)):
            quote = (self.prices.quote(position.security_id, when)
                     if position.units != ZERO
                     else Quote(None, PriceQuality.NOT_HELD, None))
            market_value = (position.units * quote.price
                            if quote.price is not None and position.units != ZERO
                            else (ZERO if position.units == ZERO else None))
            securities.append(SecurityState(
                security_id=position.security_id, code=position.code,
                units=position.units, price=quote.price, market_value=market_value,
                value_quality=quote.quality, price_as_at=quote.as_at,
                cost_basis=position.cost_basis, realised_gain=position.realised_gain,
                income=position.income))

        flows = self.cash.flows(ledger, end=when)
        from src.models import TxnType
        dividends = sum((e.net_amount or ZERO for e in ledger.up_to(when)
                         if e.type is TxnType.DIVIDEND), ZERO)
        distributions = sum((e.net_amount or ZERO for e in ledger.up_to(when)
                             if e.type is TxnType.DISTRIBUTION), ZERO)

        return PortfolioState(
            date=when,
            cash=self.cash.balance_at(ledger, when),
            securities=securities,
            realised_gain=sum((s.realised_gain for s in securities), ZERO),
            dividends=dividends,
            distributions=distributions,
            fees=abs(flows.fees),
        )

    def states_over(self, ledger: Ledger, dates: list[date]):
        """Yield PortfolioState for each date, replaying the ledger once.

        Equivalent to calling state_at for every date. Used by the history
        layer, which needs a state per day and cannot afford a full replay each
        time.
        """
        from src.models import TxnType

        positions_by_date = dict(self.holdings.positions_over(ledger, dates))
        cash_by_date = {when: (balance, flows) for when, balance, flows
                        in self.cash.balances_over(ledger, dates)}

        dividends = distributions = ZERO
        events = iter(ledger.events)
        pending = next(events, None)

        for when in dates:
            while pending is not None and pending.trade_date <= when:
                if pending.type is TxnType.DIVIDEND:
                    dividends += pending.net_amount or ZERO
                elif pending.type is TxnType.DISTRIBUTION:
                    distributions += pending.net_amount or ZERO
                pending = next(events, None)

            balance, flows = cash_by_date[when]
            yield self._compose(when, positions_by_date[when], balance,
                                dividends, distributions, abs(flows.fees))

    def _compose(self, when: date, positions, cash: Decimal,
                 dividends: Decimal, distributions: Decimal,
                 fees: Decimal) -> PortfolioState:
        securities: list[SecurityState] = []
        for position in sorted(positions.values(),
                               key=lambda p: (p.code or "", p.security_id)):
            quote = (self.prices.quote(position.security_id, when)
                     if position.units != ZERO
                     else Quote(None, PriceQuality.NOT_HELD, None))
            market_value = (position.units * quote.price
                            if quote.price is not None and position.units != ZERO
                            else (ZERO if position.units == ZERO else None))
            securities.append(SecurityState(
                security_id=position.security_id, code=position.code,
                units=position.units, price=quote.price, market_value=market_value,
                value_quality=quote.quality, price_as_at=quote.as_at,
                cost_basis=position.cost_basis, realised_gain=position.realised_gain,
                income=position.income))

        return PortfolioState(
            date=when, cash=cash, securities=securities,
            realised_gain=sum((s.realised_gain for s in securities), ZERO),
            dividends=dividends, distributions=distributions, fees=fees)
