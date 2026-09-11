"""Privacy-safe aggregate reporting for the Stage 2 trade matcher.

Emits only counts and Decimal aggregates -- never a description, a security
name, an account field or a row's raw content.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from src.ingestion.vanguard_csv.records import TradeSide
from src.ingestion.vanguard_csv.trade_match import (
    DateRelation, MatchResult, MatchStatus,
)


def summarise(result: MatchResult) -> dict[str, object]:
    matched = result.matched
    deltas_days = [c.date_delta_days for c in matched if c.date_delta_days is not None]
    value_deltas = [
        abs(Decimal(c.reconciliation_deltas.get("value_delta", "0"))) for c in matched
    ]
    rel = Counter(c.date_relation for c in matched if c.date_relation)
    return {
        "matched_buy": sum(1 for c in matched if c.side is TradeSide.BUY),
        "matched_sell": sum(1 for c in matched if c.side is TradeSide.SELL),
        "matched_total": len(matched),
        "status_counts": result.counts(),
        "unmatched_investment": result.counts()[MatchStatus.UNMATCHED_INVESTMENT.value],
        "unmatched_cash": result.counts()[MatchStatus.UNMATCHED_CASH.value],
        "ambiguous": result.counts()[MatchStatus.AMBIGUOUS.value],
        "security_mismatch": result.counts()[MatchStatus.SECURITY_MISMATCH.value],
        "quantity_mismatch": result.counts()[MatchStatus.QUANTITY_MISMATCH.value],
        "value_mismatch": result.counts()[MatchStatus.VALUE_MISMATCH.value],
        "date": {
            "same_day": rel.get(DateRelation.SAME_DAY, 0),
            "next_day": rel.get(DateRelation.NEXT_DAY, 0),
            "plus_two_days": rel.get(DateRelation.PLUS_TWO_DAYS, 0),
            "other_positive_delta": rel.get(DateRelation.OTHER_POSITIVE_DELTA, 0),
            "negative_delta": rel.get(DateRelation.NEGATIVE_DELTA, 0),
            "max_abs_delta_days": max((abs(d) for d in deltas_days), default=0),
        },
        "value": {
            "exact_matches": sum(1 for d in value_deltas if d == 0),
            "within_tolerance": sum(1 for d in value_deltas if d != 0),
            "max_residual": str(max(value_deltas, default=Decimal("0"))),
        },
        "one_to_one_ok": _one_to_one_ok(result),
        "clean": result.is_clean(),
    }


def _one_to_one_ok(result: MatchResult) -> bool:
    try:
        result.assert_one_to_one()
        return True
    except AssertionError:
        return False


def render(result: MatchResult, *, inv_buy: int, inv_sell: int,
           cash_buy: int, cash_sell: int) -> str:
    s = summarise(result)
    d, v = s["date"], s["value"]
    return "\n".join([
        "Vanguard cross-file trade matching -- sanitised aggregates",
        "",
        f"  investment side : BUY {inv_buy}  SELL {inv_sell}",
        f"  cash side       : BUY {cash_buy}  SELL {cash_sell}",
        "",
        f"  matched BUY      : {s['matched_buy']}",
        f"  matched SELL     : {s['matched_sell']}",
        f"  matched total    : {s['matched_total']}",
        f"  unmatched inv    : {s['unmatched_investment']}",
        f"  unmatched cash   : {s['unmatched_cash']}",
        f"  ambiguous        : {s['ambiguous']}",
        f"  security mismatch: {s['security_mismatch']}",
        f"  quantity mismatch: {s['quantity_mismatch']}",
        f"  value mismatch   : {s['value_mismatch']}",
        "",
        f"  date  same-day {d['same_day']}  +1 {d['next_day']}  +2 {d['plus_two_days']}"
        f"  other+ {d['other_positive_delta']}  neg {d['negative_delta']}"
        f"  max|delta| {d['max_abs_delta_days']}d",
        f"  value exact {v['exact_matches']}  within-tol {v['within_tolerance']}"
        f"  max residual {v['max_residual']}",
        "",
        f"  one-to-one ok : {s['one_to_one_ok']}",
        f"  CLEAN         : {s['clean']}",
    ])
