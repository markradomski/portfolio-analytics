"""Normalise the raw strings on a statement into typed values.

Nothing here guesses. A value that cannot be parsed confidently returns None so
the caller can raise a validation issue, rather than being coerced into a
plausible-looking number.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# 1-Apr-2026 / 01-May-2026
DATE_LONG = r"\d{1,2}-[A-Za-z]{3}-\d{4}"
# 28-Jun-24
DATE_SHORT = r"\d{1,2}-[A-Za-z]{3}-\d{2}"
# -$1,234.56 / 1,234.567 / $0.00
NUMBER = r"-?\$?-?[\d,]+\.\d+"

_DATE_FORMATS = (
    "%d-%b-%Y",      # 01-May-2026
    "%d-%b-%y",      # 28-Jun-24
    "%d %B %Y",      # 30 June 2026
    "%d %b %Y",      # 30 Jun 2026
    "%Y-%m-%d",      # already normalised
)

_UNPARSEABLE_DATES = {"not yet settled", "", "-"}


def parse_decimal(raw: str | None) -> Decimal | None:
    """'$1,234.56' -> Decimal('1234.56'). Returns None if not a number."""
    if raw is None:
        return None
    cleaned = raw.strip().replace("$", "").replace(",", "").replace(" ", "")
    if not cleaned or cleaned in {"-", "."}:
        return None
    # Statements occasionally render a negative as "-$1,234.56"; the sign has
    # already survived the strip above, but a doubled sign has not.
    cleaned = re.sub(r"^--+", "-", cleaned)
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_date(raw: str | None) -> date | None:
    """Accepts every date format seen across the statement range."""
    if raw is None:
        return None
    text = raw.strip()
    if text.lower() in _UNPARSEABLE_DATES:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def quarter_of(d: date) -> tuple[int, int]:
    """(year, quarter) for timeline gap detection."""
    return d.year, (d.month - 1) // 3 + 1
