"""The engine's public surface.

One façade, shaped around the questions later phases ask, so the eventual web
API is a thin translation rather than a place where financial decisions get
made. Nothing above this layer should decide what counts as a gain, a
contribution or a return.

    state        -> what was held and what it was worth on a date
    history      -> that state through time
    holdings     -> per-security positions on a date
    performance  -> TWRR, XIRR and the return decomposition
    income       -> dividends, distributions, interest
    transactions -> the ledger itself
    attribution  -> where the profit came from
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.database.repository import Repository
from src.engine.attribution import Attribution, Contribution
from src.engine.cash import CashEngine
from src.engine.config import DEFAULT_CONFIG, EngineConfig, ValuationFrequency
from src.engine.ledger import Event, Ledger
from src.engine.prices import PriceSource, SnapshotPriceSource
from src.engine.reconciliation import Check, Reconciler
from src.engine.returns import (PeriodReturn, ReturnDecomposition, annualised,
                                modified_dietz, time_weighted_return, xirr)
from src.engine.state import PortfolioState, StateEngine
from src.models import TxnType

ZERO = Decimal("0")


@dataclass(frozen=True)
class Snapshot:
    date: date
    total_value: Decimal
    cash: Decimal
    securities_value: Decimal
    cumulative_contributions: Decimal
    cumulative_withdrawals: Decimal
    cumulative_income: Decimal
    cumulative_realised_gain: Decimal
    unrealised_gain: Decimal
    value_quality: str


@dataclass(frozen=True)
class Performance:
    start: date
    end: date
    periods: list[PeriodReturn]
    twrr: Decimal | None
    twrr_annualised: Decimal | None
    xirr: Decimal | None
    decomposition: ReturnDecomposition


class PortfolioService:
    def __init__(self, repo: Repository, config: EngineConfig = DEFAULT_CONFIG,
                 prices: PriceSource | None = None):
        self.repo = repo
        self.config = config
        self.prices = prices or SnapshotPriceSource.from_repository(repo)
        self.ledger = Ledger.from_repository(repo)
        self.opening_cash = self._opening_cash()
        self.state_engine = StateEngine(self.prices, config, self.opening_cash)
        self.cash_engine = CashEngine(self.opening_cash)

    def _opening_cash(self) -> Decimal:
        from src.engine.cash import opening_cash_for
        return opening_cash_for(self.repo)

    # -- dates ---------------------------------------------------------------

    def reported_dates(self) -> list[date]:
        """Dates Vanguard actually priced the portfolio on."""
        return [date.fromisoformat(r["reporting_date"]) for r in self.repo.rows(
            "SELECT DISTINCT reporting_date FROM portfolio_valuations"
            " ORDER BY reporting_date")]

    def valuation_dates(self) -> list[date]:
        if self.config.valuation_frequency is ValuationFrequency.QUARTERLY:
            return self.reported_dates()
        return sorted(set(self.reported_dates()) | set(self.ledger.event_dates()))

    # -- endpoints -----------------------------------------------------------

    def state(self, on: date | None = None) -> PortfolioState:
        when = on or (self.reported_dates() or [self.ledger.end])[-1]
        return self.state_engine.state_at(self.ledger, when)

    def holdings(self, on: date | None = None):
        return self.state(on).securities

    def transactions(self) -> tuple[Event, ...]:
        return self.ledger.events

    def history(self) -> list[Snapshot]:
        """Portfolio state at every valuation date, with running totals."""
        snapshots: list[Snapshot] = []
        for when in self.valuation_dates():
            state = self.state_engine.state_at(self.ledger, when)
            flows = self.cash_engine.flows(self.ledger, end=when)
            snapshots.append(Snapshot(
                date=when,
                total_value=state.total_value,
                cash=state.cash,
                securities_value=state.securities_value,
                cumulative_contributions=flows.deposits,
                cumulative_withdrawals=flows.withdrawals,
                cumulative_income=flows.income,
                cumulative_realised_gain=state.realised_gain,
                unrealised_gain=state.unrealised_gain,
                value_quality=state.value_quality,
            ))
        return snapshots

    def income(self) -> dict:
        rows = self.repo.rows(
            "SELECT i.payment_date, s.code, i.amount, i.rate_per_unit,"
            " i.franking_credit, i.tax_withheld FROM income_events i"
            " LEFT JOIN securities s USING (security_id)"
            " ORDER BY i.payment_date, s.code")
        gross = sum((Decimal(r["amount"]) for r in rows), ZERO)
        withheld = sum((Decimal(r["tax_withheld"]) for r in rows
                        if r["tax_withheld"] is not None), ZERO)
        franking = sum((Decimal(r["franking_credit"]) for r in rows
                        if r["franking_credit"] is not None), ZERO)
        interest = sum((e.net_amount or ZERO
                        for e in self.ledger.of_type(TxnType.INTEREST)), ZERO)

        # Trust distributions are franked too, but the tax report states those
        # credits only as annual per-security totals, so they are added at that
        # grain rather than attributed to individual payments.
        trust_franking = sum((Decimal(r["franking_credit"]) for r in self.repo.rows(
            "SELECT franking_credit FROM security_tax_details"
            " WHERE franking_credit IS NOT NULL")), ZERO)
        total_franking = franking + trust_franking
        cash_income = gross + interest

        return {
            "events": [dict(r) for r in rows],
            "gross_income": cash_income,
            "net_income": cash_income - withheld,
            # Franking credits are not cash: they are a tax offset. Grossed-up
            # income is what the ATO assesses, not what reached the account.
            "franking_credits": total_franking,
            "dividend_franking_credits": franking,
            "trust_franking_credits": trust_franking,
            "grossed_up_income": cash_income + total_franking,
            "tax_withheld": withheld,
            "franking_available": total_franking > ZERO,
        }

    def performance(self, start: date | None = None,
                    end: date | None = None) -> Performance:
        dates = self.reported_dates()
        if not dates:
            raise ValueError("no reported valuation dates to measure between")
        start = start or dates[0]
        end = end or dates[-1]
        window = [d for d in dates if start <= d <= end]

        external = self.cash_engine.external_flows(self.ledger)

        periods: list[PeriodReturn] = []
        for previous, current in zip(window, window[1:]):
            begin = self.state_engine.state_at(self.ledger, previous).total_value
            finish = self.state_engine.state_at(self.ledger, current).total_value
            flows = [(w, a) for w, a in external if previous < w <= current]
            periods.append(modified_dietz(begin, finish, flows, previous, current))

        twrr = time_weighted_return(periods)

        # Investor's perspective: money in is negative, money out positive, and
        # the closing value is a final receipt.
        #
        # The window opens at the first date the portfolio can be valued, which
        # is later than the first transaction. Whatever was already invested by
        # then enters as an opening outflow -- without it, contributions made
        # before the first valuation would be missing while the gains they
        # produced still counted, overstating the return.
        opening = self.state_engine.state_at(self.ledger, start).total_value
        terminal = self.state_engine.state_at(self.ledger, end).total_value
        flows_for_xirr = [(start, -opening)] if opening != ZERO else []
        flows_for_xirr += [(w, -a) for w, a in external if start < w <= end]
        flows_for_xirr.append((end, terminal))
        money_weighted = xirr(flows_for_xirr)

        decomposition = self._decompose(start, end, periods)
        return Performance(start=start, end=end, periods=periods, twrr=twrr,
                           twrr_annualised=annualised(twrr, start, end),
                           xirr=money_weighted, decomposition=decomposition)

    def _average_capital(self, periods: list[PeriodReturn]) -> Decimal:
        """Mean capital at work, used as the denominator for profit shares."""
        bases = [p.begin_value + p.weighted_flow for p in periods
                 if (p.begin_value + p.weighted_flow) > ZERO]
        return (sum(bases, ZERO) / Decimal(len(bases))) if bases else ZERO

    def _decompose(self, start: date, end: date,
                   periods: list[PeriodReturn]) -> ReturnDecomposition:
        state = self.state_engine.state_at(self.ledger, end)
        flows = self.cash_engine.flows(self.ledger, end=end)
        income = flows.income
        fees = abs(flows.fees)
        capital = state.realised_gain + state.unrealised_gain
        total = capital + income - (fees if self.config.returns_net_of_fees else ZERO)
        average_capital = self._average_capital(periods)
        return ReturnDecomposition(
            capital_growth=capital, income=income, fees=fees, total_gain=total,
            average_capital=average_capital,
            total_return_pct=(total / average_capital) if average_capital > ZERO else None)

    def attribution(self, on: date | None = None) -> Attribution:
        dates = self.reported_dates()
        when = on or dates[-1]
        state = self.state_engine.state_at(self.ledger, when)
        periods = self.performance(dates[0], when).periods
        average_capital = self._average_capital(periods)

        contributions = [Contribution(
            security_id=s.security_id, code=s.code or s.security_id,
            realised_gain=s.realised_gain,
            unrealised_gain=s.unrealised_gain or ZERO,
            income=s.income, fees=ZERO) for s in state.securities]

        # Cash earns interest and pays the account fees; it is a position too.
        interest = sum((e.net_amount or ZERO
                        for e in self.ledger.of_type(TxnType.INTEREST)
                        if e.trade_date <= when), ZERO)
        fees = abs(self.cash_engine.flows(self.ledger, end=when).fees)
        contributions.append(Contribution(
            security_id=None, code="Cash", realised_gain=ZERO,
            unrealised_gain=ZERO, income=interest, fees=fees))

        return Attribution(contributions=contributions, average_capital=average_capital)

    def reconcile(self) -> list[Check]:
        return Reconciler(self.repo, self.prices, self.config,
                          self.opening_cash).run(self.ledger)
