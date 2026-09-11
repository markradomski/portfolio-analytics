"""Deterministic Vanguard-name -> canonical-security resolution (Step 9B, Stage 3).

The cash CSV identifies distributions by the security's long name only
(`Product ID` is blank on every `Distribution` row). This resolver maps a long
name to a canonical `(security_id, SecurityType)` using, in order:

1. an exact `Product ID` when the row carries one (trades, some distributions);
2. a long-name -> code table seeded from the investment CSV's own
   `Investment` <-> `Product ID` pairs (authoritative: same export, same account);
3. the existing canonical securities table (code + type), when a repo is given.

No fuzzy matching. An unresolved name yields `None` -- never a guess, never a
duplicate security.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.vanguard_csv.records import InvestmentSourceRecord
from src.models import SecurityType
from src.normalisation.securities import normalise_code, security_type_for


@dataclass(frozen=True)
class ResolvedSecurity:
    security_id: str          # the canonical code (VAS, BHP, ...) -- ids are the code in this dataset
    code: str
    security_type: SecurityType
    method: str               # PRODUCT_ID | NAME_FROM_INVESTMENT_CSV | REPO_SECURITIES


class SecurityResolver:
    def __init__(self) -> None:
        self._by_code: dict[str, ResolvedSecurity] = {}
        self._by_name: dict[str, ResolvedSecurity] = {}

    # -- seeding ---------------------------------------------------------

    def seed_from_investment_records(self, records: list[InvestmentSourceRecord]) -> None:
        for r in records:
            code = normalise_code(r.product_id)
            if not code:
                continue
            stype = security_type_for(
                {"ETF": "etf", "Share": "australian_share"}.get(r.product_type or "", None),
                r.security_name,
            )
            resolved = ResolvedSecurity(code, code, stype, "NAME_FROM_INVESTMENT_CSV")
            self._by_code.setdefault(code, resolved)
            key = _name_key(r.security_name)
            if key:
                self._by_name.setdefault(key, resolved)

    def seed_from_repo_securities(self, rows) -> None:
        """`rows` = iterable of mappings with 'code', 'name', 'type'."""
        for row in rows:
            code = normalise_code(row["code"])
            if not code:
                continue
            try:
                stype = SecurityType(row["type"])
            except ValueError:
                stype = security_type_for(None, row["name"])
            resolved = ResolvedSecurity(code, code, stype, "REPO_SECURITIES")
            self._by_code.setdefault(code, resolved)
            key = _name_key(row["name"])
            if key:
                self._by_name.setdefault(key, resolved)

    # -- resolution ----------------------------------------------------------

    def resolve(self, *, product_id: str | None, name: str | None) -> ResolvedSecurity | None:
        code = normalise_code(product_id)
        if code and code in self._by_code:
            return _with_method(self._by_code[code], "PRODUCT_ID")
        if code:
            # a code we have never seen -- classify by nothing, stay unresolved
            return None
        key = _name_key(name)
        if key and key in self._by_name:
            return self._by_name[key]
        return None


def _name_key(name: str | None) -> str:
    return (name or "").strip().lower()


def _with_method(r: ResolvedSecurity, method: str) -> ResolvedSecurity:
    return ResolvedSecurity(r.security_id, r.code, r.security_type, method)
