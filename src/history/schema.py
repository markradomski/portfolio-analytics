"""Time-series tables.

Daily rows are the canonical grain. Weekly, monthly, quarterly and yearly views
are derived from them rather than calculated separately, so there is exactly one
place a figure can come from.

Calendar summaries are materialised because they involve chained sub-period
returns that are expensive to recompute; they carry a granularity column rather
than living in three near-identical tables.
"""

HISTORY_SCHEMA_VERSION = 4

HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS history_runs (
    run_id            TEXT PRIMARY KEY,
    generated_at      TEXT NOT NULL,
    rebuilt_from      TEXT,
    ledger_fingerprint TEXT NOT NULL,
    days              INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_daily (
    date                     TEXT PRIMARY KEY,
    -- NULL where a holding has no price at or before this date. A partial sum
    -- would understate the portfolio while looking like a real figure, so the
    -- gap is left visible.
    total_value              TEXT,
    securities_value         TEXT,
    cash                     TEXT NOT NULL,
    cost_basis               TEXT NOT NULL,
    invested_capital         TEXT NOT NULL,
    realised_gain            TEXT NOT NULL,
    unrealised_gain          TEXT,
    dividends                TEXT NOT NULL,
    distributions            TEXT NOT NULL,
    income                   TEXT NOT NULL,
    fees                     TEXT NOT NULL,
    cumulative_contributions TEXT NOT NULL,
    cumulative_withdrawals   TEXT NOT NULL,
    -- Drawdown on portfolio value, which includes the effect of deposits and
    -- withdrawals: money taken out looks identical to money lost.
    high_water_mark          TEXT NOT NULL,
    drawdown_value           TEXT,
    drawdown_pct             TEXT,
    -- Flow-neutral growth index and its drawdown, which is what "how far are
    -- my investments down" means. Flat between valuation dates.
    return_index             TEXT,
    index_as_at              TEXT,
    return_high_water        TEXT,
    return_drawdown_pct      TEXT,
    valuation_status         TEXT NOT NULL,
    -- Where the valuation came from: VANGUARD when it matches a reported
    -- figure, VANGUARD_SECURITY_PRICE when built from Vanguard's own quoted
    -- holding prices. No other source exists yet -- the field is here so a
    -- future benchmark/market-data source has somewhere unambiguous to name.
    valuation_source          TEXT NOT NULL,
    price_as_at              TEXT,
    source_count             INTEGER NOT NULL DEFAULT 0,
    calculation_method       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS holding_daily (
    date             TEXT NOT NULL,
    security_id      TEXT NOT NULL REFERENCES securities(security_id),
    units            TEXT NOT NULL,
    price            TEXT,
    market_value     TEXT,
    cost_basis       TEXT NOT NULL,
    unrealised_gain  TEXT,
    allocation_pct   TEXT,
    asset_class      TEXT NOT NULL,
    valuation_status TEXT NOT NULL,
    price_as_at      TEXT,
    PRIMARY KEY (date, security_id)
);

CREATE TABLE IF NOT EXISTS income_daily (
    date            TEXT NOT NULL,
    security_id     TEXT,
    kind            TEXT NOT NULL,
    amount          TEXT NOT NULL,
    franking_credit TEXT,
    tax_withheld    TEXT,
    PRIMARY KEY (date, security_id, kind)
);

-- Calendar summaries. `granularity` is MONTH, QUARTER or YEAR.
CREATE TABLE IF NOT EXISTS period_summaries (
    period_id        TEXT PRIMARY KEY,
    granularity      TEXT NOT NULL,
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    -- NULL where the portfolio could not be valued at that boundary.
    opening_value    TEXT,
    closing_value    TEXT,
    contributions    TEXT NOT NULL,
    withdrawals      TEXT NOT NULL,
    net_contributions TEXT NOT NULL,
    income           TEXT NOT NULL,
    fees             TEXT NOT NULL,
    realised_gain    TEXT NOT NULL,
    investment_gain  TEXT,
    twrr             TEXT,
    xirr             TEXT,
    valuation_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performance_periods (
    label            TEXT NOT NULL,
    as_at            TEXT NOT NULL,
    start_date       TEXT,
    end_date         TEXT,
    total_return     TEXT,
    capital_return   TEXT,
    income_return    TEXT,
    twrr             TEXT,
    xirr             TEXT,
    status           TEXT NOT NULL,
    note             TEXT,
    PRIMARY KEY (label, as_at)
);

CREATE TABLE IF NOT EXISTS drawdown_episodes (
    episode_id        TEXT PRIMARY KEY,
    peak_date         TEXT NOT NULL,
    peak_value        TEXT NOT NULL,
    trough_date       TEXT NOT NULL,
    trough_value      TEXT NOT NULL,
    drawdown_value    TEXT NOT NULL,
    drawdown_pct      TEXT NOT NULL,
    recovery_date     TEXT,
    recovery_days     INTEGER,
    valuation_status  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS milestones (
    milestone_id TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    date         TEXT NOT NULL,
    value        TEXT,
    description  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_pd_date       ON portfolio_daily(date);
CREATE INDEX IF NOT EXISTS ix_hd_date       ON holding_daily(date);
CREATE INDEX IF NOT EXISTS ix_hd_security   ON holding_daily(security_id);
CREATE INDEX IF NOT EXISTS ix_hd_class      ON holding_daily(asset_class);
CREATE INDEX IF NOT EXISTS ix_id_date       ON income_daily(date);
CREATE INDEX IF NOT EXISTS ix_ps_gran       ON period_summaries(granularity, period_start);
"""
