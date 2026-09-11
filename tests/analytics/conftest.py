from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from src.database.repository import Repository
from src.engine.ledger import Ledger
from src.engine.prices import SnapshotPriceSource
from src.engine.state import StateEngine
from src.history.store import HistoryStore
from src.history.service import HistoryService
from src.ingestion.importer import import_directory


@pytest.fixture
def built(tmp_path, tax_dir):
    """A fully imported, rebuilt database -- same fixture shape as
    tests/history/conftest.py, reused here so analytics is tested against the
    same known synthetic statement rather than a third dataset."""
    repo = Repository(tmp_path / "analytics.db")
    import_directory(tax_dir, repo)
    HistoryStore(repo).rebuild()
    yield repo
    repo.close()


@pytest.fixture
def history(built):
    return HistoryService(built)


@pytest.fixture
def ledger(built):
    return Ledger.from_repository(built)


@pytest.fixture
def state_engine(built):
    from src.engine.cash import opening_cash_for
    return StateEngine(SnapshotPriceSource.from_repository(built),
                       opening_cash=opening_cash_for(built))
