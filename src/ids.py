"""Deterministic record identifiers.

IDs are derived from a record's natural key rather than from a sequence, so
re-importing the same document produces the same IDs and the import stays
idempotent. Nothing identifying is used as an input.
"""

from __future__ import annotations

import hashlib

ID_LENGTH = 16


def make_id(kind: str, *parts: object) -> str:
    """Stable ID for a record, derived from its natural key."""
    payload = "|".join([kind, *(("" if p is None else str(p)) for p in parts)])
    return hashlib.sha256(payload.encode()).hexdigest()[:ID_LENGTH]


def content_hash(data: bytes) -> str:
    """Full-strength digest of file contents, used to detect re-imported files."""
    return hashlib.sha256(data).hexdigest()
