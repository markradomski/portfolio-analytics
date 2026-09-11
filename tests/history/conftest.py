from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from src.database.repository import Repository
from src.history.config import ValuationStatus
from src.history.generator import DailyRow
from src.history.store import HistoryStore
from src.ingestion.importer import import_directory


def row(when, value=None, *, index=None, index_as_at=None, cash="0",
        contributions="0", withdrawals="0", income="0", fees="0", realised="0",
        status=ValuationStatus.CALCULATED, price_as_at=None):
    """A daily row for testing the analytics that sit on top of the series."""
    total = None if value is None else D(str(value))
    return DailyRow(
        date=when, total_value=total, securities_value=total, cash=D(cash),
        cost_basis=D("0"), invested_capital=D(contributions) + D(withdrawals),
        realised_gain=D(realised), unrealised_gain=D("0"), dividends=D("0"),
        distributions=D("0"), income=D(income), fees=D(fees),
        cumulative_contributions=D(contributions),
        cumulative_withdrawals=D(withdrawals),
        high_water_mark=total or D("0"), drawdown_value=D("0"), drawdown_pct=None,
        return_index=None if index is None else D(str(index)),
        index_as_at=index_as_at or (when if index is not None else None),
        return_high_water=None, return_drawdown_pct=None,
        valuation_status=status,
        valuation_source="VANGUARD" if status is ValuationStatus.ACTUAL
        else "VANGUARD_SECURITY_PRICE",
        price_as_at=price_as_at or (when if total is not None else None),
        source_count=0, holdings=[])


def series(values, start=date(2024, 1, 1)):
    """Daily rows from a list of index levels, one per day."""
    return [row(start + timedelta(days=n), value=level, index=level)
            for n, level in enumerate(values)]


@pytest.fixture
def built(tmp_path, tax_dir):
    """A fully imported and rebuilt database."""
    repo = Repository(tmp_path / "history.db")
    import_directory(tax_dir, repo)
    store = HistoryStore(repo)
    store.rebuild()
    yield repo, store
    repo.close()
