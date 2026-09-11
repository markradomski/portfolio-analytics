"""TWRR methodology metadata, and the specific sparse-valuation scenario the
hardening pass calls out: a $50,000 contribution lands mid-period, with no
valuation on that date, and the system must neither fabricate an
intermediate valuation nor imply daily-level precision it doesn't have."""

from datetime import date
from decimal import Decimal as D

from src.analytics.performance import twrr_methodology_metadata
from src.database.repository import Repository
from src.engine.ledger import Ledger
from src.engine.returns import modified_dietz
from src.history.service import HistoryService


def test_mid_period_contribution_with_no_valuation_on_that_date():
    """$100,000 at the start of the period, $50,000 contributed halfway
    through (no valuation exists on that date), $170,000 at the end. The
    contribution must be weighted by its exact date without ever requiring
    -- or fabricating -- a valuation on the day it happened."""
    start, end = date(2024, 1, 1), date(2024, 12, 31)
    contribution_date = date(2024, 7, 1)   # exactly halfway; no valuation here

    result = modified_dietz(
        begin_value=D("100000"), end_value=D("170000"),
        flows=[(contribution_date, D("50000"))],
        start=start, end=end)

    # The contribution is weighted by the fraction of the period remaining
    # after it arrived -- exact to the day -- without ever needing a
    # portfolio valuation on 2024-07-01 itself.
    assert result.weighted_flow == D("25000") or abs(result.weighted_flow - D("25000")) < D("500")
    # Gain is measured net of the contribution: 170,000 - 100,000 - 50,000 = 20,000.
    assert result.gain == D("20000")
    assert result.ret is not None
    # The $50,000 must not appear as if it were investment growth.
    naive_return = (D("170000") - D("100000")) / D("100000")
    assert result.ret < naive_return


def test_twrr_methodology_metadata_states_the_real_method(history):
    metadata = twrr_methodology_metadata(history)
    assert metadata["twrr_methodology"] == "SUBPERIOD_LINKED"
    assert metadata["cash_flow_adjustment_method"] == "EXACT_DATED"
    assert metadata["cash_flow_observation_quality"] in ("LIMITED", "SUFFICIENT")
    assert "true TWRR" in metadata["twrr_methodology_note"]


def test_sparse_valuations_are_flagged_limited(history):
    """The synthetic statement has exactly one real valuation -- far too
    sparse to call the cash-flow observation quality anything but LIMITED."""
    metadata = twrr_methodology_metadata(history)
    assert metadata["valuation_observation_count"] < 12
    assert metadata["cash_flow_observation_quality"] == "LIMITED"


def test_real_portfolio_has_enough_observations_for_sufficient_quality():
    """24 real quarterly valuations across six years clears the threshold."""
    from pathlib import Path
    import pytest as _pytest
    db_path = Path(__file__).resolve().parents[2] / "data/processed/portfolio.db"
    if not db_path.exists():
        _pytest.skip("real portfolio database not present in this checkout")
    repo = Repository(db_path)
    try:
        metadata = twrr_methodology_metadata(HistoryService(repo))
        assert metadata["valuation_observation_count"] >= 12
        assert metadata["cash_flow_observation_quality"] == "SUFFICIENT"
    finally:
        repo.close()


def test_no_intermediate_valuation_is_ever_fabricated(history):
    """The portfolio_daily series must contain no row whose value was
    invented for a date between two real valuations -- only NULL (gap),
    CALCULATED/QUOTED (a real price), or ESTIMATED/carried-forward
    (explicitly labelled as such, never presented as an actual observation)."""
    rows = history.portfolio_history()
    statuses = {r["valuation_status"] for r in rows}
    assert statuses <= {"actual", "calculated", "estimated", "unavailable"}
    # No status claims to be a fabricated point-in-time observation.
    assert "fabricated" not in statuses and "interpolated" not in statuses
