"""Historical layer configuration.

Asset classes are defined here rather than in the accounting engine: how a
portfolio is grouped for reporting is a presentation decision, and the engine
must not depend on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from src.models import SecurityType


class AssetClass(str, Enum):
    AUSTRALIAN_EQUITIES = "australian_equities"
    INTERNATIONAL_EQUITIES = "international_equities"
    BONDS = "bonds"
    PROPERTY = "property"
    CASH = "cash"
    # A security positively identified as belonging to a category outside the
    # above -- reserved for an actual classification decision, never used as
    # a stand-in for "we don't know". See UNKNOWN.
    OTHER = "other"
    # No classification exists for this security: not in the configured
    # ticker map, and its security type has no fallback mapping either.
    # Semantically distinct from OTHER (hardening sec 6) -- "Other" implies a
    # deliberate classification choice was made; "Unknown" says none was.
    UNKNOWN = "unknown"


class ValuationStatus(str, Enum):
    """How a historical value was arrived at. Never inferred optimistically."""
    ACTUAL = "actual"            # Vanguard reported this figure for this date
    CALCULATED = "calculated"    # units x a price quoted on this date
    ESTIMATED = "estimated"      # units x the most recent earlier price
    UNAVAILABLE = "unavailable"  # no price at or before this date


class Granularity(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# Seed mapping by ticker. Anything unlisted is classified from its security
# type, and anything still unknown becomes OTHER rather than being guessed into
# a class it might not belong to.
DEFAULT_ASSET_CLASSES: dict[str, AssetClass] = {
    "VAS": AssetClass.AUSTRALIAN_EQUITIES,
    "VAF": AssetClass.BONDS,
    "VGS": AssetClass.INTERNATIONAL_EQUITIES,
    "VGAD": AssetClass.INTERNATIONAL_EQUITIES,
    "VGE": AssetClass.INTERNATIONAL_EQUITIES,
    "BHP": AssetClass.AUSTRALIAN_EQUITIES,
    "RIO": AssetClass.AUSTRALIAN_EQUITIES,
    "WTC": AssetClass.AUSTRALIAN_EQUITIES,
    # Fictional tickers used only by the public-release synthetic demo
    # dataset (see tools/generate_demo_data.py) -- classified the same way
    # a real ETF of that description would be.
    "DAU": AssetClass.AUSTRALIAN_EQUITIES,
    "DIS": AssetClass.INTERNATIONAL_EQUITIES,
    "DFI": AssetClass.BONDS,
}

TYPE_FALLBACK = {
    SecurityType.SHARE: AssetClass.AUSTRALIAN_EQUITIES,
    SecurityType.CASH: AssetClass.CASH,
}


@dataclass(frozen=True)
class HistoryConfig:
    asset_classes: dict[str, AssetClass] = field(
        default_factory=lambda: dict(DEFAULT_ASSET_CLASSES))

    # Milestone thresholds. Configurable, with no magic numbers in the detector.
    value_milestones: tuple[Decimal, ...] = (
        Decimal("10000"), Decimal("25000"), Decimal("50000"),
        Decimal("100000"), Decimal("250000"), Decimal("500000"),
        Decimal("1000000"))

    # A drawdown episode is only recorded once it exceeds this, to avoid
    # cluttering the series with noise.
    minimum_drawdown_pct: Decimal = Decimal("0.05")


DEFAULT_HISTORY_CONFIG = HistoryConfig()


def classify(code: str | None, security_type: str | None,
             config: HistoryConfig = DEFAULT_HISTORY_CONFIG) -> AssetClass:
    if code and code in config.asset_classes:
        return config.asset_classes[code]
    if security_type:
        try:
            return TYPE_FALLBACK.get(SecurityType(security_type), AssetClass.UNKNOWN)
        except ValueError:
            pass
    return AssetClass.UNKNOWN
