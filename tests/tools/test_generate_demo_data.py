"""The synthetic public-demo dataset builds cleanly through the real
pipeline and produces a sane, reconciled, non-negative-cash portfolio.
Nothing here is real financial data -- see tools/generate_demo_data.py.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.database.repository import Repository
from src.engine.reporting import summary
from src.engine.service import PortfolioService
from tools.generate_demo_data import MONTHS, SECURITIES, build_database


@pytest.fixture(scope="module")
def demo_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("demo") / "portfolio.demo.db"
    build_database(path)
    return path


def test_builds_without_error_and_is_deterministic(tmp_path):
    a = tmp_path / "a.db"
    b = tmp_path / "b.db"
    build_database(a)
    build_database(b)
    ra, rb = Repository(a), Repository(b)
    try:
        counts_a = {t: ra.count(t) for t in ("transactions", "securities", "holdings", "portfolio_valuations")}
        counts_b = {t: rb.count(t) for t in ("transactions", "securities", "holdings", "portfolio_valuations")}
        assert counts_a == counts_b
        assert counts_a["transactions"] > 0
    finally:
        ra.close(); rb.close()


def test_all_synthetic_securities_present(demo_db):
    repo = Repository(demo_db)
    try:
        codes = {r["code"] for r in repo.rows("SELECT code FROM securities")}
        assert codes == {code for code, _name, _kind in SECURITIES}
    finally:
        repo.close()


def test_cash_never_goes_negative(demo_db):
    repo = Repository(demo_db)
    try:
        from src.engine.cash import CashEngine
        from src.engine.ledger import Ledger
        ledger = Ledger.from_repository(repo)
        cash = CashEngine()
        for month in MONTHS:
            when = date(month.year, month.month, 28)
            assert cash.balance_at(ledger, when) >= Decimal("0"), when
    finally:
        repo.close()


def test_reconciles_against_its_own_reported_snapshots(demo_db):
    """The demo's quarterly Holding/PortfolioValuation rows are computed
    from the same ledger the engine replays, so they must reconcile
    exactly -- this exercises the real reconciliation checks, just with
    nothing to disagree about."""
    repo = Repository(demo_db)
    try:
        service = PortfolioService(repo)
        checks = service.reconcile()
        assert checks, "expected at least one reconciliation check"
        assert all(c.passed for c in checks), \
            [(c.subject, c.when, c.difference) for c in checks if not c.passed]
    finally:
        repo.close()


def test_portfolio_summary_renders_without_error(demo_db):
    repo = Repository(demo_db)
    try:
        service = PortfolioService(repo)
        text = summary(service)
        assert "Closing value" in text
        assert "TWRR" in text
    finally:
        repo.close()
