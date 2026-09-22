-- HFS "Building Id" -- Illinois HFS's own facility identifier, used to
-- match our facilities against the state's published quarterly Medicaid
-- rate lists (fact_hfs_rates). Sourced from data/reference/
-- facility_listing.xlsx's "facility_id_ext" column, which was parsed at
-- load time but never persisted -- see db/seed/load_hfs_rates.py.

ALTER TABLE dim_facility ADD COLUMN hfs_building_id TEXT;
