-- Landlord dimension. Each facility has a landlord entity distinct from
-- its operator/manager -- confirmed against Portfolio_Spread_and_Mid_Month_
-- Bank_Balances.xlsx, whose "Landlord Name" values match this table's
-- landlord_name exactly (join key verified by hand for all 12
-- individually-owned properties + the pooled "Petersen SNF" portfolio).
-- See PROJECT_RULES.md section on landlord/manager structure.

CREATE TABLE dim_landlord (
    landlord_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_name   TEXT NOT NULL UNIQUE,
    notes           TEXT
);

ALTER TABLE dim_facility ADD COLUMN landlord_id INTEGER REFERENCES dim_landlord(landlord_id);
