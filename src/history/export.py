"""Export the canonical historical dataset as CSV or JSON.

Exports carry financial data only. Every column is drawn from the historical
tables, which contain no investor name, account number or address, and the
export is scanned before it is written.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.database.repository import Repository
from src.history.config import Granularity
from src.history.service import HistoryService
from src.validation.privacy import LONG_DIGITS

# Columns that would carry identity if a future change let them.
FORBIDDEN_SUBSTRINGS = ("investor", "account_number", "address", "tfn")


def _datasets(service: HistoryService, repo: Repository) -> dict[str, list[dict]]:
    return {
        "portfolio_history": service.portfolio_history(),
        "holdings_history": service.holdings_history(),
        "transactions": [dict(r) for r in repo.rows(
            "SELECT t.transaction_id, t.trade_date, t.settlement_date, t.type,"
            " s.code, t.units, t.price, t.gross_amount, t.fees, t.net_amount,"
            " t.currency, t.description FROM transactions t"
            " LEFT JOIN securities s USING (security_id)"
            " ORDER BY t.trade_date, t.transaction_id")],
        "income": service.income_history(Granularity.MONTHLY, by_security=True),
        "performance": service.performance_history(),
        "period_summaries": [row for granularity in
                             (Granularity.MONTHLY, Granularity.QUARTERLY,
                              Granularity.YEARLY)
                             for row in service.period_summaries(granularity)],
        "contributions": service.contribution_history(Granularity.MONTHLY),
        "drawdowns": service.drawdown_history(),
        "milestones": service.milestones(),
        "reconciliation": service.reconciliation(),
    }


def _check_clean(name: str, rows: list[dict]) -> None:
    """Refuse to write anything carrying identity."""
    for row in rows:
        for key, value in row.items():
            if any(bad in key.lower() for bad in FORBIDDEN_SUBSTRINGS):
                raise ValueError(f"{name}: column '{key}' looks like personal data")
            if isinstance(value, str) and LONG_DIGITS.search(value) and (
                    "description" in key or "note" in key):
                raise ValueError(
                    f"{name}: '{key}' contains an unredacted identifier")


def _plain(value):
    if isinstance(value, (Decimal, date)):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def export(repo: Repository, out_dir: Path, fmt: str = "csv") -> list[Path]:
    service = HistoryService(repo)
    datasets = _datasets(service, repo)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for name, rows in datasets.items():
        _check_clean(name, rows)
        if fmt == "json":
            path = out_dir / f"{name}.json"
            path.write_text(json.dumps(_plain(rows), indent=2))
        else:
            path = out_dir / f"{name}.csv"
            if not rows:
                path.write_text("")
            else:
                # Nested values (allocation weights) are flattened to JSON so a
                # CSV cell stays a single scalar.
                columns = list(rows[0].keys())
                with path.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=columns)
                    writer.writeheader()
                    for row in rows:
                        writer.writerow({
                            k: json.dumps(_plain(v)) if isinstance(v, (dict, list))
                            else _plain(v) for k, v in row.items()})
        written.append(path)
    return written
