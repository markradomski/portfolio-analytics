"""Command line entry point.

    python -m src.cli import statements/
    python -m src.cli import statements/ --db data/processed/portfolio.db
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from src.database.repository import Repository
from src.ingestion.importer import import_directory
from src.models import Severity
from src.validation import report

DEFAULT_DB = Path("data/processed/portfolio.db")
DEFAULT_REPORT = Path("data/processed/quality-report.txt")


def _rebuild_history(args) -> int:
    from src.history.store import HistoryStore

    repo = Repository(args.db)
    try:
        result = HistoryStore(repo).rebuild(args.from_date)
    finally:
        repo.close()
    scope = f"from {args.from_date}" if args.from_date else "complete"
    print(f"Rebuilt history ({scope}): {result.days} days, {result.holdings}"
          f" holding rows, {result.income} income rows, {result.summaries}"
          f" period summaries, {result.episodes} drawdowns,"
          f" {result.milestones} milestones")
    print(f"ledger fingerprint: {result.fingerprint}")
    return 0


def _history(args) -> int:
    from src.history import reporting as history_reporting

    repo = Repository(args.db)
    try:
        text = history_reporting.summary(repo)
    finally:
        repo.close()
    print(text)
    return 0


def _export_history(args) -> int:
    from src.history.export import export

    repo = Repository(args.db)
    try:
        written = export(repo, args.out, args.format)
    finally:
        repo.close()
    print(f"Exported {len(written)} {args.format.upper()} files to {args.out}")
    for path in written:
        print(f"  {path.name}")
    return 0


def _analytics(args) -> int:
    from src.analytics.service import AnalyticsService
    from src.analytics import reporting as analytics_reporting

    repo = Repository(args.db)
    try:
        service = AnalyticsService(repo)
        text = analytics_reporting.summary(service, args.year)
    finally:
        repo.close()
    print(text)
    return 0


def _analyse(args) -> int:
    from src.engine import reporting
    from src.engine.service import PortfolioService

    repo = Repository(args.db)
    try:
        service = PortfolioService(repo)
        text = reporting.summary(service)
        checks = service.reconcile()
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "portfolio-summary.txt").write_text(text + "\n")
        (args.out / "reconciliation.txt").write_text(
            reporting.reconciliation_report(checks) + "\n")
        (args.out / "history.json").write_text(reporting.to_json(service.history()))
        (args.out / "performance.json").write_text(
            reporting.to_json(service.performance()))
        (args.out / "attribution.json").write_text(
            reporting.to_json(service.attribution().ranked()))
    finally:
        repo.close()

    print(text)
    print(f"\nwrote {args.out}/portfolio-summary.txt, reconciliation.txt,"
          f" history.json, performance.json, attribution.json")
    return 1 if any(c.status == "FAIL" for c in checks) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portfolio-tool")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="import statement PDFs into the database")
    imp.add_argument("source", type=Path, help="directory containing statement PDFs")
    imp.add_argument("--db", type=Path, default=DEFAULT_DB)
    imp.add_argument("--report", type=Path, default=DEFAULT_REPORT)

    ana = sub.add_parser("analyse", help="run the accounting engine over the database")
    ana.add_argument("--db", type=Path, default=DEFAULT_DB)
    ana.add_argument("--out", type=Path, default=Path("data/processed"))

    reb = sub.add_parser("rebuild-history",
                         help="rebuild the historical time series")
    reb.add_argument("--db", type=Path, default=DEFAULT_DB)
    reb.add_argument("--from", dest="from_date", type=date.fromisoformat,
                     default=None, help="rebuild only from this date onward")

    his = sub.add_parser("history", help="summarise the historical dataset")
    his.add_argument("--db", type=Path, default=DEFAULT_DB)

    exp = sub.add_parser("export-history", help="export the historical dataset")
    exp.add_argument("--db", type=Path, default=DEFAULT_DB)
    exp.add_argument("--format", choices=("csv", "json"), default="csv")
    exp.add_argument("--out", type=Path, default=Path("data/processed/export"))

    ana2 = sub.add_parser("analytics", help="run the Phase 4 analytics layer")
    ana2.add_argument("--db", type=Path, default=DEFAULT_DB)
    ana2.add_argument("--year", type=int, default=None,
                      help="calendar year to summarise (defaults to the most recent)")

    args = parser.parse_args(argv)
    if args.command == "rebuild-history":
        return _rebuild_history(args)
    if args.command == "history":
        return _history(args)
    if args.command == "export-history":
        return _export_history(args)
    if args.command == "analytics":
        return _analytics(args)
    if args.command == "analyse":
        return _analyse(args)
    if not args.source.is_dir():
        print(f"not a directory: {args.source}", file=sys.stderr)
        return 2

    repo = Repository(args.db)
    try:
        result = import_directory(args.source, repo)
        text = report.build(
            repo, result.issues, files_seen=result.files_seen,
            documents_parsed=result.documents_parsed,
            duplicates=result.duplicates, source=str(args.source))
    finally:
        repo.close()

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text + "\n")
    print(text)
    print(f"\ndatabase: {args.db}\nreport:   {args.report}")

    errors = sum(1 for i in result.issues if i.severity is Severity.ERROR)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
