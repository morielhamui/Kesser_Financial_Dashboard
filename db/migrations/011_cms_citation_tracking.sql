-- Citation change tracking, for the "flag anything new or changed on the
-- next monthly CMS upload" workflow (requested 2026-11-10).
--
-- Rekeys fact_cms_citations around a citation's STABLE identity --
-- (facility, survey_date, deficiency_prefix, deficiency_tag_number) is
-- one specific deficiency found on one specific survey -- rather than
-- including scope_severity_code/corrected-status in the uniqueness.
-- Those fields are the ones expected to change between a facility's
-- monthly CMS re-pulls (a citation gets corrected, escalates through
-- IDR, etc.) and the loader now tracks such changes explicitly instead
-- of silently inserting a second row or silently overwriting history.
-- Confirmed safe: no existing rows share (facility_id, survey_date,
-- deficiency_prefix, deficiency_tag_number) under the old data.
ALTER TABLE fact_cms_citations RENAME TO fact_cms_citations_old;

CREATE TABLE fact_cms_citations (
    citation_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id               INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    survey_date               TEXT NOT NULL,
    survey_type               TEXT,
    deficiency_prefix         TEXT,
    deficiency_category       TEXT,
    deficiency_tag_number     TEXT,
    deficiency_description    TEXT,
    scope_severity_code       TEXT,
    deficiency_corrected      TEXT,
    correction_date           TEXT,
    inspection_cycle          INTEGER,
    standard_deficiency       TEXT,
    complaint_deficiency      TEXT,
    infection_control_deficiency TEXT,
    citation_under_idr        TEXT,
    citation_under_iidr       TEXT,
    first_seen_source_file    TEXT,
    first_seen_at             TEXT,
    last_seen_source_file     TEXT,
    last_seen_at              TEXT,
    UNIQUE(facility_id, survey_date, deficiency_prefix, deficiency_tag_number)
);

INSERT INTO fact_cms_citations (
    citation_id, facility_id, survey_date, survey_type, deficiency_prefix,
    deficiency_category, deficiency_tag_number, deficiency_description,
    scope_severity_code, deficiency_corrected, correction_date,
    inspection_cycle, standard_deficiency, complaint_deficiency,
    infection_control_deficiency, citation_under_idr, citation_under_iidr,
    first_seen_source_file, first_seen_at, last_seen_source_file, last_seen_at
)
SELECT
    citation_id, facility_id, survey_date, survey_type, deficiency_prefix,
    deficiency_category, deficiency_tag_number, deficiency_description,
    scope_severity_code, deficiency_corrected, correction_date,
    inspection_cycle, standard_deficiency, complaint_deficiency,
    infection_control_deficiency, citation_under_idr, citation_under_iidr,
    source_file, datetime('now'), source_file, datetime('now')
FROM fact_cms_citations_old;

DROP TABLE fact_cms_citations_old;

CREATE INDEX idx_cms_citations_facility ON fact_cms_citations(facility_id, survey_date);

-- Every new citation and every change to scope/severity, corrected
-- status, correction date, or IDR/IIDR status on an existing one gets
-- one row here (per field changed), so the dashboard can surface a
-- "review this" queue instead of silently updating history.
CREATE TABLE fact_cms_citation_changes (
    change_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id             INTEGER NOT NULL REFERENCES dim_facility(facility_id),
    survey_date             TEXT NOT NULL,
    deficiency_prefix       TEXT,
    deficiency_tag_number   TEXT,
    change_type             TEXT NOT NULL CHECK (change_type IN ('new', 'status_change')),
    field_name              TEXT,          -- NULL for change_type='new'
    old_value               TEXT,
    new_value               TEXT,
    source_file             TEXT NOT NULL,
    detected_at             TEXT NOT NULL DEFAULT (datetime('now')),
    reviewed                INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_cms_citation_changes_unreviewed ON fact_cms_citation_changes(reviewed, detected_at);
