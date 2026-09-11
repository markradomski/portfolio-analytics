"""Import orchestration.

    PDFs -> extraction -> classification -> parsing -> normalisation
         -> validation -> deduplication -> database

Deduplication is structural rather than a separate pass: every record carries a
deterministic ID derived from its natural key, and writes are INSERT OR REPLACE.
Re-importing the same statements, or importing an annual statement that repeats
a quarter's transactions, converges on the same rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.database.repository import Repository
from src.ids import make_id
from src.ingestion.statement_parser import ACCOUNT_ID, parse_document
from src.models import Account, Issue, Severity
from src.validation import checks


@dataclass
class ImportResult:
    files_seen: int
    documents_parsed: int
    duplicates: int
    issues: list[Issue]
    tax_reports: int = 0
    income_enriched: int = 0


def _record_ids(parsed) -> list[str]:
    return ([t.transaction_id for t in parsed.transactions]
            + [h.holding_id for h in parsed.holdings]
            + [i.income_id for i in parsed.income]
            + [v.valuation_id for v in parsed.valuations])


def import_directory(source: Path, repo: Repository) -> ImportResult:
    pdfs = sorted(source.glob("*.pdf"))
    run_id = make_id("RUN", datetime.now().isoformat(), str(source))
    repo.start_run(run_id, str(source))
    repo.upsert_account(Account(account_id=ACCOUNT_ID, label="primary"))

    issues: list[Issue] = []
    parsed_count = 0
    tax_reports = 0
    seen_ids: set[str] = set()
    duplicates = 0
    dividend_tax = []

    for path in pdfs:
        try:
            parsed = parse_document(path)
        except Exception as exc:                      # noqa: BLE001 - reported, not raised
            issues.append(Issue(
                Severity.ERROR, "PARSE_FAILED",
                f"{path.name}: {type(exc).__name__}: {exc}", filename=path.name))
            continue

        for issue in parsed.issues:
            issue.filename = issue.filename or path.name
        issues.extend(parsed.issues)

        ids = _record_ids(parsed)
        duplicates += sum(1 for i in ids if i in seen_ids)
        seen_ids.update(ids)

        repo.write_parsed(parsed)
        repo.record_sources(parsed)
        if parsed.tax_summary is not None:
            tax_reports += 1
            dividend_tax.extend(parsed.dividend_tax)
        if parsed.transactions or parsed.holdings or parsed.valuations:
            parsed_count += 1

    # Franking credits and ex dates only exist in the tax reports, and are
    # attached once every statement has been read.
    enriched, unmatched = repo.enrich_income_from_tax(dividend_tax)
    for detail, reason in unmatched:
        issues.append(Issue(
            Severity.WARNING, "TAX_DIVIDEND_UNMATCHED",
            f"{detail.code} dividend paid {detail.payment_date} ({reason}):"
            " franking credit not attached to an income event"))

    # Attribution must not depend on the order files were imported in.
    repo.resolve_canonical_sources()
    repo.commit()
    issues.extend(checks.run_all(repo))
    repo.finish_run(run_id, len(pdfs), issues)

    return ImportResult(files_seen=len(pdfs), documents_parsed=parsed_count,
                        duplicates=duplicates, issues=issues,
                        tax_reports=tax_reports, income_enriched=enriched)
