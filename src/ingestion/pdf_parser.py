"""PDF text extraction, with personal data removed at the boundary.

Extraction is deliberately thin: it produces page-attributed lines and nothing
else, so every downstream record can name the page it came from. Personal data
is stripped here, before any parsing runs, so that no later layer can capture
it even by accident.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

EXTRACTION_METHOD = "pdfplumber-text"

# Fields that appear on every statement and are never needed to reconstruct a
# portfolio: investor name, postal address, account number, TFN status, and the
# cash account's BSB and number.
PII_LINE = re.compile(
    r"^\s*(Investor name|Account number|Tax file number status|BSB)\s*:", re.I
)

# Withdrawal descriptions embed the destination account number, and statements
# occasionally carry other long identifiers inline.
LONG_DIGITS = re.compile(r"\b\d{6,}\b")

_TITLE_MARKER = "Vanguard Personal Investor"


@dataclass(frozen=True)
class PageLine:
    page: int          # 1-indexed, matches the printed page number
    text: str


def strip_pii(pages: list[str]) -> list[str]:
    """Remove personal data from extracted page text.

    Two rules: drop the posting address block that opens page 1 (everything
    above the document title), and drop any labelled identity line anywhere.
    """
    out: list[str] = []
    for index, text in enumerate(pages):
        lines = text.splitlines()
        if index == 0:
            title_at = next(
                (n for n, line in enumerate(lines) if _TITLE_MARKER in line), 0
            )
            lines = lines[title_at:]
        out.append("\n".join(l for l in lines if not PII_LINE.match(l)))
    return out


def redact_inline(text: str) -> str:
    """Redact identifiers embedded in free-text descriptions."""
    return LONG_DIGITS.sub("[redacted]", text)


def extract_pages(path: Path) -> list[str]:
    with pdfplumber.open(path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def load(path: Path) -> tuple[list[PageLine], int]:
    """Return PII-stripped, page-attributed lines and the page count."""
    pages = strip_pii(extract_pages(path))
    lines = [
        PageLine(page=n, text=raw.strip())
        for n, text in enumerate(pages, start=1)
        for raw in text.splitlines()
        if raw.strip()
    ]
    return lines, len(pages)
