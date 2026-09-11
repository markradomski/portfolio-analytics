"""Reconcile calculated figures against what Vanguard reported.

Nothing here adjusts a calculated value to match a reported one. A discrepancy
is reported, with both numbers, so it can be investigated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.database.repository import Repository
from src.engine.config import DEFAULT_CONFIG, EngineConfig
from src.engine.ledger import Ledger
from src.engine.state import StateEngine

ZERO = Decimal("0")


@dataclass(frozen=True)
class Check:
    when: date
    subject: str              # "portfolio value", "cash", or a ticker
    expected: Decimal | None  # as reported by Vanguard
    calculated: Decimal | None
    tolerance: Decimal

    @property
    def difference(self) -> Decimal | None:
        if self.expected is None or self.calculated is None:
            return None
        return self.calculated - self.expected

    @property
    def passed(self) -> bool:
        difference = self.difference
        return difference is not None and abs(difference) <= self.tolerance

    @property
    def status(self) -> str:
        if self.difference is None:
            return "SKIP"
        return "PASS" if self.passed else "FAIL"


class Reconciler:
    def __init__(self, repo: Repository, prices, config: EngineConfig = DEFAULT_CONFIG,
                 opening_cash: Decimal = ZERO):
        self.repo = repo
        self.config = config
        self.state = StateEngine(prices, config, opening_cash)

    def _reported_valuations(self) -> list[tuple[date, Decimal, Decimal | None, Decimal | None]]:
        return [(date.fromisoformat(r["reporting_date"]),
                 Decimal(r["portfolio_value"]),
                 Decimal(r["cash_balance"]) if r["cash_balance"] is not None else None,
                 Decimal(r["accrued_income"]) if r["accrued_income"] is not None else None)
                for r in self.repo.rows(
                    "SELECT reporting_date, portfolio_value, cash_balance,"
                    " accrued_income FROM portfolio_valuations"
                    " ORDER BY reporting_date")]

    def _reported_units(self, when: date) -> dict[str, tuple[str, Decimal]]:
        return {r["security_id"]: (r["code"], Decimal(r["units"]))
                for r in self.repo.rows(
                    "SELECT h.security_id, s.code, h.units FROM holdings h"
                    " JOIN securities s USING (security_id)"
                    " WHERE h.reporting_date = ?", (when.isoformat(),))}

    def run(self, ledger: Ledger) -> list[Check]:
        checks: list[Check] = []
        tolerance = self.config.reconciliation_tolerance

        for when, reported_value, reported_cash, accrued in self._reported_valuations():
            state = self.state.state_at(ledger, when)

            # Vanguard's portfolio value includes income declared but not yet
            # received, which sits in neither holdings nor the cash balance.
            calculated = state.total_value + (accrued or ZERO)
            checks.append(Check(when, "portfolio value", reported_value,
                                calculated, tolerance))

            if reported_cash is not None:
                checks.append(Check(when, "cash", reported_cash, state.cash, tolerance))

            reported_units = self._reported_units(when)
            calculated_units = {s.security_id: s.units for s in state.securities}
            for security_id in sorted(set(reported_units) | set(calculated_units)):
                code, expected = reported_units.get(security_id, (None, ZERO))
                if code is None:
                    code = next((s.code for s in state.securities
                                 if s.security_id == security_id), security_id)
                checks.append(Check(
                    when, f"units {code}", expected,
                    calculated_units.get(security_id, ZERO), tolerance))

        return checks


def summarise(checks: list[Check]) -> dict[str, int]:
    return {
        "total": len(checks),
        "passed": sum(1 for c in checks if c.status == "PASS"),
        "failed": sum(1 for c in checks if c.status == "FAIL"),
        "skipped": sum(1 for c in checks if c.status == "SKIP"),
    }
