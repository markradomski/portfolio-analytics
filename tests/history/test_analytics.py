from datetime import date, timedelta
from decimal import Decimal as D

from src.history.analytics import drawdown_episodes, milestones
from src.history.config import HistoryConfig

from tests.history.conftest import row, series


def test_peak_decline_recovery():
    """100 -> 120 (peak) -> 90 (trough) -> 125 (recovered)."""
    rows = series([100, 110, 120, 110, 100, 90, 100, 115, 125])
    episodes = drawdown_episodes(rows)
    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.peak_date == date(2024, 1, 3)      # first day at 120
    assert episode.trough_date == date(2024, 1, 6)    # first day at 90
    assert episode.drawdown_pct == D("-0.25")
    assert episode.recovery_date == date(2024, 1, 9)
    assert episode.recovery_days == 3


def test_unrecovered_drawdown_has_no_recovery_date():
    episodes = drawdown_episodes(series([100, 120, 80, 85]))
    assert len(episodes) == 1
    assert episodes[0].recovery_date is None
    assert episodes[0].recovery_days is None


def test_shallow_dips_are_not_episodes():
    """A 2% wobble is noise, not a drawdown."""
    assert drawdown_episodes(series([100, 99, 98, 100, 101])) == []


def test_threshold_is_configurable():
    config = HistoryConfig(minimum_drawdown_pct=D("0.01"))
    assert len(drawdown_episodes(series([100, 98, 100]), config)) == 1


def test_peak_keeps_its_first_date_through_flat_stretches():
    """The index is carried forward between valuations, so a run of equal
    values is one observation repeated -- not a peak that keeps moving."""
    rows = series([100, 120, 120, 120, 90, 130])
    assert drawdown_episodes(rows)[0].peak_date == date(2024, 1, 2)


def test_milestones_use_configured_thresholds():
    config = HistoryConfig(value_milestones=(D("150"),))
    rows = series([100, 140, 160, 200])
    kinds = {m.kind: m for m in milestones(rows, [], config)}
    assert kinds["VALUE_THRESHOLD"].date == date(2024, 1, 3)
    assert kinds["ALL_TIME_HIGH"].date == date(2024, 1, 4)


def test_no_milestones_without_a_valued_portfolio():
    rows = [row(date(2024, 1, 1), value=None)]
    assert milestones(rows, []) == []
