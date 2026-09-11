"""Automated scan of the stored dataset for personal data.

Structural rather than value-based: it cannot be given the real name or account
number to look for, so it looks for the shapes those take -- labelled identity
fields, and long digit runs in free-text columns where only descriptions belong.

Numeric columns are deliberately not scanned. Money is stored as exact decimal
strings, and a six-figure balance is not an account number.
"""

from __future__ import annotations

import re

from src.database.repository import Repository
from src.models import Issue, Severity

FORBIDDEN_LABELS = (
    "investor name", "tax file number", "account number", "bsb:",
)

# Account and member numbers; six digits is the shortest that occurs.
LONG_DIGITS = re.compile(r"\b\d{6,}\b")

# Only columns that hold prose. Everything else is a number, a date or an ID.
FREE_TEXT_COLUMNS = (
    ("transactions", "description", "transaction_id"),
    ("securities", "name", "security_id"),
    ("documents", "filename", "document_id"),
    ("issues", "message", "issue_id"),
)


def scan(repo: Repository) -> list[Issue]:
    issues: list[Issue] = []

    for table, column, key in FREE_TEXT_COLUMNS:
        for row in repo.rows(f"SELECT {key} AS k, {column} AS v FROM {table}"):
            value = row["v"] or ""
            lowered = value.lower()

            for label in FORBIDDEN_LABELS:
                if label in lowered:
                    issues.append(Issue(
                        Severity.ERROR, "PII_LABEL_PRESENT",
                        f"{table}.{column} ({row['k']}) contains '{label}'"))

            for digits in LONG_DIGITS.findall(value):
                issues.append(Issue(
                    Severity.ERROR, "PII_DIGITS_PRESENT",
                    f"{table}.{column} ({row['k']}) contains an unredacted"
                    f" {len(digits)}-digit identifier"))

    return issues
