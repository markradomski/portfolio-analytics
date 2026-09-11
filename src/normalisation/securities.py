"""Normalise security identifiers and infer instrument type.

Vanguard writes the same instrument several ways depending on which table it
appears in: 'VAS' in a holdings table, 'VAS.AX' or 'WTC.XASX.AU' in a
distribution line, and as a bracketed suffix in a trade row.
"""

from __future__ import annotations

import re

from src.models import SecurityType

# Trailing exchange/market qualifiers to drop: .AX, .XASX.AU, .ASX
_SUFFIX = re.compile(r"\.(AX|ASX|XASX)(\.[A-Z]{2})?$", re.I)

_ASSET_CLASS_TO_TYPE = {
    "etf": SecurityType.ETF,
    "australian_share": SecurityType.SHARE,
    "managed_fund": SecurityType.MANAGED_FUND,
    "cash": SecurityType.CASH,
}


def normalise_code(raw: str | None) -> str | None:
    """'WTC.XASX.AU' -> 'WTC'. Returns None if nothing usable remains."""
    if not raw:
        return None
    code = _SUFFIX.sub("", raw.strip().upper())
    code = re.sub(r"[^A-Z0-9]", "", code)
    return code or None


def security_type_for(asset_class: str | None, name: str = "") -> SecurityType:
    """Prefer the statement's own section heading; fall back to the name."""
    if asset_class in _ASSET_CLASS_TO_TYPE:
        return _ASSET_CLASS_TO_TYPE[asset_class]
    lowered = name.lower()
    if "etf" in lowered:
        return SecurityType.ETF
    if "fund" in lowered:
        return SecurityType.MANAGED_FUND
    return SecurityType.SHARE
