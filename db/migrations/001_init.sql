-- Kesser Tenant Financial Monitoring — initial schema
-- See PROJECT_RULES.md for the business rules behind these tables.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Dimensions
-- ---------------------------------------------------------------------

CREATE TABLE dim_operator (
    operator_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_name   TEXT NOT NULL UNIQUE,      -- Curis, Extendicare, Lincoln, Lineage, Evercare, Aliya
    is_active       INTEGER NOT NULL DEFAULT 1,
    notes           TEXT
);

CREATE TABLE dim_facility (
    facility_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id     INTEGER NOT NULL REFERENCES dim_operator(operator_id),
    facility_name   TEXT NOT NULL,             -- canonical/current name
    brand           TEXT,                      -- e.g. Axiom, Arcadia, Goldwater, Avenues, Villas, Gardens
    facility_group  TEXT,                      -- e.g. "Petersen Group" (Curis consolidated statements)
    state           TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    notes           TEXT,
    UNIQUE(operator_id, facility_name)
);

-- Alternate/prior names for a facility (e.g. Lincoln mid-stream renames).
-- Lookups must check both dim_facility.facility_name and this table,
-- case-insensitively.
CREATE TABLE dim_facility_alias (
    alias_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id     INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    alias_name      TEXT NOT NULL,
    UNIQUE(facility_id, alias_name)
);

-- Master account mapping: raw source account -> canonical taxonomy.
-- One row per (operator, raw account label/code) with the resulting
-- category/sub-group/detail and any sign correction.
CREATE TABLE dim_account_mapping (
    mapping_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id      INTEGER NOT NULL REFERENCES dim_operator(operator_id),
    raw_account_code TEXT,                     -- e.g. "504000" (nullable — some sources have no code)
    raw_account_label TEXT NOT NULL,           -- e.g. "Salaries - Regular"
    statement_type   TEXT NOT NULL,            -- 'revenue' | 'expense' | 'capital' | 'other'
    category         TEXT NOT NULL,            -- department, e.g. "Nursing"; or payor for revenue
    sub_group        TEXT,                     -- e.g. "Management Fees", "Salaries", "Other"
    detail           TEXT,                     -- e.g. "Other", "Licenses and Provider Fee"
    sign_multiplier  INTEGER NOT NULL DEFAULT 1 CHECK (sign_multiplier IN (1, -1)),
    is_addback       INTEGER NOT NULL DEFAULT 0,
    notes            TEXT,
    UNIQUE(operator_id, raw_account_code, raw_account_label)
);

CREATE INDEX idx_account_mapping_lookup
    ON dim_account_mapping(operator_id, raw_account_label);

-- ---------------------------------------------------------------------
-- Facts
-- ---------------------------------------------------------------------

-- One row per facility / period / mapped account line.
CREATE TABLE fact_tenant_financials (
    fact_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    period_date      TEXT NOT NULL,            -- last day of month, ISO 'YYYY-MM-DD'
    mapping_id       INTEGER NOT NULL REFERENCES dim_account_mapping(mapping_id),
    amount           REAL NOT NULL,            -- post sign_multiplier, in dollars
    source_file      TEXT NOT NULL,
    source_row_ref   TEXT,                     -- sheet!cell or row label, for traceability
    load_batch_id    TEXT NOT NULL,
    loaded_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(facility_id, period_date, mapping_id, source_file)
);

CREATE INDEX idx_tenant_financials_period
    ON fact_tenant_financials(facility_id, period_date);

-- Census by payor per facility/period/day-count.
CREATE TABLE fact_census (
    census_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    period_date      TEXT NOT NULL,
    payor            TEXT NOT NULL,            -- canonical payor, post alias consolidation
    resident_days    REAL NOT NULL,
    source_file      TEXT NOT NULL,
    load_batch_id    TEXT NOT NULL,
    loaded_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(facility_id, period_date, payor, source_file)
);

CREATE INDEX idx_census_period
    ON fact_census(facility_id, period_date);

-- Kesser's own rent revenue. Effective-dated, NOT monthly: carry the last
-- known row forward until the next effective_date for that facility.
CREATE TABLE fact_kesser_revenue (
    revenue_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    effective_date   TEXT NOT NULL,            -- date the rent value takes effect
    monthly_rent     REAL NOT NULL,
    notes            TEXT,                     -- e.g. "step-up per lease amendment #3"
    UNIQUE(facility_id, effective_date)
);

CREATE INDEX idx_kesser_revenue_facility
    ON fact_kesser_revenue(facility_id, effective_date);

-- The operator's own reported bottom-line Net Income per facility/period,
-- as printed in the source file. This is the validation target.
CREATE TABLE fact_reported_net_income (
    reported_ni_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    period_date      TEXT NOT NULL,
    reported_net_income REAL NOT NULL,
    source_file      TEXT NOT NULL,
    source_row_ref   TEXT,
    load_batch_id    TEXT NOT NULL,
    UNIQUE(facility_id, period_date, source_file)
);

-- Validation / load failures. Nothing downstream reads data for a
-- (facility_id, period_date, source_file) that has an unresolved row here.
CREATE TABLE exceptions_log (
    exception_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER REFERENCES dim_facility(facility_id),
    period_date      TEXT,
    source_file      TEXT NOT NULL,
    load_batch_id    TEXT NOT NULL,
    exception_type   TEXT NOT NULL,            -- 'net_income_mismatch' | 'unmapped_account' | 'parse_error' | ...
    detail           TEXT NOT NULL,            -- human-readable explanation, incl. computed vs reported values
    resolved         INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at      TEXT
);

CREATE INDEX idx_exceptions_unresolved
    ON exceptions_log(resolved, facility_id, period_date);

-- ---------------------------------------------------------------------
-- External reference data (Medicaid / CMS)
-- ---------------------------------------------------------------------

CREATE TABLE fact_hfs_rates (
    hfs_rate_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER REFERENCES dim_facility(facility_id),
    state            TEXT NOT NULL,
    effective_date   TEXT NOT NULL,
    rate_component   TEXT NOT NULL,            -- e.g. "Direct Care", "Support", "Capital"
    rate_amount      REAL NOT NULL,
    source_file      TEXT,
    UNIQUE(facility_id, effective_date, rate_component)
);

CREATE TABLE fact_qip_payments (
    qip_payment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    period_date      TEXT NOT NULL,
    amount           REAL NOT NULL,
    source_file      TEXT,
    UNIQUE(facility_id, period_date)
);

CREATE TABLE fact_cna_payments (
    cna_payment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    period_date      TEXT NOT NULL,
    amount           REAL NOT NULL,
    source_file      TEXT,
    UNIQUE(facility_id, period_date)
);

CREATE TABLE fact_cms_ratings (
    cms_rating_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id      INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    rating_date      TEXT NOT NULL,
    overall_rating   INTEGER,
    health_inspection_rating INTEGER,
    staffing_rating  INTEGER,
    qm_rating        INTEGER,
    source_file      TEXT,
    UNIQUE(facility_id, rating_date)
);
