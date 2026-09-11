"""Import-level behaviour: idempotency, deduplication, and privacy."""

from pathlib import Path

import pytest

from src.database.repository import Repository
from src.ingestion.importer import import_directory
from src.models import Severity
from tests.fixtures import synthetic
from tests.fixtures.pdf_builder import build_pdf

TABLES = ("documents", "securities", "transactions", "holdings",
          "income_events", "portfolio_valuations", "statement_periods")

FORBIDDEN = (synthetic.FAKE_NAME, synthetic.FAKE_ADDRESS_1,
             synthetic.FAKE_ADDRESS_2, synthetic.FAKE_ACCOUNT,
             synthetic.FAKE_BSB, synthetic.FAKE_DESTINATION)


def _counts(repo):
    return {t: repo.count(t) for t in TABLES}


def _dump(repo) -> str:
    """Every stored value as one string, for scanning."""
    parts = []
    for table in TABLES + ("accounts", "issues", "import_runs"):
        for row in repo.rows(f"SELECT * FROM {table}"):
            parts.extend(str(v) for v in tuple(row) if v is not None)
    return "\n".join(parts)


def test_import_is_idempotent(tmp_path, statement_dir):
    """Re-running the importer must not duplicate anything."""
    repo = Repository(tmp_path / "a.db")
    import_directory(statement_dir, repo)
    first = _counts(repo)
    import_directory(statement_dir, repo)
    assert _counts(repo) == first
    repo.close()


def test_duplicate_file_under_a_different_name_is_collapsed(tmp_path, statement_dir):
    """The same statement saved twice describes one set of events."""
    repo = Repository(tmp_path / "b.db")
    import_directory(statement_dir, repo)
    baseline = _counts(repo)

    build_pdf(statement_dir / "copy_of_statement.pdf", synthetic.QUARTERLY_STATEMENT)
    import_directory(statement_dir, repo)

    after = _counts(repo)
    assert after["transactions"] == baseline["transactions"]
    assert after["holdings"] == baseline["holdings"]
    assert after["income_events"] == baseline["income_events"]
    # Two files, one content hash: still a single document row.
    assert after["documents"] == baseline["documents"]
    repo.close()


def test_two_identical_rows_in_one_document_stay_distinct(tmp_path):
    """Genuinely repeated events are not deduplication targets."""
    pages = [list(page) for page in synthetic.QUARTERLY_STATEMENT]
    fee_row = "02-Jul-2024 Account Fee 10.00 90.00"
    index = pages[2].index(fee_row)
    pages[2].insert(index + 1, "03-Jul-2024 Account Fee 10.00 80.00")

    source = tmp_path / "src"
    source.mkdir()
    build_pdf(source / "s.pdf", pages)
    repo = Repository(tmp_path / "c.db")
    import_directory(source, repo)
    fees = repo.rows("SELECT * FROM transactions WHERE type='FEE'")
    assert len(fees) == 3
    repo.close()


def test_no_personal_data_reaches_the_database(tmp_path, statement_dir):
    """The dataset must contain no investor name, address or account number."""
    repo = Repository(tmp_path / "d.db")
    import_directory(statement_dir, repo)
    dump = _dump(repo)
    for secret in FORBIDDEN:
        assert secret not in dump, f"{secret!r} leaked into the dataset"
    for label in ("Investor name", "Tax file number", "BSB:"):
        assert label not in dump
    repo.close()


def test_withdrawal_description_keeps_its_meaning_after_redaction(tmp_path, statement_dir):
    repo = Repository(tmp_path / "e.db")
    import_directory(statement_dir, repo)
    row = repo.rows("SELECT description FROM transactions WHERE type='WITHDRAWAL'")[0]
    assert "[redacted]" in row["description"]
    assert "Cash Withdrawal" in row["description"]
    repo.close()


def test_unreadable_file_is_reported_not_fatal(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "not-really.pdf").write_bytes(b"this is not a PDF")
    repo = Repository(tmp_path / "f.db")
    result = import_directory(source, repo)
    assert any(i.code == "PARSE_FAILED" and i.severity is Severity.ERROR
               for i in result.issues)
    repo.close()


def test_every_record_is_traceable_to_a_source_document(tmp_path, statement_dir):
    repo = Repository(tmp_path / "g.db")
    import_directory(statement_dir, repo)
    for table in ("transactions", "holdings", "income_events",
                  "portfolio_valuations", "statement_periods"):
        orphans = repo.rows(
            f"SELECT COUNT(*) AS n FROM {table} t LEFT JOIN documents d"
            " ON d.document_id = t.source_document_id WHERE d.document_id IS NULL")
        assert orphans[0]["n"] == 0, f"{table} has records with no source document"
    repo.close()
