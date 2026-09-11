"""Income analytics (sec 8: Income family). Preserves the gross/tax-withheld/
net distinction, and franking credits where the annual tax reports supply
them (see docs/analytics.md 'Franking credits' -- never fabricated when
absent)."""

from __future__ import annotations

from src.api.models.common import ApiModel, DecimalString, ISODate, Metric


class IncomeRow(ApiModel):
    period_end: ISODate
    code: str | None = None
    dividends: DecimalString | None = None
    distributions: DecimalString | None = None
    interests: DecimalString | None = None
    gross_income: DecimalString
    franking_credits: DecimalString
    tax_withheld: DecimalString
    net_income: DecimalString


class IncomeGrowthRow(ApiModel):
    year: str
    gross_income: DecimalString
    growth_pct: DecimalString | None = None
    decomposition: str


class IncomeYieldResponse(ApiModel):
    trailing: Metric
    forward: Metric
