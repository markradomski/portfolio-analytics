"""Drawdowns, high-water marks and milestones, derived from the daily series.

Drawdown is measured on the flow-neutral growth index, not on portfolio value.
Value-based drawdown counts a withdrawal as a loss: this portfolio shows a 62%
value drawdown in August 2024 on a day its investments were at an all-time
high, because most of it had just been withdrawn. Both are recorded, and the
value-based figures keep their own columns, but episodes are detected on the
index because that is what "how far are my investments down" means.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.history.config import (DEFAULT_HISTORY_CONFIG, HistoryConfig,
                                ValuationStatus)
from src.history.generator import DailyRow
from src.ids import make_id

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True)
class DrawdownEpisode:
    episode_id: str
    peak_date: date
    peak_value: Decimal
    trough_date: date
    trough_value: Decimal
    drawdown_value: Decimal
    drawdown_pct: Decimal
    recovery_date: date | None
    recovery_days: int | None
    valuation_status: ValuationStatus


@dataclass(frozen=True)
class Milestone:
    milestone_id: str
    kind: str
    date: date
    value: Decimal | None
    description: str


def drawdown_episodes(rows: list[DailyRow],
                      config: HistoryConfig = DEFAULT_HISTORY_CONFIG
                      ) -> list[DrawdownEpisode]:
    """Peak, trough and recovery for each decline beyond the configured floor."""
    points = [(r.date, r.return_index, r.total_value) for r in rows
              if r.return_index is not None]
    if not points:
        return []

    episodes: list[DrawdownEpisode] = []
    peak = trough = points[0]
    in_drawdown = False

    for point in points[1:]:
        _, index, _ = point

        if in_drawdown and index >= peak[1]:
            episodes.append(_episode(peak, trough, recovery=point[0]))
            in_drawdown = False
            peak = trough = point
            continue

        if index > peak[1]:
            peak = trough = point
            continue

        # The index is carried forward between priced dates, so a run of equal
        # values is one observation repeated. The peak keeps the first date it
        # was reached rather than drifting to the last day at that level.
        if index == peak[1]:
            continue

        if index < trough[1] or trough[1] >= peak[1]:
            trough = point
        if (trough[1] / peak[1] - ONE).copy_abs() >= config.minimum_drawdown_pct:
            in_drawdown = True

    if in_drawdown:
        episodes.append(_episode(peak, trough, recovery=None))
    return episodes


def _episode(peak, trough, recovery: date | None) -> DrawdownEpisode:
    peak_date, peak_index, peak_value = peak
    trough_date, trough_index, trough_value = trough
    depth = trough_index / peak_index - ONE
    return DrawdownEpisode(
        episode_id=make_id("DD", peak_date, trough_date),
        peak_date=peak_date, peak_value=peak_value or ZERO,
        trough_date=trough_date, trough_value=trough_value or ZERO,
        drawdown_value=(trough_value or ZERO) - (peak_value or ZERO),
        drawdown_pct=depth, recovery_date=recovery,
        recovery_days=(recovery - trough_date).days if recovery else None,
        # The index only moves on dates the portfolio could be valued, so an
        # episode's dates are as precise as the underlying pricing allows.
        valuation_status=ValuationStatus.CALCULATED)


def milestones(rows: list[DailyRow], events,
               config: HistoryConfig = DEFAULT_HISTORY_CONFIG) -> list[Milestone]:
    """Notable moments. Thresholds come from configuration, never hard-coded."""
    from src.models import TxnType

    out: list[Milestone] = []
    valued = [r for r in rows if r.total_value is not None]
    if not valued:
        return out

    def add(kind: str, when: date, value: Decimal | None, description: str) -> None:
        out.append(Milestone(make_id("MS", kind, when), kind, when, value, description))

    first_buy = next((e for e in events if e.type is TxnType.BUY), None)
    if first_buy:
        add("FIRST_INVESTMENT", first_buy.trade_date, first_buy.net_amount,
            f"First investment: {first_buy.code or 'security'}")

    for threshold in config.value_milestones:
        crossing = next((r for r in valued if r.total_value >= threshold), None)
        if crossing:
            add("VALUE_THRESHOLD", crossing.date, threshold,
                f"Portfolio first reached ${threshold:,.0f}")

    peak = max(valued, key=lambda r: (r.total_value, r.date))
    add("ALL_TIME_HIGH", peak.date, peak.total_value,
        f"All-time high of ${peak.total_value:,.2f}")

    deposits = [e for e in events if e.type is TxnType.DEPOSIT]
    if deposits:
        largest = max(deposits, key=lambda e: (e.net_amount or ZERO, e.event_id))
        add("LARGEST_CONTRIBUTION", largest.cash_date, largest.net_amount,
            f"Largest contribution: ${largest.net_amount:,.2f}")

    withdrawals = [e for e in events if e.type is TxnType.WITHDRAWAL]
    if withdrawals:
        largest = min(withdrawals, key=lambda e: (e.net_amount or ZERO, e.event_id))
        add("LARGEST_WITHDRAWAL", largest.cash_date, largest.net_amount,
            f"Largest withdrawal: ${abs(largest.net_amount):,.2f}")

    income = [e for e in events
              if e.type in (TxnType.DIVIDEND, TxnType.DISTRIBUTION)]
    if income:
        largest = max(income, key=lambda e: (e.net_amount or ZERO, e.event_id))
        add("LARGEST_INCOME", largest.cash_date, largest.net_amount,
            f"Largest income payment: ${largest.net_amount:,.2f}"
            f" from {largest.code or 'a holding'}")

    # The growth index only moves between dates the portfolio could be valued,
    # so the largest move is reported over the interval it actually spans
    # rather than being attributed to a single day it cannot be pinned to.
    steps = [(r.date, r.return_index) for r in rows if r.return_index is not None]
    changes = [(current[0], previous[0], current[1] / previous[1] - ONE)
               for previous, current in zip(steps, steps[1:])
               if previous[1] != current[1] and previous[1] > ZERO]
    if changes:
        best = max(changes, key=lambda c: c[2])
        worst = min(changes, key=lambda c: c[2])
        add("LARGEST_GAIN", best[0], best[2] * 100,
            f"Largest measured gain: {best[2] * 100:.2f}% over the period ending {best[0]}")
        add("LARGEST_LOSS", worst[0], worst[2] * 100,
            f"Largest measured loss: {worst[2] * 100:.2f}% over the period ending {worst[0]}")

    return out
