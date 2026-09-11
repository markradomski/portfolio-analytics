"""Turnover and trading activity (sec 16-17).

Reads transactions directly rather than through Phase 3 (which stores state,
not activity), and never counts internal cash-leg TRANSFER rows as trading --
BUY/SELL are the trade events; TRANSFER is their cash effect (see
docs/timing.md).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analytics.config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig, TurnoverMethod
from src.analytics.result import DataQuality, Metric, unavailable
from src.database.repository import Repository
from src.history.service import HistoryService

ZERO = Decimal("0")


def _dec(v):
    return None if v is None else Decimal(v)


@dataclass(frozen=True)
class TradingActivity:
    period_start: date
    period_end: date
    buy_count: int
    sell_count: int
    total_purchase_value: Decimal
    total_sale_value: Decimal
    average_trade_size: Decimal | None
    largest_trade_value: Decimal | None
    largest_trade_security: str | None
    most_traded_security: str | None
    most_traded_count: int


def trading_activity(repo: Repository, start: date | None = None,
                     end: date | None = None) -> TradingActivity:
    clauses, params = ["t.type IN ('BUY','SELL')"], []
    if start:
        clauses.append("t.trade_date >= ?"); params.append(start.isoformat())
    if end:
        clauses.append("t.trade_date <= ?"); params.append(end.isoformat())
    rows = repo.rows(
        "SELECT t.type, t.trade_date, t.net_amount, s.code FROM transactions t"
        " LEFT JOIN securities s USING (security_id)"
        f" WHERE {' AND '.join(clauses)}", tuple(params))

    buys = [r for r in rows if r["type"] == "BUY"]
    sells = [r for r in rows if r["type"] == "SELL"]
    buy_value = sum((abs(_dec(r["net_amount"]) or ZERO) for r in buys), ZERO)
    sell_value = sum((abs(_dec(r["net_amount"]) or ZERO) for r in sells), ZERO)
    all_values = [(abs(_dec(r["net_amount"]) or ZERO), r["code"]) for r in rows]
    largest = max(all_values, default=(None, None), key=lambda x: x[0] or ZERO)
    security_counts = Counter(r["code"] for r in rows if r["code"])
    most_traded = security_counts.most_common(1)

    dates = [date.fromisoformat(r["trade_date"]) for r in rows]
    return TradingActivity(
        period_start=start or (min(dates) if dates else date.today()),
        period_end=end or (max(dates) if dates else date.today()),
        buy_count=len(buys), sell_count=len(sells),
        total_purchase_value=buy_value, total_sale_value=sell_value,
        average_trade_size=((buy_value + sell_value) / len(rows)) if rows else None,
        largest_trade_value=largest[0], largest_trade_security=largest[1],
        most_traded_security=most_traded[0][0] if most_traded else None,
        most_traded_count=most_traded[0][1] if most_traded else 0)


def trading_activity_by(repo: Repository, granularity: str = "year") -> list[dict]:
    """Trading activity bucketed by month/quarter/year (sec 17)."""
    fmt = {"year": lambda d: d[:4], "quarter": lambda d: f"{d[:4]}Q{(int(d[5:7])-1)//3+1}",
          "month": lambda d: d[:7]}[granularity]
    rows = repo.rows(
        "SELECT type, trade_date, net_amount FROM transactions"
        " WHERE type IN ('BUY','SELL') ORDER BY trade_date")
    buckets: dict[str, dict] = defaultdict(lambda: {"buys": 0, "sells": 0,
                                                     "buy_value": ZERO, "sell_value": ZERO})
    for row in rows:
        key = fmt(row["trade_date"])
        bucket = buckets[key]
        amount = abs(_dec(row["net_amount"]) or ZERO)
        if row["type"] == "BUY":
            bucket["buys"] += 1; bucket["buy_value"] += amount
        else:
            bucket["sells"] += 1; bucket["sell_value"] += amount
    return [{"period": k, "buys": v["buys"], "sells": v["sells"],
            "buy_value": str(v["buy_value"]), "sell_value": str(v["sell_value"])}
            for k, v in sorted(buckets.items())]


def turnover(service: HistoryService, repo: Repository, start: date, end: date,
            config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> Metric:
    """turnover = min(purchases, sales) / average portfolio value, the
    standard convention -- a simple rebalance (sell X, buy X) is 100%
    turnover under this method, not 200%, since only the smaller side counts.
    TurnoverMethod.TOTAL_TRADED gives the (buys + sales) / average value
    alternative when that convention is wanted instead. Internal transfers
    (TRANSFER, the cash leg of a trade) are never counted -- only BUY/SELL.
    """
    activity = trading_activity(repo, start, end)
    rows = service.portfolio_history(start, end)
    valued = [Decimal(r["total_value"]) for r in rows if r["total_value"]]
    if not valued:
        return unavailable("turnover", config.turnover_method.value,
                           "no valued days in the period", period_start=start,
                           period_end=end)
    average_value = sum(valued, ZERO) / Decimal(len(valued))
    if average_value <= ZERO:
        return unavailable("turnover", config.turnover_method.value,
                           "average portfolio value was zero or negative")

    if config.turnover_method is TurnoverMethod.LESSER_OF_BUYS_SELLS:
        numerator = min(activity.total_purchase_value, activity.total_sale_value)
        formula = "min(purchases, sales) / average_portfolio_value"
    else:
        numerator = activity.total_purchase_value + activity.total_sale_value
        formula = "(purchases + sales) / average_portfolio_value"

    quality = (DataQuality.ACTUAL if len(valued) == len(rows) and rows
              else DataQuality.ESTIMATED)
    return Metric(name="turnover", value=numerator / average_value,
                 methodology=formula, data_quality=quality,
                 period_start=start, period_end=end, currency=config.currency,
                 note=f"purchases {activity.total_purchase_value}, sales"
                      f" {activity.total_sale_value}, average value {average_value:.2f}")
