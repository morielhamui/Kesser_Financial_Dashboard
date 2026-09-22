-- Licensed bed counts, needed for occupancy % (census days / available
-- bed-days). Sourced from data/reference/facility_listing.xlsx's
-- total_beds/skilled_beds columns, which -- like facility_id_ext before
-- migration 005 -- were parsed by load_facility_listing.py but never
-- persisted. total_beds is the right occupancy denominator (total
-- licensed capacity); skilled_beds is a subset for facilities licensed
-- as combined SNF/ICF, kept for reference but not used in the occupancy
-- calculation.

ALTER TABLE dim_facility ADD COLUMN total_beds INTEGER;
ALTER TABLE dim_facility ADD COLUMN skilled_beds INTEGER;
