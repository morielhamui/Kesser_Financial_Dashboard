-- Purchase price per landlord/manager package, for the Covenant & EBIDAR
-- page. Keyed by (landlord_id, brand) rather than facility_id because
-- these are package-level prices -- e.g. all 7 Arcadia facilities under
-- the Petersen SNF master lease were bought as one package with one
-- price, not priced individually per building. "brand" matches
-- dim_facility.brand (the Manager column), not operator_name, since a
-- single landlord (Petersen SNF) can host multiple different operator
-- brands, each its own separately-priced package.

CREATE TABLE fact_purchase_price (
    purchase_price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id        INTEGER NOT NULL REFERENCES dim_landlord(landlord_id),
    brand               TEXT NOT NULL,
    purchase_price      REAL NOT NULL,
    source_file         TEXT,
    notes               TEXT,
    UNIQUE(landlord_id, brand)
);
