import pytest

from src.database.repository import Repository
from src.ingestion.importer import import_directory
from src.validation import privacy


@pytest.fixture
def repo(tmp_path, statement_dir):
    repo = Repository(tmp_path / "p.db")
    import_directory(statement_dir, repo)
    yield repo
    repo.close()


def test_clean_dataset_scans_clean(repo):
    assert privacy.scan(repo) == []


def test_detects_an_unredacted_account_number(repo):
    repo.conn.execute(
        "UPDATE transactions SET description = 'Withdrawal to 13257353'"
        " WHERE type = 'WITHDRAWAL'")
    repo.commit()
    codes = [i.code for i in privacy.scan(repo)]
    assert "PII_DIGITS_PRESENT" in codes


def test_detects_a_leaked_identity_label(repo):
    repo.conn.execute("UPDATE securities SET name = 'Investor name: A N Other'")
    repo.commit()
    codes = [i.code for i in privacy.scan(repo)]
    assert "PII_LABEL_PRESENT" in codes


def test_money_is_not_mistaken_for_an_identifier(repo):
    """A six-figure balance is not an account number."""
    repo.conn.execute("UPDATE transactions SET net_amount = '107110.02'")
    repo.commit()
    assert privacy.scan(repo) == []
