"""Realised/unrealised gains (sec 8, reusing UnrealisedGainSnapshot from
holdings.py since it's a holdings-shaped concept -- kept here for the
lifetime/period summary that isn't)."""

from __future__ import annotations

from src.api.models.common import ApiModel, DecimalString, ISODate


class RealisedGainSummary(ApiModel):
    period_start: ISODate
    period_end: ISODate
    realised_gain: DecimalString
    realised_loss: DecimalString
    net_realised_gain: DecimalString


class SecurityRealisedGain(ApiModel):
    security_id: str
    code: str | None = None
    units_sold: DecimalString
    proceeds: DecimalString
    cost_basis: DecimalString
    realised_gain: DecimalString


class GainAttribution(ApiModel):
    unrealised_gains: DecimalString
    realised_gains: DecimalString
    income: DecimalString
    total: DecimalString
