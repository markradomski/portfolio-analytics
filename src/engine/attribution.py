"""Return attribution.

Each security's contribution is its share of the portfolio's profit, expressed
over the same denominator as the portfolio return:

    contribution_i = pnl_i / average_capital
    pnl_i          = realised gain + unrealised gain + income - fees

Because the parts of pnl sum to the whole, the contributions sum exactly to the
portfolio return -- there is no residual to explain away. This is a profit-share
attribution and is consistent with the money-weighted return, not the
time-weighted one. It answers "how much money did VAS make for this portfolio",
which is a different question from "how did VAS perform".

A Brinson-style decomposition into allocation and selection effects needs
benchmark weights, and belongs with the benchmark work in Phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True)
class Contribution:
    security_id: str | None
    code: str
    realised_gain: Decimal
    unrealised_gain: Decimal
    income: Decimal
    fees: Decimal

    @property
    def profit(self) -> Decimal:
        return self.realised_gain + self.unrealised_gain + self.income - self.fees

    def contribution_pct(self, average_capital: Decimal) -> Decimal | None:
        if average_capital <= ZERO:
            return None
        return self.profit / average_capital


@dataclass(frozen=True)
class Attribution:
    contributions: list[Contribution]
    average_capital: Decimal

    @property
    def total_profit(self) -> Decimal:
        return sum((c.profit for c in self.contributions), ZERO)

    @property
    def total_pct(self) -> Decimal | None:
        if self.average_capital <= ZERO:
            return None
        return self.total_profit / self.average_capital

    def ranked(self) -> list[Contribution]:
        """Largest contributor first; ties broken by code so output is stable."""
        return sorted(self.contributions,
                      key=lambda c: (-c.profit, c.code))
