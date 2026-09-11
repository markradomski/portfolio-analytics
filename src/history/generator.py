"""Generate the canonical daily history.

Phase 2 remains authoritative: this layer asks the accounting engine for state
and records it, and performs no financial calculation of its own beyond
arithmetic on what the engine returns.

The honest limitation of this dataset is pricing. The statements quote prices on
roughly 23 dates across six years, so on almost every other day a holding's
market value is real units at a stale price. Every row says which it is:

    ACTUAL       Vanguard reported this portfolio value for this date
    CALCULATED   units x a price actually quoted on this date
    ESTIMATED    units x the most recent earlier price
    UNAVAILABLE  a holding exists with no price at or before this date

Cash, contributions, withdrawals, income, fees and realised gains are exact on
every date -- they come from the ledger, not from prices. Only market value and
anything derived from it is subject to the status above.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from src.database.repository import Repository
from src.engine.cash import CashEngine
from src.engine.config import DEFAULT_CONFIG, EngineConfig
from src.engine.ledger import Ledger
from src.engine.prices import PriceQuality, SnapshotPriceSource
from src.engine.state import PortfolioState, StateEngine
from src.history.config import (DEFAULT_HISTORY_CONFIG, AssetClass,
                                HistoryConfig, ValuationStatus, classify)

ZERO = Decimal("0")
CALCULATION_METHOD = "phase2-state-replay"

_QUALITY_TO_STATUS = {
    PriceQuality.QUOTED: ValuationStatus.CALCULATED,
    PriceQuality.CARRIED_FORWARD: ValuationStatus.ESTIMATED,
    PriceQuality.UNAVAILABLE: ValuationStatus.UNAVAILABLE,
    PriceQuality.NOT_HELD: ValuationStatus.CALCULATED,
}


@dataclass
class HoldingRow:
    date: date
    security_id: str
    code: str | None
    units: Decimal
    price: Decimal | None
    market_value: Decimal | None
    cost_basis: Decimal
    unrealised_gain: Decimal | None
    allocation_pct: Decimal | None
    asset_class: AssetClass
    valuation_status: ValuationStatus
    price_as_at: date | None


@dataclass
class DailyRow:
    date: date
    # None when a holding has no price at or before this date. A partial sum
    # would understate the portfolio while looking like a real figure.
    total_value: Decimal | None
    securities_value: Decimal | None
    cash: Decimal
    cost_basis: Decimal
    invested_capital: Decimal
    realised_gain: Decimal
    unrealised_gain: Decimal | None
    dividends: Decimal
    distributions: Decimal
    income: Decimal
    fees: Decimal
    cumulative_contributions: Decimal
    cumulative_withdrawals: Decimal
    # Drawdown on portfolio value. Includes the effect of contributions and
    # withdrawals: a portfolio that halves because half was withdrawn shows a
    # 50% value drawdown without having lost anything.
    high_water_mark: Decimal
    drawdown_value: Decimal | None
    drawdown_pct: Decimal | None
    # Drawdown on a flow-neutral growth index, which is what "how far are my
    # investments down" actually means. Flat between priced dates.
    return_index: Decimal | None
    # The valuation date this index value was observed on. Between valuation
    # dates the index is carried forward, so this is what says how stale it is.
    index_as_at: date | None
    return_high_water: Decimal | None
    return_drawdown_pct: Decimal | None
    valuation_status: ValuationStatus
    valuation_source: str
    price_as_at: date | None
    source_count: int
    holdings: list[HoldingRow] = field(default_factory=list)


class HistoryGenerator:
    def __init__(self, repo: Repository,
                 config: EngineConfig = DEFAULT_CONFIG,
                 history_config: HistoryConfig = DEFAULT_HISTORY_CONFIG):
        self.repo = repo
        self.config = config
        self.history_config = history_config
        self.ledger = Ledger.from_repository(repo)
        self.prices = SnapshotPriceSource.from_repository(repo)
        self.opening_cash = self._opening_cash()
        self.state_engine = StateEngine(self.prices, config, self.opening_cash)
        self.cash_engine = CashEngine(self.opening_cash)
        self._meta = self._security_metadata()
        self._reported = self._reported_values()
        self._sources = self._source_counts()

    # -- lookups -------------------------------------------------------------

    def _opening_cash(self) -> Decimal:
        from src.engine.cash import opening_cash_for
        return opening_cash_for(self.repo)

    def _security_metadata(self) -> dict[str, tuple[str, str]]:
        return {r["security_id"]: (r["code"], r["type"])
                for r in self.repo.rows("SELECT security_id, code, type FROM securities")}

    def _reported_values(self) -> dict[date, Decimal]:
        return {date.fromisoformat(r["reporting_date"]): Decimal(r["portfolio_value"])
                for r in self.repo.rows(
                    "SELECT reporting_date, portfolio_value FROM portfolio_valuations")}

    def _source_counts(self) -> dict[date, int]:
        """How many source documents cover each reported date."""
        counts: dict[date, int] = {}
        for row in self.repo.rows(
            "SELECT v.reporting_date, COUNT(DISTINCT s.document_id) AS n"
            " FROM portfolio_valuations v"
            " LEFT JOIN record_sources s ON s.record_type = 'valuation'"
            "   AND s.record_id = v.valuation_id"
            " GROUP BY v.reporting_date"
        ):
            counts[date.fromisoformat(row["reporting_date"])] = row["n"]
        return counts

    # -- generation ----------------------------------------------------------

    def date_range(self) -> list[date]:
        start, end = self.ledger.start, self.ledger.end
        if start is None or end is None:
            return []
        end = max(end, max(self._reported, default=end))
        return [start + timedelta(days=n) for n in range((end - start).days + 1)]

    def generate(self, dates: list[date] | None = None,
                 opening_high_water: Decimal = ZERO,
                 opening_return_high_water: Decimal | None = None) -> list[DailyRow]:
        dates = dates if dates is not None else self.date_range()
        if not dates:
            return []

        cash_by_date = {when: flows for when, _, flows
                        in self.cash_engine.balances_over(self.ledger, dates)}
        index_by_date = self._growth_index(dates)

        rows: list[DailyRow] = []
        high_water = opening_high_water
        return_high_water = opening_return_high_water

        for state in self.state_engine.states_over(self.ledger, dates):
            flows = cash_by_date[state.date]
            holdings = self._holdings_for(state)
            status, price_as_at = self._status_for(state, holdings)
            source = ("VANGUARD" if status is ValuationStatus.ACTUAL
                      else "VANGUARD_SECURITY_PRICE")
            unpriced = status is ValuationStatus.UNAVAILABLE

            total = None if unpriced else state.total_value
            securities_value = None if unpriced else state.securities_value
            unrealised = None if unpriced else state.unrealised_gain

            drawdown = drawdown_pct = None
            if total is not None:
                high_water = max(high_water, total)
                drawdown = total - high_water
                drawdown_pct = (drawdown / high_water) if high_water > ZERO else None

            index, index_as_at = index_by_date.get(state.date, (None, None))
            return_drawdown = None
            if index is not None:
                return_high_water = (index if return_high_water is None
                                     else max(return_high_water, index))
                if return_high_water > ZERO:
                    return_drawdown = index / return_high_water - Decimal(1)

            rows.append(DailyRow(
                date=state.date,
                total_value=total,
                securities_value=securities_value,
                cash=state.cash,
                cost_basis=state.cost_basis,
                # What the investor has put in, net of what they have taken out.
                invested_capital=flows.deposits + flows.withdrawals,
                realised_gain=state.realised_gain,
                unrealised_gain=unrealised,
                dividends=state.dividends,
                distributions=state.distributions,
                income=flows.income,
                fees=abs(flows.fees),
                cumulative_contributions=flows.deposits,
                cumulative_withdrawals=flows.withdrawals,
                high_water_mark=high_water,
                drawdown_value=drawdown,
                drawdown_pct=drawdown_pct,
                return_index=index,
                index_as_at=index_as_at,
                return_high_water=return_high_water,
                return_drawdown_pct=return_drawdown,
                valuation_status=status,
                valuation_source=source,
                price_as_at=price_as_at,
                source_count=self._sources.get(state.date, 0),
                holdings=holdings,
            ))
        return rows

    def _growth_index(self, dates: list[date]
                      ) -> dict[date, tuple[Decimal | None, date | None]]:
        """A flow-neutral growth index, base 100, for measuring real drawdowns.

        Built by chaining Modified Dietz returns between the dates the portfolio
        can actually be valued, using the same Phase 2 functions the performance
        figures use. It steps at those dates and is flat between them, because
        no price movement is observable in between -- which is honest, if blunt.
        """
        from src.engine.returns import modified_dietz

        valuation_dates = sorted(self._reported)
        if len(valuation_dates) < 2:
            return {when: (None, None) for when in dates}

        external = self.cash_engine.external_flows(self.ledger)
        states = {s.date: s for s in
                  self.state_engine.states_over(self.ledger, valuation_dates)}

        index = Decimal("100")
        at_valuation: dict[date, Decimal] = {valuation_dates[0]: index}
        for previous, current in zip(valuation_dates, valuation_dates[1:]):
            period = modified_dietz(
                states[previous].total_value, states[current].total_value,
                [(w, a) for w, a in external if previous < w <= current],
                previous, current)
            if period.ret is not None:
                index *= (Decimal(1) + period.ret)
            at_valuation[current] = index

        # Carry the index forward between valuation dates; before the first one
        # there is nothing to carry, so it stays undefined.
        out: dict[date, tuple[Decimal | None, date | None]] = {}
        current_index: Decimal | None = None
        observed_on: date | None = None

        # A partial rebuild starts mid-history, so seed the carry-forward from
        # the last valuation before the window. Without this the index would
        # read as unknown until the next valuation, and an incremental rebuild
        # would not match a full one.
        earlier = [d for d in at_valuation if d < dates[0]]
        if earlier:
            observed_on = max(earlier)
            current_index = at_valuation[observed_on]
        for when in dates:
            if when in at_valuation:
                current_index, observed_on = at_valuation[when], when
            out[when] = (current_index, observed_on)
        return out

    def _holdings_for(self, state: PortfolioState) -> list[HoldingRow]:
        total = state.total_value
        out: list[HoldingRow] = []
        for security in state.securities:
            if security.units == ZERO:
                continue
            code, security_type = self._meta.get(
                security.security_id, (security.code, None))
            allocation = ((security.market_value / total)
                          if security.market_value is not None and total > ZERO
                          else None)
            out.append(HoldingRow(
                date=state.date, security_id=security.security_id, code=code,
                units=security.units, price=security.price,
                market_value=security.market_value,
                cost_basis=security.cost_basis,
                unrealised_gain=security.unrealised_gain,
                allocation_pct=allocation,
                asset_class=classify(code, security_type, self.history_config),
                valuation_status=_QUALITY_TO_STATUS[security.value_quality],
                price_as_at=security.price_as_at))
        return out

    def _status_for(self, state: PortfolioState,
                    holdings: list[HoldingRow]) -> tuple[ValuationStatus, date | None]:
        """The weakest status among the holdings bounds the portfolio's own.

        A date Vanguard reported directly is ACTUAL, but only when the
        calculated value agrees with it -- otherwise the reconciliation report
        is the place that disagreement belongs, not a status that hides it.
        """
        if not holdings:
            reported = self._reported.get(state.date)
            if reported is not None:
                return ValuationStatus.ACTUAL, state.date
            return ValuationStatus.CALCULATED, None

        statuses = {h.valuation_status for h in holdings}
        price_dates = [h.price_as_at for h in holdings if h.price_as_at]
        price_as_at = max(price_dates) if price_dates else None

        if ValuationStatus.UNAVAILABLE in statuses:
            return ValuationStatus.UNAVAILABLE, price_as_at

        reported = self._reported.get(state.date)
        if (reported is not None
                and (state.total_value - reported).copy_abs()
                <= self.config.reconciliation_tolerance):
            return ValuationStatus.ACTUAL, state.date

        if ValuationStatus.ESTIMATED in statuses:
            return ValuationStatus.ESTIMATED, price_as_at
        return ValuationStatus.CALCULATED, price_as_at

    def fingerprint(self) -> str:
        """Identifies the ledger the history was built from, so a stale rebuild
        can be detected."""
        import hashlib
        digest = hashlib.sha256()
        for event in self.ledger:
            digest.update(event.event_id.encode())
        return digest.hexdigest()[:16]
