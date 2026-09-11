"""Pending-settlement detection and the fee-adjusted matching it depends on."""

from datetime import date
from decimal import Decimal as D

from src.engine.ledger import Ledger
from src.engine.settlement import (pair_trades_with_settlement,
                                   pending_settlements, settlement_gaps)
from src.models import TxnType as T

from tests.conftest import ev

TRADE, SAME, LATER = date(2024, 5, 10), date(2024, 5, 10), date(2024, 5, 13)


def test_a_trade_pairs_with_its_matching_transfer():
    """BUY net_amount includes the fee; the TRANSFER carries the ex-fee
    principal. Matching must add the fee back or every real pair looks
    unmatched."""
    ledger = Ledger([
        ev(TRADE, T.BUY, code="AAA", units=10, price=100, net=1009, fees=9),
        ev(SAME, T.TRANSFER, net=-1000, eid="tr"),
    ])
    pairings = pair_trades_with_settlement(ledger)
    assert len(pairings) == 1
    assert not pairings[0].is_pending
    assert pairings[0].cash_effective_date == SAME
    assert pairings[0].days_to_cash == 0


def test_a_sell_pairs_with_its_gross_proceeds():
    """SELL net_amount already has the fee deducted from proceeds; the
    TRANSFER carries the gross amount before that deduction."""
    ledger = Ledger([
        ev(TRADE, T.SELL, code="AAA", units=-10, price=100, net=-991, fees=9),
        ev(SAME, T.TRANSFER, net=1000, eid="tr"),
    ])
    pairings = pair_trades_with_settlement(ledger)
    assert not pairings[0].is_pending
    assert pairings[0].cash_effective_date == SAME


def test_a_trade_with_no_matching_transfer_is_pending():
    ledger = Ledger([ev(TRADE, T.BUY, code="AAA", units=10, price=100, net=1000)])
    pairings = pair_trades_with_settlement(ledger)
    assert pairings[0].is_pending
    assert pairings[0].cash_effective_date is None
    assert pending_settlements(ledger) == pairings


def test_a_cash_effect_on_a_later_date_is_a_genuine_settlement_gap():
    """If cash ever did move after the trade date, that must be visible, not
    silently accepted as if nothing had changed."""
    ledger = Ledger([
        ev(TRADE, T.BUY, code="AAA", units=10, price=100, net=1000),
        ev(LATER, T.TRANSFER, net=-1000, eid="tr"),
    ])
    gaps = settlement_gaps(ledger)
    assert len(gaps) == 1
    assert gaps[0].days_to_cash == 3


def test_two_same_day_trades_do_not_cross_match():
    """Two trades of different sizes on the same day must each pair with
    their own transfer, not with whichever happens to come first."""
    ledger = Ledger([
        ev(TRADE, T.BUY, code="AAA", units=10, price=100, net=1000, eid="buyA"),
        ev(TRADE, T.BUY, code="BBB", units=5, price=50, net=250, eid="buyB"),
        ev(TRADE, T.TRANSFER, net=-250, eid="trB"),
        ev(TRADE, T.TRANSFER, net=-1000, eid="trA"),
    ])
    pairings = {p.trade.event_id: p.transfer.event_id
                for p in pair_trades_with_settlement(ledger)}
    assert pairings == {"buyA": "trA", "buyB": "trB"}


def test_this_portfolios_history_has_no_pending_or_gapped_trades():
    """The empirical finding this module exists to check: Vanguard's own cash
    ledger dates every trade's cash effect on trade date, always -- confirmed
    across all 76 trades in this portfolio's real history. Skipped when the
    real database is not present (it is gitignored, like the source PDFs)."""
    import pytest as _pytest
    from pathlib import Path
    from src.database.repository import Repository

    db_path = Path(__file__).resolve().parents[2] / "data/processed/portfolio.db"
    if not db_path.exists():
        _pytest.skip("real portfolio database not present in this checkout")

    repo = Repository(db_path)
    try:
        ledger = Ledger.from_repository(repo)
        assert ledger.of_type(T.BUY, T.SELL), "expected real trades to check against"
        pairings = pair_trades_with_settlement(ledger)
        assert pending_settlements(ledger) == []
        assert settlement_gaps(ledger) == []
        assert all(p.days_to_cash == 0 for p in pairings)
    finally:
        repo.close()
