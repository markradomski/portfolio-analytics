"""Contributions and cash (sec 8). Contributions/withdrawals are kept
structurally separate from investment_growth in every field name here --
the frontend must never be tempted to add them together and call it a
return (see docs/analytics.md and sec 21's explicit prohibition)."""

from __future__ import annotations

from src.api.models.common import ApiModel, DecimalString, ISODate


class ContributionSummary(ApiModel):
    total_contributed: DecimalString
    total_withdrawn: DecimalString
    net_contributed: DecimalString
    investment_growth: DecimalString | None = None
    income_received: DecimalString
    current_value: DecimalString | None = None
    as_at: ISODate


class ContributionHistoryRow(ApiModel):
    """One bucket of history.contribution_history() -- per-period flows plus
    running totals (sec 8's contributions family, history variant)."""
    period_end: ISODate
    contributions: DecimalString
    withdrawals: DecimalString
    net_contributions: DecimalString
    cumulative_contributions: DecimalString
    cumulative_withdrawals: DecimalString
    cumulative_net: DecimalString
