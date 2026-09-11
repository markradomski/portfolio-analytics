"""getAnalyticsCapabilities() (sec 6): the single typed contract the
frontend uses to decide whether a metric/period/chart can be shown. React
must never recreate this decision with a rule like `if (years < 1)` --
every availability question resolves to one lookup in this response."""

from __future__ import annotations

from src.api.models.common import ApiModel, Capability

AnalyticsCapabilities = dict[str, Capability]
