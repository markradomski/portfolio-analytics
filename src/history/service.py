"""Query interface over the historical dataset.

Reads the stored time series rather than recomputing it, and returns plain
structured data with no presentation concerns. Higher-frequency series are
aggregated from the daily rows rather than recalculated, so a monthly figure
always agrees with the days inside it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.database.repository import Repository
from src.history.config import Granularity, ValuationStatus

ZERO = Decimal("0")

# Running totals: take the value as at the end of the bucket.
CUMULATIVE_FIELDS = (
    "cumulative_contributions", "cumulative_withdrawals", "income", "fees",
    "realised_gain", "invested_capital",
)
# Point-in-time: take the value on the last day of the bucket.
POSITION_FIELDS = (
    "total_value", "securities_value", "cash", "cost_basis", "unrealised_gain",
    "high_water_mark", "drawdown_value", "drawdown_pct", "return_index",
    "return_drawdown_pct",
)


def _dec(value) -> Decimal | None:
    return None if value is None else Decimal(value)


def _date(value) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _bucket_key(when: date, granularity: Granularity) -> date:
    """The last day of the bucket a date belongs to."""
    if granularity is Granularity.DAILY:
        return when
    if granularity is Granularity.WEEKLY:
        return when + timedelta(days=6 - when.weekday())
    if granularity is Granularity.MONTHLY:
        return date(when.year + (when.month // 12), (when.month % 12) + 1, 1) - timedelta(days=1)
    if granularity is Granularity.QUARTERLY:
        end_month = 3 * ((when.month - 1) // 3) + 3
        return date(when.year + (end_month // 12), (end_month % 12) + 1, 1) - timedelta(days=1)
    return date(when.year, 12, 31)


class HistoryService:
    def __init__(self, repo: Repository):
        self.repo = repo

    # -- portfolio -----------------------------------------------------------

    def portfolio_history(self, start: date | None = None, end: date | None = None,
                          granularity: Granularity = Granularity.DAILY) -> list[dict]:
        clauses, params = [], []
        if start:
            clauses.append("date >= ?"), params.append(start.isoformat())
        if end:
            clauses.append("date <= ?"), params.append(end.isoformat())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.repo.rows(
            f"SELECT * FROM portfolio_daily{where} ORDER BY date", tuple(params))
        daily = [dict(r) for r in rows]
        if granularity is Granularity.DAILY:
            return daily

        # Aggregate by taking the last day of each bucket: every field here is
        # either a running total or a point-in-time state, so the closing day
        # of a period is the period's value.
        buckets: dict[date, dict] = {}
        for row in daily:
            buckets[_bucket_key(_date(row["date"]), granularity)] = row
        return [dict(row, period_end=key.isoformat())
                for key, row in sorted(buckets.items())]

    def portfolio_value(self, on: date) -> dict | None:
        rows = self.repo.rows(
            "SELECT date, total_value, valuation_status, price_as_at"
            " FROM portfolio_daily WHERE date = ?", (on.isoformat(),))
        return dict(rows[0]) if rows else None

    def portfolio_state(self, on: date) -> dict | None:
        rows = self.repo.rows("SELECT * FROM portfolio_daily WHERE date = ?",
                              (on.isoformat(),))
        if not rows:
            return None
        state = dict(rows[0])
        state["holdings"] = [dict(r) for r in self.repo.rows(
            "SELECT h.*, s.code FROM holding_daily h"
            " JOIN securities s USING (security_id)"
            " WHERE h.date = ? ORDER BY s.code", (on.isoformat(),))]
        return state

    # -- holdings and allocation --------------------------------------------

    def holdings_history(self, security_id: str | None = None,
                         start: date | None = None,
                         end: date | None = None) -> list[dict]:
        clauses, params = [], []
        if security_id:
            clauses.append("h.security_id = ?"), params.append(security_id)
        if start:
            clauses.append("h.date >= ?"), params.append(start.isoformat())
        if end:
            clauses.append("h.date <= ?"), params.append(end.isoformat())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return [dict(r) for r in self.repo.rows(
            f"SELECT h.*, s.code FROM holding_daily h"
            f" JOIN securities s USING (security_id){where}"
            f" ORDER BY h.date, s.code", tuple(params))]

    def allocation_history(self, by: str = "security",
                           granularity: Granularity = Granularity.MONTHLY) -> list[dict]:
        """Allocation through time, by security or by asset class."""
        rows = self.repo.rows(
            "SELECT h.date, h.security_id, s.code, h.asset_class, h.market_value,"
            " h.allocation_pct FROM holding_daily h JOIN securities s"
            " USING (security_id) WHERE h.market_value IS NOT NULL ORDER BY h.date")

        buckets: dict[date, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        cash_by_bucket: dict[date, Decimal] = {}
        for row in rows:
            when = _bucket_key(_date(row["date"]), granularity)
            key = row["code"] if by == "security" else row["asset_class"]
            # Later dates in a bucket overwrite earlier ones: the bucket's
            # allocation is its closing allocation.
            if buckets[when].get("__date__") != row["date"]:
                if buckets[when].get("__date__") is not None and \
                        row["date"] > buckets[when]["__date__"]:
                    buckets[when] = defaultdict(Decimal)
                buckets[when]["__date__"] = row["date"]
            buckets[when][key] += Decimal(row["market_value"])

        for when in list(buckets):
            closing = buckets[when].pop("__date__", None)
            cash = self.repo.rows(
                "SELECT cash FROM portfolio_daily WHERE date = ?", (closing,))
            cash_by_bucket[when] = Decimal(cash[0]["cash"]) if cash else ZERO

        out = []
        for when in sorted(buckets):
            weights = dict(buckets[when])
            if by != "security":
                weights.setdefault("cash", ZERO)
                weights["cash"] += cash_by_bucket[when]
            total = sum(weights.values(), ZERO)
            out.append({
                "date": when.isoformat(),
                "total": str(total),
                "weights": {k: str(v) for k, v in sorted(weights.items())},
                "allocation_pct": {k: str(v / total) if total > ZERO else None
                                   for k, v in sorted(weights.items())},
            })
        return out

    # -- flows and income ----------------------------------------------------

    def contribution_history(self,
                             granularity: Granularity = Granularity.YEARLY) -> list[dict]:
        """Contributions and withdrawals per period, plus running totals.

        Kept separate from performance on purpose: a portfolio that grew
        because more was paid in did not earn anything.
        """
        rows = self.repo.rows(
            "SELECT date, cumulative_contributions, cumulative_withdrawals"
            " FROM portfolio_daily ORDER BY date")
        buckets: dict[date, dict] = {}
        for row in rows:
            buckets[_bucket_key(_date(row["date"]), granularity)] = row

        out, previous_in, previous_out = [], ZERO, ZERO
        for when in sorted(buckets):
            row = buckets[when]
            total_in = Decimal(row["cumulative_contributions"])
            total_out = Decimal(row["cumulative_withdrawals"])
            contributions = total_in - previous_in
            withdrawals = total_out - previous_out
            out.append({
                "period_end": when.isoformat(),
                "contributions": str(contributions),
                "withdrawals": str(withdrawals),
                "net_contributions": str(contributions + withdrawals),
                "cumulative_contributions": str(total_in),
                "cumulative_withdrawals": str(total_out),
                "cumulative_net": str(total_in + total_out),
            })
            previous_in, previous_out = total_in, total_out
        return out

    def income_history(self, granularity: Granularity = Granularity.YEARLY,
                       by_security: bool = False) -> list[dict]:
        rows = self.repo.rows(
            "SELECT i.date, i.kind, i.amount, i.franking_credit, i.tax_withheld,"
            " s.code FROM income_daily i LEFT JOIN securities s USING (security_id)"
            " ORDER BY i.date")
        buckets: dict[tuple, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal))
        for row in rows:
            when = _bucket_key(_date(row["date"]), granularity)
            key = (when, row["code"]) if by_security else (when,)
            bucket = buckets[key]
            bucket[row["kind"].lower() + "s"] += Decimal(row["amount"])
            bucket["gross_income"] += Decimal(row["amount"])
            bucket["franking_credits"] += _dec(row["franking_credit"]) or ZERO
            bucket["tax_withheld"] += _dec(row["tax_withheld"]) or ZERO

        out = []
        # Interest income has no security (key[1] is None), which cannot be
        # compared against a code string -- sort on a string-safe form of the
        # key instead of the raw tuple.
        for key in sorted(buckets, key=lambda k: (k[0], k[1] or "") if len(k) > 1 else k):
            values = buckets[key]
            record = {"period_end": key[0].isoformat()}
            if by_security:
                record["code"] = key[1]
            record.update({k: str(v) for k, v in sorted(values.items())})
            record["net_income"] = str(values["gross_income"] - values["tax_withheld"])
            out.append(record)
        return out

    # -- performance ---------------------------------------------------------

    def period_summaries(self, granularity: Granularity) -> list[dict]:
        return [dict(r) for r in self.repo.rows(
            "SELECT * FROM period_summaries WHERE granularity = ?"
            " ORDER BY period_start", (granularity.value,))]

    def performance_history(self) -> list[dict]:
        return [dict(r) for r in self.repo.rows(
            "SELECT * FROM performance_periods ORDER BY as_at, label")]

    def drawdown_history(self) -> list[dict]:
        return [dict(r) for r in self.repo.rows(
            "SELECT * FROM drawdown_episodes ORDER BY peak_date")]

    def high_water_history(self, granularity: Granularity = Granularity.MONTHLY) -> list[dict]:
        rows = self.portfolio_history(granularity=granularity)
        return [{"date": r["date"], "high_water_mark": r["high_water_mark"],
                 "total_value": r["total_value"],
                 "distance_from_high": r["drawdown_value"],
                 "distance_from_high_pct": r["drawdown_pct"],
                 "investment_drawdown_pct": r["return_drawdown_pct"]} for r in rows]

    def milestones(self) -> list[dict]:
        return [dict(r) for r in self.repo.rows(
            "SELECT * FROM milestones ORDER BY date, kind")]

    # -- quality -------------------------------------------------------------

    def data_quality(self) -> dict:
        counts = {r["valuation_status"]: r["n"] for r in self.repo.rows(
            "SELECT valuation_status, COUNT(*) AS n FROM portfolio_daily"
            " GROUP BY valuation_status")}
        total = sum(counts.values())
        return {
            "days": total,
            "by_status": counts,
            "priced_dates": self.repo.rows(
                "SELECT COUNT(DISTINCT price_as_at) AS n FROM portfolio_daily"
                " WHERE price_as_at IS NOT NULL")[0]["n"],
            "days_without_value": self.repo.rows(
                "SELECT COUNT(*) AS n FROM portfolio_daily"
                " WHERE total_value IS NULL")[0]["n"],
        }

    def reconciliation(self) -> list[dict]:
        """Reported vs stored history at every date Vanguard reported one."""
        out = []
        for row in self.repo.rows(
            "SELECT v.reporting_date, v.portfolio_value, v.accrued_income,"
            " d.total_value, d.valuation_status FROM portfolio_valuations v"
            " LEFT JOIN portfolio_daily d ON d.date = v.reporting_date"
            " ORDER BY v.reporting_date"
        ):
            reported = Decimal(row["portfolio_value"])
            accrued = _dec(row["accrued_income"]) or ZERO
            calculated = _dec(row["total_value"])
            difference = (calculated + accrued - reported
                          if calculated is not None else None)
            out.append({
                "date": row["reporting_date"],
                "reported": str(reported),
                "calculated": str(calculated + accrued) if calculated is not None else None,
                "difference": str(difference) if difference is not None else None,
                "status": ("SKIP" if difference is None
                           else "PASS" if abs(difference) <= Decimal("0.05") else "FAIL"),
            })
        return out
