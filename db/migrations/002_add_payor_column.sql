-- Add a dedicated payor dimension to dim_account_mapping, matching the
-- master account mapping spreadsheet's (Operator, Raw Account, Grouping,
-- Sub-Group, Detail, Payor, Sign Multiplier, Exclude) shape:
--   statement_type <- Grouping   (revenue | opex | capital)
--   category       <- Sub-Group  (department: Nursing, Ancillary, G&A, ...)
--   detail (renamed usage) <- Detail (Salaries, Supplies, Therapy, ...)
--   payor          <- Payor      (canonical payor, mainly for Ancillary opex
--                                  and Revenue rows split by payor)
-- "sub_group" (the original column) is left in place but unused by the
-- master-mapping-driven loaders; it's superseded by category+detail+payor.

ALTER TABLE dim_account_mapping ADD COLUMN payor TEXT;
