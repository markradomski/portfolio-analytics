"""Persistence and rebuilding of the historical dataset.

A rebuild is deterministic: the same ledger always produces the same rows. An
incremental rebuild recomputes only from a given date, carrying in the state
that preceded it, and must produce exactly what a full rebuild would.

Derived tables (summaries, drawdowns, milestones) are always recomputed from
the complete daily series, because they depend on the whole history -- a
high-water mark cannot be updated from a fragment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.database.repository import Repository, _text
from src.engine.config import DEFAULT_CONFIG, EngineConfig
from src.history.analytics import drawdown_episodes, milestones
from src.history.config import (DEFAULT_HISTORY_CONFIG, Granularity,
                                HistoryConfig, ValuationStatus)
from src.history.generator import DailyRow, HistoryGenerator, HoldingRow
from src.history.periods import performance_periods, summarise
from src.history.schema import HISTORY_DDL, HISTORY_SCHEMA_VERSION
from src.ids import make_id

ZERO = Decimal("0")

DAILY_TABLES = ("portfolio_daily", "holding_daily", "income_daily")
DERIVED_TABLES = ("period_summaries", "performance_periods",
                  "drawdown_episodes", "milestones")


@dataclass
class RebuildResult:
    days: int
    holdings: int
    income: int
    summaries: int
    episodes: int
    milestones: int
    rebuilt_from: date | None
    fingerprint: str


class HistoryStore:
    def __init__(self, repo: Repository, config: EngineConfig = DEFAULT_CONFIG,
                 history_config: HistoryConfig = DEFAULT_HISTORY_CONFIG):
        self.repo = repo
        self.config = config
        self.history_config = history_config
        self._migrate()

    def _migrate(self) -> None:
        """Create the history tables, rebuilding them if their shape changed.

        Everything here is derived from the ledger, so a schema change is a
        drop-and-regenerate rather than a data migration: nothing is lost that
        cannot be recomputed.
        """
        stored = self.repo.rows(
            "SELECT value FROM schema_meta WHERE key = 'history_version'")
        current = str(HISTORY_SCHEMA_VERSION)
        if stored and stored[0]["value"] != current:
            for table in (*DAILY_TABLES, *DERIVED_TABLES, "history_runs"):
                self.repo.conn.execute(f"DROP TABLE IF EXISTS {table}")
        self.repo.conn.executescript(HISTORY_DDL)
        self.repo.conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value)"
            " VALUES ('history_version', ?)", (current,))
        self.repo.commit()

    # -- writing -------------------------------------------------------------

    def _write_daily(self, rows: list[DailyRow]) -> int:
        self.repo.conn.executemany(
            "INSERT OR REPLACE INTO portfolio_daily(date, total_value,"
            " securities_value, cash, cost_basis, invested_capital,"
            " realised_gain, unrealised_gain, dividends, distributions, income,"
            " fees, cumulative_contributions, cumulative_withdrawals,"
            " high_water_mark, drawdown_value, drawdown_pct, return_index,"
            " index_as_at, return_high_water, return_drawdown_pct,"
            " valuation_status, valuation_source, price_as_at, source_count,"
            " calculation_method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(_text(r.date), _text(r.total_value), _text(r.securities_value),
              _text(r.cash), _text(r.cost_basis), _text(r.invested_capital),
              _text(r.realised_gain), _text(r.unrealised_gain),
              _text(r.dividends), _text(r.distributions), _text(r.income),
              _text(r.fees), _text(r.cumulative_contributions),
              _text(r.cumulative_withdrawals), _text(r.high_water_mark),
              _text(r.drawdown_value), _text(r.drawdown_pct),
              _text(r.return_index), _text(r.index_as_at),
              _text(r.return_high_water), _text(r.return_drawdown_pct),
              r.valuation_status.value, r.valuation_source,
              _text(r.price_as_at), r.source_count,
              "phase2-state-replay") for r in rows])
        return len(rows)

    def _write_holdings(self, rows: list[DailyRow]) -> int:
        payload = [
            (_text(h.date), h.security_id, _text(h.units), _text(h.price),
             _text(h.market_value), _text(h.cost_basis),
             _text(h.unrealised_gain), _text(h.allocation_pct),
             h.asset_class.value, h.valuation_status.value, _text(h.price_as_at))
            for row in rows for h in row.holdings]
        self.repo.conn.executemany(
            "INSERT OR REPLACE INTO holding_daily(date, security_id, units,"
            " price, market_value, cost_basis, unrealised_gain, allocation_pct,"
            " asset_class, valuation_status, price_as_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)", payload)
        return len(payload)

    def _write_income(self, since: date | None) -> int:
        """Income at daily grain, straight from the recorded events."""
        clause = " WHERE i.payment_date >= ?" if since else ""
        params = (since.isoformat(),) if since else ()
        rows = self.repo.rows(
            "SELECT i.payment_date, i.security_id, i.amount, i.franking_credit,"
            " i.tax_withheld, s.type FROM income_events i"
            " LEFT JOIN securities s USING (security_id)" + clause, params)
        payload = [(r["payment_date"], r["security_id"],
                    "DISTRIBUTION" if r["type"] in ("ETF", "MANAGED_FUND") else "DIVIDEND",
                    r["amount"], r["franking_credit"], r["tax_withheld"])
                   for r in rows]

        interest_clause = " AND trade_date >= ?" if since else ""
        payload += [(r["trade_date"], None, "INTEREST", r["net_amount"], None, None)
                    for r in self.repo.rows(
                        "SELECT trade_date, net_amount FROM transactions"
                        " WHERE type = 'INTEREST'" + interest_clause, params)]

        self.repo.conn.executemany(
            "INSERT OR REPLACE INTO income_daily(date, security_id, kind, amount,"
            " franking_credit, tax_withheld) VALUES (?,?,?,?,?,?)", payload)
        return len(payload)

    def _write_derived(self, rows: list[DailyRow], generator: HistoryGenerator):
        for table in DERIVED_TABLES:
            self.repo.conn.execute(f"DELETE FROM {table}")

        flows = generator.cash_engine.external_flows(generator.ledger)

        summaries = []
        for granularity in (Granularity.MONTHLY, Granularity.QUARTERLY,
                            Granularity.YEARLY):
            summaries.extend(summarise(rows, granularity, flows))
        self.repo.conn.executemany(
            "INSERT OR REPLACE INTO period_summaries(period_id, granularity,"
            " period_start, period_end, opening_value, closing_value,"
            " contributions, withdrawals, net_contributions, income, fees,"
            " realised_gain, investment_gain, twrr, xirr, valuation_status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(s.period_id, s.granularity.value, _text(s.period_start),
              _text(s.period_end), _text(s.opening_value), _text(s.closing_value),
              _text(s.contributions), _text(s.withdrawals),
              _text(s.net_contributions), _text(s.income), _text(s.fees),
              _text(s.realised_gain), _text(s.investment_gain), _text(s.twrr),
              _text(s.xirr), s.valuation_status.value) for s in summaries])

        periods = performance_periods(rows, flows)
        self.repo.conn.executemany(
            "INSERT OR REPLACE INTO performance_periods(label, as_at, start_date,"
            " end_date, total_return, capital_return, income_return, twrr, xirr,"
            " status, note) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(p.label, _text(p.as_at), _text(p.start_date), _text(p.end_date),
              _text(p.total_return), _text(p.capital_return),
              _text(p.income_return), _text(p.twrr), _text(p.xirr),
              p.status.value, p.note) for p in periods])

        episodes = drawdown_episodes(rows, self.history_config)
        self.repo.conn.executemany(
            "INSERT OR REPLACE INTO drawdown_episodes(episode_id, peak_date,"
            " peak_value, trough_date, trough_value, drawdown_value,"
            " drawdown_pct, recovery_date, recovery_days, valuation_status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(e.episode_id, _text(e.peak_date), _text(e.peak_value),
              _text(e.trough_date), _text(e.trough_value),
              _text(e.drawdown_value), _text(e.drawdown_pct),
              _text(e.recovery_date), e.recovery_days,
              e.valuation_status.value) for e in episodes])

        marks = milestones(rows, generator.ledger.events, self.history_config)
        self.repo.conn.executemany(
            "INSERT OR REPLACE INTO milestones(milestone_id, kind, date, value,"
            " description) VALUES (?,?,?,?,?)",
            [(m.milestone_id, m.kind, _text(m.date), _text(m.value),
              m.description) for m in marks])

        return len(summaries), len(episodes), len(marks)

    # -- rebuilding ----------------------------------------------------------

    def rebuild(self, from_date: date | None = None) -> RebuildResult:
        generator = HistoryGenerator(self.repo, self.config, self.history_config)
        all_dates = generator.date_range()
        if not all_dates:
            return RebuildResult(0, 0, 0, 0, 0, 0, from_date, generator.fingerprint())

        if from_date is None:
            for table in DAILY_TABLES:
                self.repo.conn.execute(f"DELETE FROM {table}")
            dates = all_dates
            opening_high_water, opening_return_high_water = ZERO, None
        else:
            for table in DAILY_TABLES:
                self.repo.conn.execute(f"DELETE FROM {table} WHERE date >= ?",
                                       (from_date.isoformat(),))
            dates = [d for d in all_dates if d >= from_date]
            # High-water marks only ever rise, so the last row before the
            # boundary carries both. MAX() is deliberately not used: these are
            # decimal strings, and MAX would compare them lexicographically --
            # "9,999" would beat "10,000".
            carried = self.repo.rows(
                "SELECT high_water_mark, return_high_water FROM portfolio_daily"
                " WHERE date < ? ORDER BY date DESC LIMIT 1",
                (from_date.isoformat(),))
            opening_high_water = (Decimal(carried[0]["high_water_mark"])
                                  if carried and carried[0]["high_water_mark"]
                                  else ZERO)
            opening_return_high_water = (
                Decimal(carried[0]["return_high_water"])
                if carried and carried[0]["return_high_water"] else None)

        new_rows = generator.generate(dates, opening_high_water,
                                      opening_return_high_water)
        days = self._write_daily(new_rows)
        holdings = self._write_holdings(new_rows)
        income = self._write_income(from_date)

        # Derived tables depend on the whole series, so they are recomputed
        # from everything now stored rather than from the fragment just built.
        complete = self.load_daily() if from_date else new_rows
        summaries, episodes, marks = self._write_derived(complete, generator)

        run_id = make_id("HRUN", generator.fingerprint(), from_date)
        self.repo.conn.execute(
            "INSERT OR REPLACE INTO history_runs(run_id, generated_at,"
            " rebuilt_from, ledger_fingerprint, days) VALUES (?,?,?,?,?)",
            (run_id, datetime.now().isoformat(), _text(from_date),
             generator.fingerprint(), days))
        self.repo.commit()

        return RebuildResult(days, holdings, income, summaries, episodes,
                             marks, from_date, generator.fingerprint())

    # -- reading -------------------------------------------------------------

    def load_daily(self) -> list[DailyRow]:
        """Reconstruct daily rows from storage, for derived recalculation."""
        generator = HistoryGenerator(self.repo, self.config, self.history_config)
        return generator.generate()

    def is_stale(self) -> bool:
        """True when the ledger has changed since the history was built."""
        rows = self.repo.rows(
            "SELECT ledger_fingerprint FROM history_runs"
            " ORDER BY generated_at DESC LIMIT 1")
        if not rows:
            return True
        current = HistoryGenerator(self.repo, self.config,
                                   self.history_config).fingerprint()
        return rows[0]["ledger_fingerprint"] != current
