from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import app as app_module
from src.database.repository import Repository
from src.history.store import HistoryStore
from src.ingestion.importer import import_directory


@pytest.fixture
def built_db_path(tmp_path, tax_dir) -> Path:
    """Builds a standalone database file (not an already-open Repository)
    and rebuilds history on it, so the API app -- which opens its own
    connection per request -- can point at the same file the rest of the
    test suite's fixtures use."""
    db_path = tmp_path / "api.db"
    repo = Repository(db_path)
    import_directory(tax_dir, repo)
    HistoryStore(repo).rebuild()
    repo.close()
    return db_path


@pytest.fixture
def client(monkeypatch, built_db_path):
    """Points the API at the synthetic test database rather than the real
    portfolio, so API tests don't depend on the (gitignored) real data."""
    monkeypatch.setattr(app_module, "DB_PATH", built_db_path)
    return TestClient(app_module.app)
