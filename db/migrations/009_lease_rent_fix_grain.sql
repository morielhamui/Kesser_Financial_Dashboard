-- Fix fact_lease_rent's grain: the lease covenant is a COLLECTIVE measure
-- at the landlord level (Petersen SNF's combined Covenant Income across
-- ALL its operator brands vs. the single rent Petersen SNF pays its own
-- owner, CareTrust) -- not a per-(landlord, brand) figure, and NOT the
-- rent Petersen SNF collects from its operators (migration 008 loaded
-- the wrong rent stream -- "Rent credit", what operators pay Petersen --
-- when the covenant is against "Total rent being paid to Caretrust",
-- what Petersen itself pays upstream). See PROJECT_RULES.md section 9a.

DROP TABLE fact_lease_rent;

CREATE TABLE fact_lease_rent (
    lease_rent_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id     INTEGER NOT NULL REFERENCES dim_landlord(landlord_id),
    monthly_rent    REAL NOT NULL,
    effective_date  TEXT,
    source_file     TEXT,
    notes           TEXT,
    UNIQUE(landlord_id, effective_date)
);
