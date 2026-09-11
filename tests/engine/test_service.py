"""End-to-end: import a statement, then reconcile the engine against it."""

from datetime import date
from decimal import Decimal as D

import pytest

from src.database.repository import Repository
from src.engine.reconciliation import summarise
from src.engine.service import PortfolioService
from src.ingestion.importer import import_directory
from src.models import TxnType


@pytest.fixture
def service(tmp_path, statement_dir):
    repo = Repository(tmp_path / "engine.db")
    import_directory(statement_dir, repo)
    yield PortfolioService(repo)
    repo.close()


def test_opening_cash_is_read_from_the_statement(service):
    """The synthetic ledger opens on $100, not on zero."""
    assert service.opening_cash == D("100.00")


def test_every_reported_figure_reconciles(service):
    checks = service.reconcile()
    failures = [(c.when, c.subject, c.expected, c.calculated)
                for c in checks if c.status == "FAIL"]
    assert failures == [], failures
    assert summarise(checks)["passed"] == len(checks)


def test_calculated_value_matches_the_reported_portfolio_value(service):
    """1,500 of holdings + 390 cash + 20 accrued = the reported 1,910."""
    state = service.state(date(2024, 9, 30))
    assert state.securities_value == D("1500.00")
    assert state.cash == D("390.00")
    assert state.total_value == D("1890.00")     # accrued income sits outside


def test_holdings_reconstruct_from_trades(service):
    holding = service.holdings(date(2024, 9, 30))[0]
    assert holding.code == "TST"
    assert holding.units == D("15.00")           # 10 settled + 5 unsettled


def test_income_is_reported_with_its_limitations(service):
    income = service.income()
    assert income["gross_income"] == D("20.00")
    # Franking credits live in the annual tax reports, which are not parsed.
    assert income["franking_available"] is False
    assert income["franking_credits"] == D("0")


def test_history_labels_how_each_value_was_obtained(service):
    for snapshot in service.history():
        assert snapshot.value_quality.value in (
            "not_held", "quoted", "carried_forward", "unavailable")


def test_transactions_are_exposed_in_ledger_order(service):
    events = service.transactions()
    assert [e.sort_key() for e in events] == sorted(e.sort_key() for e in events)
    assert any(e.type is TxnType.BUY for e in events)
