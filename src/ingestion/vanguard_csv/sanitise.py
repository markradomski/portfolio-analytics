"""Privacy sanitisation for Vanguard structured exports (Step 9B).

Account-identifying data must never survive into a record, a log, a hash, a
snapshot or a test fixture. This module is the single choke point: every string
that a parser carries forward from a CSV cell passes through `redact` first, and
the `Account number` column is dropped before a row is ever constructed.

The rule: any run of 4+ digits is replaced with the same number of `#`, unless
it is part of a `dd-Mon-yyyy` / `dd-Mon-yy` date (those are legitimate source
values the reconciliation layer needs). Two- and three-digit runs are left --
they are quantities, small reference codes and the day/year parts of dates,
never account or BSB numbers (the shortest of those Vanguard uses is 6 digits;
BSBs are 6).
"""

from __future__ import annotations

import re

# A dd-Mon-yyyy or dd-Mon-yy date embedded anywhere in prose. Matched first and
# preserved verbatim; only the digit runs *outside* such a date are redacted.
_DATE = re.compile(r"\b\d{1,2}-[A-Za-z]{3}-\d{2,4}\b")

# 4+ consecutive digits: account numbers, BSBs, member numbers, payment refs.
_DIGIT_RUN = re.compile(r"\d{4,}")

# Column headers that carry account identity outright and are dropped whole.
FORBIDDEN_COLUMNS = frozenset({"account number", "accountnumber", "account no"})

# A Vanguard Deposit description often reads "Off-System BSB Direct Entry
# Deposit - <source>", where <source> is a free-text bank name or the
# investor's own initials (observed in this dataset: a real bank name and
# real initials) -- alphabetic, so the digit-only `redact()` above never
# touches it. Nothing about the identity of the sending bank/person is an
# economic fact the ledger needs, so the whole trailing clause is dropped,
# not just redacted.
_TRAILING_SOURCE_CLAUSE = re.compile(r"\s+-\s+.+$")


def strip_deposit_source(text: str | None) -> str:
    """'Off-System BSB Direct Entry Deposit - demobank' ->
    'Off-System BSB Direct Entry Deposit'. Only ever applied to Deposit rows
    -- Withdrawal rows keep their (already digit-redacted) destination
    clause, since it carries the (redacted) account reference and a date the
    reconciliation-evidence trail benefits from."""
    if not text:
        return text or ""
    return _TRAILING_SOURCE_CLAUSE.sub("", text).strip()


def redact(text: str | None) -> str:
    """Replace every non-date run of 4+ digits in `text` with `#` characters.

    >>> redact("One-off Cash Withdrawal to 29545782 on 05-May-2026")
    'One-off Cash Withdrawal to ######## on 05-May-2026'
    >>> redact("Off-System BSB Direct Entry Deposit - 123456789")
    'Off-System BSB Direct Entry Deposit - #########'
    >>> redact("VAS trade of 14 units")
    'VAS trade of 14 units'
    """
    if not text:
        return text or ""

    # Protect embedded dates by carving the string around them.
    out: list[str] = []
    last = 0
    for m in _DATE.finditer(text):
        out.append(_DIGIT_RUN.sub(lambda d: "#" * len(d.group()), text[last:m.start()]))
        out.append(m.group())
        last = m.end()
    out.append(_DIGIT_RUN.sub(lambda d: "#" * len(d.group()), text[last:]))
    return "".join(out)


def contains_identifier(text: str | None) -> bool:
    """True if `text` still holds an unredacted 4+ digit run outside a date --
    used by the privacy tests as a belt-and-braces check on parser output."""
    if not text:
        return False
    stripped = _DATE.sub("", text)
    return bool(_DIGIT_RUN.search(stripped))


def drop_forbidden_columns(fieldnames: list[str]) -> list[str]:
    """The subset of `fieldnames` that is safe to read. `Account number` and
    friends never reach a record."""
    return [f for f in fieldnames if f.strip().lower() not in FORBIDDEN_COLUMNS]
