"""Risk metrics must refuse to fabricate precision the data can't support:
UNAVAILABLE rather than a number, when there's no risk-free rate, no
benchmark, or too few observations (sec 24-28, 43)."""

from decimal import Decimal as D

import pytest

from src.analytics.config import AnalyticsConfig, ReturnFrequency
from src.analytics.result import DataQuality
from src.analytics.risk import (beta, correlation, sharpe_ratio, sortino_ratio,
                                volatility)
from src.history.service import HistoryService
from tests.analytics.conftest import history as _history  # noqa: F401


def test_daily_volatility_is_unavailable_against_quarterly_pricing(history):
    """This synthetic statement (and the real portfolio) is priced far too
    coarsely to support a genuine daily return series."""
    config = AnalyticsConfig(risk_return_frequency=ReturnFrequency.DAILY)
    result = volatility(history, config)
    assert result.data_quality is DataQuality.UNAVAILABLE
    assert result.value is None


def test_quarterly_volatility_needs_a_minimum_sample(history):
    """One quarterly statement gives one observation -- nowhere near enough
    for a meaningful standard deviation."""
    config = AnalyticsConfig(minimum_observations_for_risk_metrics=6)
    result = volatility(history, config)
    assert result.data_quality is DataQuality.UNAVAILABLE
    assert "observations" in (result.note or "")


def test_sharpe_needs_an_explicit_risk_free_rate(history):
    """No configured rate must report UNAVAILABLE, never assume 0%."""
    result = sharpe_ratio(history)
    assert result.data_quality is DataQuality.UNAVAILABLE
    assert "risk_free_rate" in result.note or "risk-free" in result.note


def test_sortino_needs_an_explicit_risk_free_rate(history):
    result = sortino_ratio(history)
    assert result.data_quality is DataQuality.UNAVAILABLE


def test_beta_needs_a_registered_benchmark(history):
    result = beta(history, None)
    assert result.data_quality is DataQuality.UNAVAILABLE
    assert "benchmark" in result.note


def test_correlation_needs_a_registered_benchmark(history):
    result = correlation(history, None)
    assert result.data_quality is DataQuality.UNAVAILABLE


def test_risk_metrics_are_deterministic(history):
    """Same inputs, same config, same output -- called twice."""
    config = AnalyticsConfig(risk_free_rate_annual=D("0.04"))
    first = sharpe_ratio(history, config)
    second = sharpe_ratio(history, config)
    assert first.value == second.value
    assert first.data_quality == second.data_quality
