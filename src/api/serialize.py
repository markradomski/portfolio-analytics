"""JSON serialisation for API responses.

Decimals are serialised as strings, never floats: converting to float would
introduce IEEE754 rounding into a value that the accounting engine computed
exactly, and the frontend formatting layer must receive the same precision
Phase 4 produced. This is the one rule the whole frontend architecture
depends on -- see docs/api.md "Precision over the wire".
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def to_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        # Include @property-derived fields (e.g. Metric.available,
        # ReconciliationResult.status alias) alongside declared fields, so
        # the API surface matches what Python callers already rely on.
        data = {f.name: to_json(getattr(value, f.name))
               for f in dataclasses.fields(value)}
        for name in dir(type(value)):
            if name.startswith("_") or name in data:
                continue
            attr = getattr(type(value), name, None)
            if isinstance(attr, property):
                try:
                    data[name] = to_json(getattr(value, name))
                except Exception:
                    pass
        return data
    if hasattr(value, "to_dict"):
        return to_json(value.to_dict())
    if isinstance(value, dict):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json(v) for v in value]
    return value
