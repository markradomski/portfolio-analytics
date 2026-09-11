"""Engine configuration.

Every accounting assumption lives here rather than being scattered through the
calculation code, so a reviewer can see in one place what the numbers mean.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class CostBasisMethod(str, Enum):
    AVERAGE_COST = "average_cost"
    TAX_LOT = "tax_lot"          # FIFO parcels


class ValuationFrequency(str, Enum):
    EVENT = "event"              # value on every date something happened
    QUARTERLY = "quarterly"      # value only on reported statement dates


@dataclass(frozen=True)
class EngineConfig:
    currency: str = "AUD"
    cost_basis_method: CostBasisMethod = CostBasisMethod.AVERAGE_COST
    valuation_frequency: ValuationFrequency = ValuationFrequency.EVENT
    rounding_precision: int = 2

    # Reported figures are rounded to cents; allow a little slack per component.
    reconciliation_tolerance: Decimal = Decimal("0.05")

    # Vanguard reports "return after withholding tax and fees", so netting fees
    # off is what makes calculated returns comparable to the statements.
    returns_net_of_fees: bool = True

    # Holdings move on trade date; cash moves on settlement date. The statements
    # themselves follow this split, and mixing them breaks both reconciliations.
    holdings_use_trade_date: bool = True
    cash_uses_settlement_date: bool = True


DEFAULT_CONFIG = EngineConfig()
