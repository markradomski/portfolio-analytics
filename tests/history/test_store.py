"""Rebuild behaviour: deterministic, and incremental must equal full."""

import hashlib
from datetime import date

import pytest

from src.history.store import DAILY_TABLES, DERIVED_TABLES

TABLES = (*DAILY_TABLES, *DERIVED_TABLES)


def fingerprint(repo, table):
    rows = repo.rows(f"SELECT * FROM {table} ORDER BY 1, 2")
    return hashlib.sha256("|".join(str(tuple(r)) for r in rows).encode()).hexdigest()


def snapshot(repo):
    return {table: fingerprint(repo, table) for table in TABLES}


def test_rebuild_is_deterministic(built):
    repo, store = built
    first = snapshot(repo)
    store.rebuild()
    assert snapshot(repo) == first


def test_import_rebuild_rebuild_is_identical(built, tax_dir):
    """The sequence the spec calls out: import, rebuild, rebuild."""
    repo, store = built
    from src.ingestion.importer import import_directory
    first = snapshot(repo)
    import_directory(tax_dir, repo)
    store.rebuild()
    store.rebuild()
    assert snapshot(repo) == first


@pytest.mark.parametrize("boundary", [date(2024, 8, 1), date(2024, 9, 1)])
def test_incremental_rebuild_matches_full(built, boundary):
    """A partial rebuild must reproduce exactly what a full one would."""
    repo, store = built
    full = snapshot(repo)
    store.rebuild(boundary)
    assert snapshot(repo) == full


def test_history_knows_when_it_is_stale(built):
    repo, store = built
    assert store.is_stale() is False
    repo.conn.execute("DELETE FROM transactions WHERE type = 'FEE'")
    repo.commit()
    assert store.is_stale() is True


def test_rebuild_records_the_ledger_it_was_built_from(built):
    repo, _ = built
    runs = repo.rows("SELECT ledger_fingerprint, days FROM history_runs")
    assert runs and runs[0]["days"] > 0
    assert len(runs[0]["ledger_fingerprint"]) == 16
