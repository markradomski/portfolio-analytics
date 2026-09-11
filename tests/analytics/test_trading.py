"""Turnover and trading activity must never count the cash leg of a trade
(TRANSFER) as trading activity itself (sec 16-17)."""

from datetime import date
from decimal import Decimal as D

from src.analytics.config import AnalyticsConfig, TurnoverMethod
from src.analytics.trading import trading_activity, trading_activity_by, turnover


def test_transfers_are_never_counted_as_trades(built):
    """The synthetic statement has 2 BUYs and 2 matching TRANSFERs; activity
    must report exactly 2 trades, not 4."""
    activity = trading_activity(built)
    assert activity.buy_count == 2
    assert activity.sell_count == 0


def test_turnover_uses_the_lesser_of_buys_and_sells_by_default(history):
    """A portfolio with only buys and no sells has zero turnover under the
    default (lesser-of) convention, since min(purchases, 0) = 0."""
    result = turnover(history, history.repo, date(2024, 6, 30), date(2024, 9, 30))
    assert result.value == D("0")


def test_turnover_total_traded_method_differs_from_the_default(history):
    lesser = turnover(history, history.repo, date(2024, 6, 30), date(2024, 9, 30))
    total = turnover(history, history.repo, date(2024, 6, 30), date(2024, 9, 30),
                     AnalyticsConfig(turnover_method=TurnoverMethod.TOTAL_TRADED))
    assert lesser.value != total.value
    assert total.value > lesser.value


def test_trading_activity_by_year_sums_to_lifetime(built):
    lifetime = trading_activity(built)
    by_year = trading_activity_by(built, "year")
    assert sum(row["buys"] for row in by_year) == lifetime.buy_count
    assert sum(row["sells"] for row in by_year) == lifetime.sell_count
