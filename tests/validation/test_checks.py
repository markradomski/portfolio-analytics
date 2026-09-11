from pathlib import Path

import pytest

from src.database.repository import Repository
from src.ingestion.importer import import_directory
from src.models import Severity
from src.validation import checks


@pytest.fixture
def imported(tmp_path, statement_dir):
    repo = Repository(tmp_path / "test.db")
    result = import_directory(statement_dir, repo)
    yield repo, result
    repo.close()


def test_synthetic_statement_passes_every_check(imported):
    repo, result = imported
    errors = [i for i in result.issues if i.severity is Severity.ERROR]
    warnings = [i for i in result.issues if i.severity is Severity.WARNING]
    assert errors == [], [i.message for i in errors]
    assert warnings == [], [i.message for i in warnings]


def test_valuation_check_catches_a_missing_holding(imported):
    """Portfolio value must equal holdings plus cash plus accrued income."""
    repo, _ = imported
    repo.conn.execute("DELETE FROM holdings")
    repo.commit()
    issues = checks.check_valuation_totals(repo)
    assert [i.code for i in issues] == ["VALUATION_MISMATCH"]


def test_period_identity_check_catches_a_wrong_closing_value(imported):
    repo, _ = imported
    repo.conn.execute("UPDATE statement_periods SET closing_value = '9999.99'")
    repo.commit()
    issues = checks.check_period_identity(repo)
    assert [i.code for i in issues] == ["PERIOD_IDENTITY_DRIFT"]


def test_unit_continuity_check_catches_a_dropped_trade(imported):
    """Reported units must equal prior units plus everything traded since."""
    repo, _ = imported
    repo.conn.execute("DELETE FROM transactions WHERE type = 'BUY'")
    repo.commit()
    issues = checks.check_unit_continuity(repo)
    assert [i.code for i in issues] == ["UNIT_CONTINUITY_DRIFT"]


def test_negative_units_are_an_error(imported):
    repo, _ = imported
    repo.conn.execute("UPDATE holdings SET units = '-5'")
    repo.commit()
    assert any(i.code == "HOLDING_NEGATIVE" for i in checks.check_holding_signs(repo))


def test_impossible_dates_are_an_error(imported):
    repo, _ = imported
    repo.conn.execute("UPDATE holdings SET reporting_date = '2999-01-01'")
    repo.commit()
    assert any(i.code == "IMPOSSIBLE_DATE" for i in checks.check_timeline(repo))


def test_missing_quarters_are_reported(imported):
    repo, _ = imported
    repo.conn.execute(
        "INSERT INTO statement_periods(period_id, account_id, kind, period_start,"
        " period_end, source_document_id, extraction_method)"
        " SELECT 'gap', account_id, 'QUARTERLY', '2025-04-01', '2025-06-30',"
        " source_document_id, extraction_method FROM statement_periods LIMIT 1")
    repo.commit()
    codes = [i.code for i in checks.check_timeline(repo)]
    assert "MISSING_QUARTER" in codes
