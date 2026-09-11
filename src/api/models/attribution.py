"""Growth decomposition, security attribution, and the attribution tree
(sec 8: Attribution family)."""

from __future__ import annotations

from src.api.models.common import ApiModel, DecimalString, ISODate


class SecurityAttributionRow(ApiModel):
    """A security's OWN return (total_return) is kept distinct from its
    SHARE of the portfolio's return (portfolio_contribution) -- collapsing
    these into one field was the exact confusion sec 7 (Phase 4) exists to
    prevent: a small, high-return holding must show a high own-return and a
    small contribution, never the same number for both."""
    security_id: str
    code: str
    opening_value: DecimalString
    closing_value: DecimalString
    capital_gain: DecimalString
    income: DecimalString
    fees: DecimalString
    total_return: DecimalString | None = None
    portfolio_contribution: DecimalString | None = None
    portfolio_weight: DecimalString | None = None


class AttributionPeriod(ApiModel):
    start: ISODate
    end: ISODate


class AttributionIncome(ApiModel):
    dividends: DecimalString
    distributions: DecimalString
    interest: DecimalString


class AttributionCapitalAppreciation(ApiModel):
    total: DecimalString
    securities: dict[str, DecimalString]


class AttributionInvestmentReturn(ApiModel):
    total: DecimalString
    capital_appreciation: AttributionCapitalAppreciation
    income: AttributionIncome


class AttributionCash(ApiModel):
    """Cash is represented explicitly in the tree (Phase 4 hardening sec 5)
    -- never silently excluded just because it isn't a security. data_quality
    is "unavailable" rather than the fields being absent, when cash's own
    contribution genuinely cannot be computed."""
    interest_income: DecimalString | None = None
    fees: DecimalString | None = None
    profit: DecimalString | None = None
    data_quality: str  # "calculated" | "unavailable"


class AttributionTree(ApiModel):
    period: AttributionPeriod
    external_cash_flows: DecimalString
    investment_return: AttributionInvestmentReturn
    cash: AttributionCash
    fees: DecimalString
    taxes: DecimalString
    other_adjustments: DecimalString
