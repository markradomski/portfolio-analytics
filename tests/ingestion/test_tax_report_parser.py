from datetime import date
from decimal import Decimal as D

import pytest

from src.database.repository import Repository
from src.ingestion.importer import import_directory
from src.ingestion.statement_parser import parse_document
from src.models import DocumentKind, Severity
from src.validation import checks, privacy


def test_tax_report_is_classified_and_dated(tax_pdf):
    parsed = parse_document(tax_pdf)
    assert parsed.document.kind is DocumentKind.TAX_REPORT
    assert parsed.tax_summary is not None
    assert parsed.tax_summary.financial_year == 2025
    assert parsed.tax_summary.period_start == date(2024, 7, 1)
    assert parsed.tax_summary.period_end == date(2025, 6, 30)


def test_reads_the_portfolio_level_totals(tax_pdf):
    summary = parse_document(tax_pdf).tax_summary
    assert summary.gross_income == D("28.57")
    assert summary.dividend_franking_credits == D("8.57")
    assert summary.trust_franking_credits == D("0.00")
    assert summary.total_tax_offsets == D("8.57")
    assert summary.total_fees == D("30.00")
    assert summary.withholding_tax == D("0.00")


def test_reads_dated_dividend_rows_with_ex_dates(tax_pdf):
    """Ex dates exist nowhere else in the document set."""
    dividends = parse_document(tax_pdf).dividend_tax
    assert len(dividends) == 1
    row = dividends[0]
    assert row.code == "TST"
    assert row.ex_date == date(2024, 7, 5)
    assert row.payment_date == date(2024, 7, 18)
    assert row.franked_amount == D("20.00")
    assert row.franking_credit == D("8.57")
    assert row.total_income == D("28.57")


def test_reads_per_security_distribution_totals(tax_pdf):
    """Trust distributions are annual totals; they carry no payment dates."""
    details = parse_document(tax_pdf).security_tax
    assert [d.code for d in details] == ["TST"]
    assert details[0].financial_year == 2025
    assert details[0].franking_credit == D("0.00")


def test_tax_report_produces_no_portfolio_records(tax_pdf):
    """It adds detail to the statements rather than restating them."""
    parsed = parse_document(tax_pdf)
    assert parsed.transactions == []
    assert parsed.holdings == []
    assert parsed.valuations == []


def test_personal_data_is_stripped_from_tax_reports_too(tax_pdf):
    from src.ingestion.pdf_parser import load
    from tests.fixtures import synthetic
    lines, _ = load(tax_pdf)
    text = "\n".join(l.text for l in lines)
    assert synthetic.FAKE_NAME not in text
    assert synthetic.FAKE_ACCOUNT not in text
    assert "Investor name" not in text


class TestEnrichment:
    @pytest.fixture
    def repo(self, tmp_path, tax_dir):
        repo = Repository(tmp_path / "tax.db")
        self.result = import_directory(tax_dir, repo)
        yield repo
        repo.close()

    def test_franking_and_ex_date_attach_to_the_income_event(self, repo):
        """The statement records the cash; the tax report supplies the rest."""
        row = repo.rows(
            "SELECT payment_date, amount, franking_credit, ex_date"
            " FROM income_events WHERE franking_credit IS NOT NULL")[0]
        assert row["payment_date"] == "2024-07-19"     # as per the statement
        assert row["amount"] == "20.00"
        assert row["franking_credit"] == "8.57"
        assert row["ex_date"] == "2024-07-05"

    def test_matching_tolerates_the_one_day_date_disagreement(self, repo):
        """Statement says the 19th, tax report says the 18th; same payment."""
        assert self.result.income_enriched == 1

    def test_tax_report_counted_but_not_treated_as_a_statement(self, repo):
        assert self.result.tax_reports == 1
        assert repo.count("tax_summaries") == 1

    def test_totals_reconcile_against_the_breakdown(self, repo):
        assert checks.check_tax_totals(repo) == []

    def test_a_missed_row_shows_up_as_a_shortfall(self, repo):
        repo.conn.execute("UPDATE income_events SET franking_credit = NULL")
        repo.commit()
        codes = [i.code for i in checks.check_tax_totals(repo)]
        assert "TAX_DIVIDEND_FRANKING_DRIFT" in codes

    def test_no_personal_data_reaches_the_dataset(self, repo):
        assert privacy.scan(repo) == []

    def test_import_stays_idempotent_with_tax_reports(self, repo, tax_dir):
        before = {t: repo.count(t) for t in
                  ("income_events", "tax_summaries", "security_tax_details")}
        import_directory(tax_dir, repo)
        after = {t: repo.count(t) for t in
                 ("income_events", "tax_summaries", "security_tax_details")}
        assert after == before

    def test_unmatched_dividends_are_reported_not_forced(self, tmp_path, tax_dir):
        """A dividend the statements never recorded must not invent an event."""
        from tests.fixtures import synthetic
        from tests.fixtures.pdf_builder import build_pdf
        pages = [list(p) for p in synthetic.TAX_REPORT]
        pages[1].insert(-1, "01-Jan-2025 15-Jan-2025 ZZZ Nothing Ltd "
                            "$0.00 $99.99 $42.85 $142.84")
        build_pdf(tax_dir / "extra_tax.pdf", pages)

        repo = Repository(tmp_path / "unmatched.db")
        result = import_directory(tax_dir, repo)
        assert any(i.code == "TAX_DIVIDEND_UNMATCHED" for i in result.issues)
        repo.close()
