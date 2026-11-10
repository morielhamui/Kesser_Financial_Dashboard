-- CMS Care Compare data: star ratings, staffing, citations, fines.
-- See PROJECT_RULES.md section on CMS data (to be added) for sourcing.
--
-- dim_facility.ccn is the join key to CMS's own data (every CMS Care
-- Compare file is keyed by CMS Certification Number). Only SNF/ICF
-- facilities are CMS-certified -- ALF and independent-living units in
-- dim_facility correctly have no ccn.
ALTER TABLE dim_facility ADD COLUMN ccn TEXT;

-- fact_cms_ratings (migration 001) was a 4-column placeholder, never
-- populated anywhere in this codebase (confirmed by repo-wide search
-- before dropping it) -- replaced here by a proper snapshot table
-- matching CMS's own NH_ProviderInfo file, one row per facility per
-- monthly Provider Data Catalog refresh (processing_date).
DROP TABLE IF EXISTS fact_cms_ratings;

CREATE TABLE fact_cms_provider_info (
    provider_info_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id               INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    processing_date           TEXT NOT NULL,   -- CMS's own "Processing Date" for this snapshot
    ownership_type            TEXT,
    number_of_certified_beds  INTEGER,
    avg_residents_per_day     REAL,
    chain_name                TEXT,
    number_of_facilities_in_chain INTEGER,
    special_focus_status      TEXT,            -- 'SFF', 'SFF Candidate', or NULL
    abuse_icon                TEXT,            -- 'Y' / 'N'
    high_performing_icon      TEXT,
    overall_rating            INTEGER,
    health_inspection_rating  INTEGER,
    staffing_rating           INTEGER,
    qm_rating                 INTEGER,
    long_stay_qm_rating       INTEGER,
    short_stay_qm_rating      INTEGER,
    reported_nurse_aide_hprd  REAL,            -- hours per resident per day
    reported_lpn_hprd         REAL,
    reported_rn_hprd          REAL,
    reported_total_nurse_hprd REAL,
    case_mix_total_nurse_hprd REAL,
    total_nursing_staff_turnover REAL,
    rn_turnover               REAL,
    administrator_turnover    INTEGER,         -- count, per CMS's own field
    number_of_citations_infection_control INTEGER,
    number_of_fines           INTEGER,
    total_fines_dollars       REAL,
    number_of_payment_denials INTEGER,
    total_number_of_penalties INTEGER,
    source_file               TEXT,
    UNIQUE(facility_id, processing_date)
);

CREATE INDEX idx_cms_provider_info_facility ON fact_cms_provider_info(facility_id);

-- One row per deficiency citation, from CMS's NH_HealthCitations file.
-- No natural single-column key (a facility/survey can carry several
-- citations on the same tag across re-surveys), so dedup is on the
-- full tuple CMS itself would consider a unique citation.
CREATE TABLE fact_cms_citations (
    citation_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id               INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    survey_date               TEXT NOT NULL,
    survey_type               TEXT,            -- 'Health' | 'Fire Safety' | ...
    deficiency_prefix         TEXT,            -- 'F', 'K', ...
    deficiency_category       TEXT,
    deficiency_tag_number     TEXT,
    deficiency_description    TEXT,
    scope_severity_code       TEXT,
    deficiency_corrected      TEXT,
    correction_date           TEXT,
    inspection_cycle          INTEGER,
    standard_deficiency       TEXT,            -- 'Y' / 'N'
    complaint_deficiency      TEXT,
    infection_control_deficiency TEXT,
    citation_under_idr        TEXT,
    citation_under_iidr       TEXT,
    source_file               TEXT,
    UNIQUE(facility_id, survey_date, deficiency_tag_number, deficiency_prefix, scope_severity_code)
);

CREATE INDEX idx_cms_citations_facility ON fact_cms_citations(facility_id, survey_date);
