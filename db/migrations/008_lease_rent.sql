-- Monthly lease rent per landlord/manager package, for the Covenant &
-- EBIDAR page's rent-coverage covenant test -- distinct from
-- fact_purchase_price's cap-rate-on-purchase-price test (two separate
-- measures per the real underwriting model: "Covenant" checks rolling
-- T12 EBIDAR against Annual Rent, with a financial penalty in the lease
-- if it falls short; "Cap Rate Supportable" checks EBIDAR against the
-- purchase option price -- they are never combined into one number).
-- Same (landlord_id, brand) package grain as fact_purchase_price, for
-- the same reason: rent is set per master-lease package, not per
-- facility -- e.g. all 7 Arcadia facilities pay one combined rent to
-- Petersen SNF, not separately metered rents.

CREATE TABLE fact_lease_rent (
    lease_rent_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id     INTEGER NOT NULL REFERENCES dim_landlord(landlord_id),
    brand           TEXT NOT NULL,
    monthly_rent    REAL NOT NULL,
    effective_date  TEXT,
    source_file     TEXT,
    notes           TEXT,
    UNIQUE(landlord_id, brand, effective_date)
);
