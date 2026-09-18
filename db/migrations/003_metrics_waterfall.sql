-- Derived metrics table (PROJECT_RULES.md section 7). Computed by
-- metrics/waterfall.py from fact_tenant_financials; one row per
-- facility/period, using the single canonical source_file chosen for
-- that period (see chosen_source_file and pick_canonical_source in
-- metrics/waterfall.py for the de-duplication rule across overlapping
-- trailing-period files).

CREATE TABLE fact_metrics_waterfall (
    facility_id                     INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    period_date                     TEXT NOT NULL,
    source_file                     TEXT NOT NULL,
    operating_revenue               REAL NOT NULL,
    operating_expense                REAL NOT NULL,
    operating_income                REAL NOT NULL,
    general_and_administrative      REAL NOT NULL,
    ebitdarm                        REAL NOT NULL,
    real_estate_tax                 REAL NOT NULL,
    ebidarm                         REAL NOT NULL,
    capital_expenses_ex_ret         REAL NOT NULL,
    earnings_before_management_fees REAL NOT NULL,
    management_fees                 REAL NOT NULL,
    earnings                        REAL NOT NULL,
    other_income_expense            REAL NOT NULL,
    noi                             REAL NOT NULL,
    computed_at                     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (facility_id, period_date)
);
