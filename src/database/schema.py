"""SQLite schema for the canonical portfolio dataset.

Money and unit quantities are stored as TEXT holding exact decimal strings.
SQLite has no decimal type, and REAL would silently introduce binary rounding
into values that get summed and reconciled to the cent. Callers convert with
Decimal on the way in and out; ad-hoc SQL can CAST where approximate is fine.

Every financial table carries source_document_id and source_page so any figure
can be traced back to the page it was read from.
"""

SCHEMA_VERSION = 5

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    document_id       TEXT PRIMARY KEY,
    filename          TEXT NOT NULL,
    kind              TEXT NOT NULL,
    period_start      TEXT,
    period_end        TEXT,
    page_count        INTEGER NOT NULL,
    content_sha256    TEXT NOT NULL UNIQUE,
    extraction_method TEXT NOT NULL,
    imported_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id    TEXT PRIMARY KEY,
    label         TEXT NOT NULL,
    base_currency TEXT NOT NULL DEFAULT 'AUD'
);

CREATE TABLE IF NOT EXISTS securities (
    security_id TEXT PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,
    currency    TEXT NOT NULL DEFAULT 'AUD'
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id     TEXT PRIMARY KEY,
    account_id         TEXT NOT NULL REFERENCES accounts(account_id),
    trade_date         TEXT NOT NULL,
    settlement_date    TEXT,
    type               TEXT NOT NULL,
    security_id        TEXT REFERENCES securities(security_id),
    units              TEXT,
    price              TEXT,
    gross_amount       TEXT,
    fees               TEXT,
    net_amount         TEXT,
    currency           TEXT NOT NULL,
    description        TEXT NOT NULL,
    ordinal            INTEGER NOT NULL DEFAULT 0,
    source_document_id TEXT NOT NULL REFERENCES documents(document_id),
    source_page        INTEGER,
    extraction_method  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS holdings (
    holding_id         TEXT PRIMARY KEY,
    account_id         TEXT NOT NULL REFERENCES accounts(account_id),
    reporting_date     TEXT NOT NULL,
    security_id        TEXT NOT NULL REFERENCES securities(security_id),
    units              TEXT NOT NULL,
    price              TEXT,
    market_value       TEXT NOT NULL,
    currency           TEXT NOT NULL,
    source_document_id TEXT NOT NULL REFERENCES documents(document_id),
    source_page        INTEGER,
    extraction_method  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS income_events (
    income_id          TEXT PRIMARY KEY,
    account_id         TEXT NOT NULL REFERENCES accounts(account_id),
    payment_date       TEXT NOT NULL,
    security_id        TEXT REFERENCES securities(security_id),
    amount             TEXT NOT NULL,
    rate_per_unit      TEXT,
    franking_credit    TEXT,
    tax_withheld       TEXT,
    ex_date            TEXT,
    currency           TEXT NOT NULL,
    source_document_id TEXT NOT NULL REFERENCES documents(document_id),
    source_page        INTEGER,
    extraction_method  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_valuations (
    valuation_id       TEXT PRIMARY KEY,
    account_id         TEXT NOT NULL REFERENCES accounts(account_id),
    reporting_date     TEXT NOT NULL,
    portfolio_value    TEXT NOT NULL,
    cash_balance       TEXT,
    investment_value   TEXT,
    accrued_income     TEXT,
    currency           TEXT NOT NULL,
    source_document_id TEXT NOT NULL REFERENCES documents(document_id),
    source_page        INTEGER,
    extraction_method  TEXT NOT NULL
);

-- Period flow summaries. Distinct from a valuation: these describe movement
-- over a window, and Phase 2 reconciles its own figures against them.
CREATE TABLE IF NOT EXISTS statement_periods (
    period_id          TEXT PRIMARY KEY,
    account_id         TEXT NOT NULL REFERENCES accounts(account_id),
    kind               TEXT NOT NULL,
    period_start       TEXT,
    period_end         TEXT NOT NULL,
    opening_value      TEXT,
    closing_value      TEXT,
    deposits           TEXT,
    withdrawals        TEXT,
    transfers_in       TEXT,
    transfers_out      TEXT,
    change_in_value    TEXT,
    income             TEXT,
    withholding_tax    TEXT,
    fees               TEXT,
    reported_return    TEXT,
    -- The cash balance the ledger opens on. Without it, a statement set that
    -- starts mid-life reconstructs cash from zero and is wrong by that amount.
    opening_cash       TEXT,
    source_document_id TEXT NOT NULL REFERENCES documents(document_id),
    source_page        INTEGER,
    extraction_method  TEXT NOT NULL
);

-- A record can appear in several documents: an annual statement repeats the
-- transactions of its four quarters. One source column per record could only
-- name the document that happened to be written last, which made provenance
-- depend on import order. Every appearance is recorded here instead, and each
-- record's canonical source is resolved deterministically as its earliest.
CREATE TABLE IF NOT EXISTS record_sources (
    record_type TEXT NOT NULL,
    record_id   TEXT NOT NULL,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    page        INTEGER,
    PRIMARY KEY (record_type, record_id, document_id)
);

CREATE INDEX IF NOT EXISTS ix_sources_record ON record_sources(record_type, record_id);

-- Annual tax reports. One per financial year, overlapping the statements
-- that cover the same period and adding detail rather than restating them.
CREATE TABLE IF NOT EXISTS tax_summaries (
    tax_summary_id                 TEXT PRIMARY KEY,
    financial_year                 INTEGER NOT NULL UNIQUE,
    period_start                   TEXT,
    period_end                     TEXT,
    gross_income                   TEXT,
    net_income_received            TEXT,
    dividend_franking_credits      TEXT,
    trust_franking_credits         TEXT,
    foreign_income_tax_offsets     TEXT,
    total_tax_offsets              TEXT,
    withholding_tax                TEXT,
    total_fees                     TEXT,
    gross_capital_gains            TEXT,
    net_capital_gain               TEXT,
    discounted_capital_gains       TEXT,
    cgt_concession                 TEXT,
    capital_losses_carried_forward TEXT,
    source_document_id             TEXT NOT NULL REFERENCES documents(document_id),
    source_page                    INTEGER,
    extraction_method              TEXT NOT NULL
);

-- Trust distributions are reported as annual totals per security with no
-- payment dates, so they cannot be attributed to individual income events.
CREATE TABLE IF NOT EXISTS security_tax_details (
    security_tax_id    TEXT PRIMARY KEY,
    financial_year     INTEGER NOT NULL,
    security_id        TEXT NOT NULL REFERENCES securities(security_id),
    franked_amount     TEXT,
    unfranked_amount   TEXT,
    franking_credit    TEXT,
    interest_income    TEXT,
    other_deductions   TEXT,
    source_document_id TEXT NOT NULL REFERENCES documents(document_id),
    source_page        INTEGER,
    extraction_method  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sectax_year ON security_tax_details(financial_year);

CREATE TABLE IF NOT EXISTS import_runs (
    run_id       TEXT PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    source_path  TEXT NOT NULL,
    documents_seen INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS issues (
    issue_id    TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES import_runs(run_id),
    severity    TEXT NOT NULL,
    code        TEXT NOT NULL,
    message     TEXT NOT NULL,
    document_id TEXT,
    filename    TEXT,
    page        INTEGER
);

CREATE INDEX IF NOT EXISTS ix_txn_date     ON transactions(trade_date);
CREATE INDEX IF NOT EXISTS ix_txn_security ON transactions(security_id);
CREATE INDEX IF NOT EXISTS ix_txn_type     ON transactions(type);
CREATE INDEX IF NOT EXISTS ix_hold_date    ON holdings(reporting_date);
CREATE INDEX IF NOT EXISTS ix_hold_security ON holdings(security_id);
CREATE INDEX IF NOT EXISTS ix_income_date  ON income_events(payment_date);
CREATE INDEX IF NOT EXISTS ix_val_date     ON portfolio_valuations(reporting_date);
"""
