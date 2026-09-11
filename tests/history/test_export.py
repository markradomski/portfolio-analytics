import csv
import json

import pytest

from src.history.export import export
from tests.fixtures import synthetic

FORBIDDEN = (synthetic.FAKE_NAME, synthetic.FAKE_ADDRESS_1,
             synthetic.FAKE_ACCOUNT, synthetic.FAKE_BSB,
             synthetic.FAKE_DESTINATION)


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_export_writes_every_dataset(built, tmp_path, fmt):
    repo, _ = built
    written = export(repo, tmp_path / fmt, fmt)
    names = {p.stem for p in written}
    assert {"portfolio_history", "holdings_history", "transactions", "income",
            "performance", "contributions", "drawdowns"} <= names
    assert all(p.exists() for p in written)


def test_exported_data_contains_no_personal_data(built, tmp_path):
    repo, _ = built
    for path in export(repo, tmp_path / "out", "json"):
        content = path.read_text()
        for secret in FORBIDDEN:
            assert secret not in content, f"{secret!r} leaked into {path.name}"


def test_csv_is_readable_and_has_headers(built, tmp_path):
    repo, _ = built
    export(repo, tmp_path / "csv", "csv")
    with (tmp_path / "csv" / "portfolio_history.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert "total_value" in rows[0]
    assert "valuation_status" in rows[0]


def test_json_round_trips(built, tmp_path):
    repo, _ = built
    export(repo, tmp_path / "json", "json")
    data = json.loads((tmp_path / "json" / "performance.json").read_text())
    assert isinstance(data, list)
    assert any(row["label"] == "INCEPTION" for row in data)
