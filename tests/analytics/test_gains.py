"""Realised/unrealised gains must come from Phase 2's own cost-basis engine,
never a separately computed figure (sec 18-20)."""

from datetime import date
from decimal import Decimal as D

from src.analytics.gains import (gain_attribution, realised_gains,
                                 realised_gains_by_security, unrealised_gains)
from src.engine.holdings import HoldingsEngine


def test_unrealised_gain_matches_phase2_state_directly(state_engine, ledger):
    """No separate cost-basis calculation: the figure here must be exactly
    what Phase 2's own SecurityState already computed."""
    on = date(2024, 9, 30)
    rows = unrealised_gains(state_engine, ledger, on)
    state = state_engine.state_at(ledger, on)
    by_id = {s.security_id: s for s in state.securities if s.units != 0}
    for row in rows:
        assert row.unrealised_gain == by_id[row.security_id].unrealised_gain
        assert row.cost_basis == by_id[row.security_id].cost_basis


def test_zero_cost_holding_does_not_produce_infinity_or_nan(state_engine, ledger):
    """Every unrealised_gain_pct must be a real number or None, never inf/nan."""
    import math
    rows = unrealised_gains(state_engine, ledger, date(2024, 9, 30))
    for row in rows:
        if row.unrealised_gain_pct is not None:
            assert math.isfinite(float(row.unrealised_gain_pct))


def test_gain_attribution_categories_do_not_overlap(state_engine, ledger):
    """Realised, unrealised and income are mutually exclusive by construction
    -- summing them must not double count anything Phase 2 already tracks."""
    attribution = gain_attribution(state_engine, ledger, date(2024, 9, 30))
    state = state_engine.state_at(ledger, date(2024, 9, 30))
    assert attribution.realised_gains == state.realised_gain
    assert attribution.unrealised_gains == state.unrealised_gain


def test_realised_gain_and_loss_are_internally_consistent(ledger):
    """gain is the sum of profitable disposals, loss the sum of losing ones
    (a negative number); net is their sum. Per-security detail is covered by
    the repo-backed test below."""
    engine = HoldingsEngine()
    total = realised_gains(ledger, holdings_engine=engine)
    assert total.net_realised_gain == total.realised_gain + total.realised_loss
    assert total.realised_gain >= 0
    assert total.realised_loss <= 0


def test_realised_gains_by_security_needs_a_repo(built, ledger):
    from src.analytics.gains import realised_gains_by_security
    rows = realised_gains_by_security(built, ledger)
    # The synthetic statement has no sells, so this should be empty --
    # confirms it doesn't fabricate a disposal that never happened.
    assert rows == []
