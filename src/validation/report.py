"""Data quality report."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from src.database.repository import Repository
from src.models import Issue, Severity

_LINE = "-" * 68


def _counts(repo: Repository) -> dict[str, int]:
    return {t: repo.count(t) for t in (
        "documents", "securities", "transactions", "holdings",
        "income_events", "portfolio_valuations", "statement_periods",
        "tax_summaries", "security_tax_details")}


def build(repo: Repository, issues: list[Issue], *, files_seen: int,
          documents_parsed: int, duplicates: int, source: str) -> str:
    counts = _counts(repo)
    franked = repo.rows(
        "SELECT COUNT(*) AS n FROM income_events"
        " WHERE franking_credit IS NOT NULL")[0]["n"]
    by_severity = Counter(i.severity for i in issues)
    review = {i.document_id for i in issues
              if i.severity in (Severity.ERROR, Severity.WARNING) and i.document_id}

    out = [
        "Vanguard portfolio — data quality report",
        f"Generated {datetime.now():%Y-%m-%d %H:%M}    source: {source}",
        _LINE,
        f"Files seen:                 {files_seen}",
        f"Documents parsed:           {documents_parsed}",
        f"Documents requiring review: {len(review)}",
        "",
        f"Securities:                 {counts['securities']}",
        f"Transactions extracted:     {counts['transactions']}",
        f"Holdings extracted:         {counts['holdings']}",
        f"Income events:              {counts['income_events']}",
        f"Valuations:                 {counts['portfolio_valuations']}",
        f"Statement periods:          {counts['statement_periods']}",
        f"Tax years:                  {counts['tax_summaries']}",
        f"Security tax details:       {counts['security_tax_details']}",
        f"Income events with franking: {franked}",
        "",
        f"Duplicate records collapsed: {duplicates}",
        f"Validation errors:           {by_severity[Severity.ERROR]}",
        f"Validation warnings:         {by_severity[Severity.WARNING]}",
        f"Notes:                       {by_severity[Severity.INFO]}",
        _LINE,
    ]

    if not issues:
        out.append("No issues raised.")
        return "\n".join(out)

    filenames = {r["document_id"]: r["filename"]
                 for r in repo.rows("SELECT document_id, filename FROM documents")}

    for severity in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        group = [i for i in issues if i.severity is severity]
        if not group:
            continue
        out.append(f"\n{severity.value} ({len(group)})")
        for issue in group:
            where = issue.filename or filenames.get(issue.document_id or "", "")
            page = f" p{issue.page}" if issue.page else ""
            location = f"  [{where}{page}]" if where or page else ""
            out.append(f"  {issue.code}: {issue.message}{location}")

    return "\n".join(out)
