"""Return calculations.

Two returns, answering different questions, and never interchangeable:

* Time-weighted (TWRR) measures the investments, ignoring when money was added
  or removed. It is what you compare against a benchmark.
* Money-weighted (XIRR) measures the investor's actual experience, and is
  sensitive to the timing and size of contributions.

TWRR is computed as Modified Dietz within each sub-period, chained across
sub-periods. True TWRR revalues the portfolio at every external cash flow;
that needs a price on each flow date, and the statements only provide
quarter-end prices. Modified Dietz weights each flow by the fraction of the
period it was invested for, which is the standard approximation when valuations
are periodic. The approximation is exact when no flows occur mid-period.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, DivisionByZero, InvalidOperation

ZERO = Decimal("0")
ONE = Decimal("1")
DAYS_PER_YEAR = Decimal("365")


@dataclass(frozen=True)
class PeriodReturn:
    start: date
    end: date
    begin_value: Decimal
    end_value: Decimal
    external_flow: Decimal
    weighted_flow: Decimal
    ret: Decimal | None          # None when the period cannot be measured

    @property
    def gain(self) -> Decimal:
        return self.end_value - self.begin_value - self.external_flow


def modified_dietz(begin_value: Decimal, end_value: Decimal,
                   flows: list[tuple[date, Decimal]],
                   start: date, end: date) -> PeriodReturn:
    """Return over one period, weighting each flow by its time invested."""
    total_days = Decimal((end - start).days or 1)
    net_flow = sum((amount for _, amount in flows), ZERO)

    weighted = ZERO
    for when, amount in flows:
        remaining = Decimal((end - when).days)
        weighted += amount * (remaining / total_days)

    denominator = begin_value + weighted
    gain = end_value - begin_value - net_flow

    if denominator <= ZERO:
        # No capital at risk to earn a return on. Reported rather than forced
        # to zero, so callers can tell "flat" from "unmeasurable".
        ret = None
    else:
        ret = gain / denominator

    return PeriodReturn(start, end, begin_value, end_value, net_flow, weighted, ret)


def time_weighted_return(periods: list[PeriodReturn]) -> Decimal | None:
    """Chain sub-period returns: (1+r1)(1+r2)... - 1."""
    measurable = [p for p in periods if p.ret is not None]
    if not measurable:
        return None
    compound = ONE
    for period in measurable:
        compound *= (ONE + period.ret)
    return compound - ONE


def annualised(total_return: Decimal | None, start: date, end: date) -> Decimal | None:
    """Convert a cumulative return to a per-annum rate."""
    if total_return is None:
        return None
    years = Decimal((end - start).days) / DAYS_PER_YEAR
    if years <= ZERO:
        return None
    base = ONE + total_return
    if base <= ZERO:
        return None
    return Decimal(str(float(base) ** (1 / float(years)))) - ONE


def xirr(cash_flows: list[tuple[date, Decimal]], *,
         guess_low: float = -0.9999, guess_high: float = 10.0,
         tolerance: float = 1e-9, max_iterations: int = 200) -> Decimal | None:
    """Money-weighted return: the rate at which the cash flows net to zero.

    Solved by bisection rather than Newton's method: bisection cannot diverge,
    and always takes the same number of steps for the same input, which keeps
    the engine deterministic.

    Sign convention is the investor's: money paid in is negative, money received
    (including the terminal portfolio value) is positive.
    """
    flows = sorted(cash_flows)
    if len(flows) < 2:
        return None
    if not (any(a > ZERO for _, a in flows) and any(a < ZERO for _, a in flows)):
        return None            # all one direction: no rate solves it

    origin = flows[0][0]
    points = [((when - origin).days / 365.0, float(amount)) for when, amount in flows]

    def npv(rate: float) -> float:
        return sum(amount / ((1.0 + rate) ** years) for years, amount in points)

    low, high = guess_low, guess_high
    npv_low, npv_high = npv(low), npv(high)
    if npv_low * npv_high > 0:
        return None            # no sign change in range: no solution to find

    for _ in range(max_iterations):
        mid = (low + high) / 2
        value = npv(mid)
        if abs(value) < tolerance:
            break
        if npv_low * value <= 0:
            high = mid
        else:
            low, npv_low = mid, value
    else:
        mid = (low + high) / 2

    return Decimal(str(round(mid, 10)))


@dataclass(frozen=True)
class ReturnDecomposition:
    """Where the money came from, separated from money put in."""
    capital_growth: Decimal        # realised + unrealised
    income: Decimal                # dividends, distributions, interest
    fees: Decimal                  # positive number, already deducted if net
    total_gain: Decimal
    average_capital: Decimal
    total_return_pct: Decimal | None

    @property
    def capital_growth_pct(self) -> Decimal | None:
        if self.average_capital <= ZERO:
            return None
        return self.capital_growth / self.average_capital

    @property
    def income_return_pct(self) -> Decimal | None:
        if self.average_capital <= ZERO:
            return None
        return self.income / self.average_capital
