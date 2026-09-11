"""Step 9: the Portfolio Growth dataset and its reconciliation.

Builds a small, fully controlled synthetic ledger directly (accounts,
transactions, valuations -- bypassing PDF parsing, which is irrelevant to
this module's own logic) rather than reusing the shared PDF-derived
fixture, so every contribution/withdrawal/valuation date and amount here is
exact and known in advance. The portfolio is deliberately 100% cash (no
securities) so portfolio_value equals the ledger's own cash balance exactly
at every date -- isolating "did growth.py assemble the numbers correctly"
from "did the pricing/holdings engine value something correctly" (already
covered elsewhere).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal as D

import pytest

from src.analytics.growth import (portfolio_growth, portfolio_growth_summary,
                                  growth_reconciliation)
from src.database.repository import Repository
from src.engine.ledger import Ledger
from src.history.service import HistoryService
from src.history.store import HistoryStore
from src.models import (Account, Document, DocumentKind, PortfolioValuation,
                        Provenance, Transaction, TxnType)

ACCOUNT_ID = "A1"
DOC_ID = "D1"


def _prov():
    return Provenance(document_id=DOC_ID, page=1)


def _txn(tid, when, kind, net, description=""):
    return Transaction(
        transaction_id=tid, account_id=ACCOUNT_ID, trade_date=when, settlement_date=when,
        type=kind, security_id=None, units=None, price=None, gross_amount=D(str(net)),
        fees=None, net_amount=D(str(net)), currency="AUD", description=description,
        ordinal=0, provenance=_prov())


def _valuation(vid, when, value, cash):
    return PortfolioValuation(
        valuation_id=vid, account_id=ACCOUNT_ID, reporting_date=when,
        portfolio_value=D(str(value)), cash_balance=D(str(cash)), investment_value=D("0"),
        accrued_income=None, currency="AUD", provenance=_prov())


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "growth.db")
    r.upsert_account(Account(account_id=ACCOUNT_ID, label="primary"))
    r.upsert_document(Document(
        document_id=DOC_ID, filename="test.pdf", kind=DocumentKind.QUARTERLY,
        period_start=date(2024, 1, 1), period_end=date(2024, 3, 31), page_count=1,
        content_sha256="x", extraction_method="test", imported_at=datetime.now()))
    yield r
    r.close()


@pytest.fixture
def reconciled_repo(repo):
    """One deposit in January, a second in February, a withdrawal in March,
    plus small interest payments so investment_gain is a real, nonzero,
    independently-verifiable number -- and every reported valuation matches
    the ledger's own cash balance exactly (a perfectly reconciled dataset)."""
    repo.upsert_transactions([
        _txn("t1", date(2024, 1, 15), TxnType.DEPOSIT, 1000, "Deposit 1"),
        _txn("t2", date(2024, 1, 20), TxnType.INTEREST, 10, "Interest"),
        _txn("t3", date(2024, 2, 15), TxnType.DEPOSIT, 2000, "Deposit 2"),
        _txn("t4", date(2024, 2, 20), TxnType.INTEREST, 15, "Interest"),
        _txn("t5", date(2024, 3, 10), TxnType.WITHDRAWAL, -500, "Withdrawal 1"),
        _txn("t6", date(2024, 3, 25), TxnType.INTEREST, 5, "Interest"),
    ])
    repo.upsert_valuations([
        _valuation("v1", date(2024, 1, 31), "1010.00", "1010.00"),
        _valuation("v2", date(2024, 2, 29), "3025.00", "3025.00"),
        _valuation("v3", date(2024, 3, 31), "2530.00", "2530.00"),
    ])
    HistoryStore(repo).rebuild()
    return repo


@pytest.fixture
def history(reconciled_repo):
    return HistoryService(reconciled_repo)


# -- contributions ------------------------------------------------------------

def test_a_single_contribution_appears_on_its_own_date(history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert points[date(2024, 1, 15)].contributions == D("1000.00")
    assert points[date(2024, 1, 15)].withdrawals == D("0.00")


def test_multiple_contributions_on_different_dates_are_each_attributed_to_their_own_day(
        history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert points[date(2024, 1, 15)].contributions == D("1000.00")
    assert points[date(2024, 2, 15)].contributions == D("2000.00")
    # A day with no contribution is exactly zero, not merely "small".
    assert points[date(2024, 1, 16)].contributions == D("0.00")


# -- withdrawals --------------------------------------------------------------

def test_a_single_withdrawal_appears_on_its_own_date_signed_negative(history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert points[date(2024, 3, 10)].withdrawals == D("-500.00")
    assert points[date(2024, 3, 10)].contributions == D("0.00")


def test_a_withdrawal_after_contributions_reduces_net_contributions_but_not_past_history(
        history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    before = points[date(2024, 3, 9)].net_contributions
    after = points[date(2024, 3, 10)].net_contributions
    assert before == D("3000.00")
    assert after == D("2500.00")
    # The withdrawal must not retroactively change an earlier day's figure.
    assert points[date(2024, 1, 31)].net_contributions == D("1000.00")


# -- net contributions ---------------------------------------------------------

def test_net_contributions_equals_contributions_minus_withdrawals_cumulatively(
        history, reconciled_repo):
    """Verifies the Step 9 formula directly: net = cumulative contributions
    - cumulative withdrawals (withdrawals are signed negative throughout
    this API, so the module adds them; the arithmetic result is identical)."""
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    end = points[date(2024, 3, 31)]
    total_contributed = D("3000.00")   # 1000 + 2000
    total_withdrawn = D("500.00")
    assert end.net_contributions == total_contributed - total_withdrawn


# -- portfolio growth (investment_gain = value - net_contributions) ----------

def test_investment_gain_equals_portfolio_value_minus_net_contributions(history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    for d in (date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)):
        row = points[d]
        assert row.investment_gain == row.portfolio_value - row.net_contributions

    # And the known, independently-computed interest total at each point.
    assert points[date(2024, 1, 31)].investment_gain == D("10.00")
    assert points[date(2024, 2, 29)].investment_gain == D("25.00")
    assert points[date(2024, 3, 31)].investment_gain == D("30.00")


# -- period investment gain/loss (the chart's Investment Gain/Investment
# Loss areas) -- day-over-day, not cumulative ------------------------------

def test_period_investment_gain_is_zero_on_a_pure_contribution_day(history, reconciled_repo):
    """Depositing money is not, itself, a gain -- confirms the formula's
    own point: contributions[t] is fully cancelled out of the delta. (The
    very first date in the series, 15 Jan, has no prior day to diff
    against at all -- covered separately below.)"""
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert points[date(2024, 2, 15)].period_investment_gain == D("0.00")


def test_period_investment_gain_is_zero_on_a_pure_withdrawal_day(history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert points[date(2024, 3, 10)].period_investment_gain == D("0.00")


def test_period_investment_gain_equals_that_days_own_interest_on_an_interest_day(
        history, reconciled_repo):
    """The one thing genuinely generated by the investments each month --
    isolated from the much larger deposits/withdrawals landing on other
    days entirely."""
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert points[date(2024, 1, 20)].period_investment_gain == D("10.00")
    assert points[date(2024, 2, 20)].period_investment_gain == D("15.00")
    assert points[date(2024, 3, 25)].period_investment_gain == D("5.00")


def test_period_investment_gain_is_zero_on_a_day_with_no_events_at_all(history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert points[date(2024, 1, 16)].period_investment_gain == D("0.00")


def test_period_investment_gain_is_none_for_the_very_first_point_with_no_prior_day(
        history, reconciled_repo):
    points = portfolio_growth(history, reconciled_repo)
    assert points[0].date == date(2024, 1, 15)
    assert points[0].period_investment_gain is None


def test_period_investment_gain_equals_balance_change_minus_that_days_own_flows(
        history, reconciled_repo):
    """Directly verifies the identity a later chart update states as its
    own formula: gain/loss[t] = balance[t] - balance[t-1] -
    (contributions[t] + withdrawals[t])."""
    points = portfolio_growth(history, reconciled_repo)
    by_date = {p.date: p for p in points}
    for i in range(1, len(points)):
        p, prev = points[i], points[i - 1]
        if p.portfolio_value is None or prev.portfolio_value is None:
            continue
        expected = (p.portfolio_value - prev.portfolio_value) - (p.contributions + p.withdrawals)
        assert by_date[p.date].period_investment_gain == expected


def test_period_investment_gain_sums_to_the_total_cumulative_gain_over_the_whole_period(
        history, reconciled_repo):
    points = portfolio_growth(history, reconciled_repo)
    total = sum((p.period_investment_gain for p in points if p.period_investment_gain is not None), D("0"))
    # The first point's own gain (0.00, established above) plus every
    # day-over-day delta after it must reconstruct the final cumulative
    # investment_gain exactly.
    assert points[0].investment_gain + total == points[-1].investment_gain


def test_period_investment_gain_for_a_mid_series_window_uses_the_day_before_the_window(
        history, reconciled_repo):
    """The window starts after the 20 Feb interest payment -- the first
    point in the window must still show zero period gain (nothing happened
    that specific day), not a spurious carry-in from outside the window."""
    points = {p.date: p for p in portfolio_growth(
        history, reconciled_repo, start=date(2024, 2, 21), end=date(2024, 2, 29))}
    assert points[date(2024, 2, 21)].period_investment_gain == D("0.00")


def test_cash_flow_events_are_attached_to_the_matching_date_with_provenance(history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    events = points[date(2024, 1, 15)].cash_flow_events
    assert len(events) == 1
    assert events[0].type == "CONTRIBUTION"
    assert events[0].amount == D("1000.00")
    assert events[0].transaction_id == "t1"   # traceable back to its own source row


def test_growth_is_never_fabricated_for_a_date_the_series_does_not_contain(history, reconciled_repo):
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    assert date(2023, 12, 31) not in points


def test_an_arbitrary_date_range_can_be_requested(history, reconciled_repo):
    points = portfolio_growth(history, reconciled_repo, start=date(2024, 2, 1), end=date(2024, 2, 29))
    assert all(date(2024, 2, 1) <= p.date <= date(2024, 2, 29) for p in points)
    # The delta for the first day of a mid-series window must still be
    # correct relative to what came immediately before the window, not
    # relative to zero.
    first = next(p for p in points if p.date == date(2024, 2, 15))
    assert first.contributions == D("2000.00")


# -- historical correctness across the full period ---------------------------

def test_the_full_historical_period_has_no_gaps_and_ends_at_the_last_known_value(
        history, reconciled_repo):
    points = portfolio_growth(history, reconciled_repo)
    assert points[0].date == date(2024, 1, 15)
    # Extends to the last *reported* date (31 Mar), one past the last
    # ledger event (25 Mar) -- the daily series always covers every
    # statement date, not only days something happened.
    assert points[-1].date == date(2024, 3, 31)
    # Every day in between is present (a 100%-cash portfolio has no
    # unpriced gap days) -- one row per calendar day, no skips.
    all_dates = [p.date for p in points]
    assert all_dates == sorted(all_dates)
    assert len(all_dates) == (all_dates[-1] - all_dates[0]).days + 1


# -- summary --------------------------------------------------------------------

def test_growth_summary_matches_the_final_growth_point(history):
    summary = portfolio_growth_summary(history)
    assert summary.current_value == D("2530.00")
    assert summary.net_contributions == D("2500.00")
    assert summary.investment_gain == D("30.00")
    # gain_per_dollar_contributed, not an annualised return -- see
    # contributions.py's own ContributionEfficiency docstring.
    assert summary.growth_pct == D("30.00") / D("2500.00")


# -- reconciliation: perfectly reconciled data -------------------------------

def test_reconciliation_passes_when_every_reported_valuation_matches_the_ledger(
        reconciled_repo):
    ledger = Ledger.from_repository(reconciled_repo)
    checks = growth_reconciliation(reconciled_repo, ledger)
    portfolio_value_checks = [c for c in checks if c.subject == "portfolio value"]
    assert len(portfolio_value_checks) == 3
    assert all(c.status == "PASS" for c in portfolio_value_checks)
    assert all(c.difference == D("0.00") for c in portfolio_value_checks)
    assert all(c.calculated == c.source for c in portfolio_value_checks)


# -- reconciliation: data containing a discrepancy ---------------------------

@pytest.fixture
def discrepant_repo(repo):
    """Same shape as reconciled_repo, but the January statement reports a
    portfolio value the ledger's own transactions do not support -- a real,
    calculated discrepancy, not a rounding artefact."""
    repo.upsert_transactions([
        _txn("t1", date(2024, 1, 15), TxnType.DEPOSIT, 1000, "Deposit 1"),
    ])
    repo.upsert_valuations([
        # Ledger says cash is 1000.00 on this date; the statement claims
        # 1500.00 -- a $500 unexplained difference.
        _valuation("v1", date(2024, 1, 31), "1500.00", "1500.00"),
    ])
    HistoryStore(repo).rebuild()
    return repo


def test_reconciliation_surfaces_a_discrepancy_rather_than_hiding_it(discrepant_repo):
    ledger = Ledger.from_repository(discrepant_repo)
    checks = growth_reconciliation(discrepant_repo, ledger)
    portfolio_value_check = next(c for c in checks if c.subject == "portfolio value")
    assert portfolio_value_check.status == "FAIL"
    assert portfolio_value_check.calculated == D("1000.00")
    assert portfolio_value_check.source == D("1500.00")
    assert portfolio_value_check.difference == D("-500.00")


# -- performance: a cash-flow-heavy scenario must not be mislabelled --------

def test_a_large_contribution_is_never_presented_as_investment_return(history, reconciled_repo):
    """The $2000 February deposit dwarfs the $15 of interest earned that
    month -- if investment_gain (or anything derived from it here) were
    mistaken for a return, this portfolio would look like it grew ~67% in
    a month. growth.py must never produce or label a percentage like that;
    only contributions.py's own gain_per_dollar_contributed exists here,
    and its docstring is explicit that it is not a return methodology."""
    points = {p.date: p for p in portfolio_growth(history, reconciled_repo)}
    row = points[date(2024, 2, 29)]
    assert row.investment_gain == D("25.00")  # the real, small, interest-only gain
    assert not hasattr(row, "return_pct")
    assert not hasattr(row, "annualised_return")

    summary = portfolio_growth_summary(history)
    # growth_pct is a plain ratio (gain / net contributions so far), never
    # annualised and never called a "return" anywhere in this module.
    assert summary.growth_pct is not None
    assert summary.growth_pct < D("0.02")  # nowhere near the ~67% a mislabelled figure would show
