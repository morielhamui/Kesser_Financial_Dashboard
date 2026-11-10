"""Export CMS Care Compare data (ratings, staffing, citations, fines)
for the CMS Quality & Compliance dashboard artifact.

Usage:
    python3 dashboard/export_cms.py

Writes dashboard/cms_data.json, embedded by build_cms.py into the
published artifact -- run that next, then publish the resulting
dashboard/cms.html via the Artifact tool.
"""
import json
import pathlib
import sqlite3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

conn = sqlite3.connect(REPO_ROOT / "db" / "kesser_financials.sqlite3")
conn.row_factory = sqlite3.Row

facilities = []
for row in conn.execute("""
    SELECT f.facility_id, f.facility_name, f.brand, f.ccn, l.landlord_name
    FROM dim_facility f
    LEFT JOIN dim_landlord l ON l.landlord_id = f.landlord_id
    WHERE l.landlord_name = 'Petersen SNF' AND f.is_active = 1
    ORDER BY f.brand, f.facility_name
"""):
    facilities.append({
        "facility_id": row["facility_id"], "name": row["facility_name"],
        "manager": row["brand"], "ccn": row["ccn"],
    })
fac_ids = {f["facility_id"] for f in facilities}

# --- latest provider-info snapshot per facility ---
latest_by_facility = {}
for row in conn.execute("""
    SELECT * FROM fact_cms_provider_info
    WHERE facility_id IN ({})
    ORDER BY facility_id, processing_date
""".format(",".join("?" * len(fac_ids))), list(fac_ids)):
    d = dict(row)
    latest_by_facility[d["facility_id"]] = d  # last write per facility_id wins (sorted asc)

for f in facilities:
    info = latest_by_facility.get(f["facility_id"])
    f["info"] = info

# --- unreviewed changes (new citations + status changes), keyed the
# same way citations are, so each citation row can carry its own flag ---
unreviewed_by_key: dict[tuple, list] = {}
for row in conn.execute("""
    SELECT facility_id, survey_date, deficiency_prefix, deficiency_tag_number,
           change_type, field_name, old_value, new_value, source_file, detected_at
    FROM fact_cms_citation_changes
    WHERE facility_id IN ({}) AND reviewed = 0
    ORDER BY detected_at DESC
""".format(",".join("?" * len(fac_ids))), list(fac_ids)):
    key = (row["facility_id"], row["survey_date"], row["deficiency_prefix"], row["deficiency_tag_number"])
    unreviewed_by_key.setdefault(key, []).append(dict(row))

# --- citations, full history, grouped by facility ---
citations_by_facility = {}
for row in conn.execute("""
    SELECT facility_id, survey_date, survey_type, deficiency_prefix, deficiency_category,
           deficiency_tag_number, deficiency_description, scope_severity_code,
           deficiency_corrected, correction_date, standard_deficiency,
           complaint_deficiency, infection_control_deficiency,
           first_seen_at, last_seen_at
    FROM fact_cms_citations
    WHERE facility_id IN ({})
    ORDER BY facility_id, survey_date DESC
""".format(",".join("?" * len(fac_ids))), list(fac_ids)):
    d = dict(row)
    key = (d["facility_id"], d["survey_date"], d["deficiency_prefix"], d["deficiency_tag_number"])
    d["changes"] = unreviewed_by_key.get(key, [])
    citations_by_facility.setdefault(row["facility_id"], []).append(d)

for f in facilities:
    f["citations"] = citations_by_facility.get(f["facility_id"], [])

# --- distinct option lists for filter dropdowns, drawn from CMS's own
# data rather than hardcoded, so the UI always offers exactly the
# options CMS gives (no invented categories) ---
corrected_options = [r[0] for r in conn.execute(
    "SELECT DISTINCT deficiency_corrected FROM fact_cms_citations WHERE deficiency_corrected IS NOT NULL ORDER BY 1"
)]
scope_severity_options = [r[0] for r in conn.execute(
    "SELECT DISTINCT scope_severity_code FROM fact_cms_citations WHERE scope_severity_code IS NOT NULL ORDER BY 1"
)]

# --- "as of" tagline: the latest processing_date across every loaded
# facility snapshot ---
latest_processing_date = conn.execute(
    "SELECT MAX(processing_date) FROM fact_cms_provider_info"
).fetchone()[0]
total_unreviewed = conn.execute(
    "SELECT COUNT(*) FROM fact_cms_citation_changes WHERE reviewed = 0"
).fetchone()[0]

out = {
    "facilities": facilities,
    "corrected_options": corrected_options,
    "scope_severity_options": scope_severity_options,
    "latest_processing_date": latest_processing_date,
    "total_unreviewed": total_unreviewed,
}
out_path = pathlib.Path(__file__).resolve().parent / "cms_data.json"
out_path.write_text(json.dumps(out, default=str))
print(f"Wrote {out_path} ({len(facilities)} facilities, "
      f"{sum(len(f['citations']) for f in facilities)} citation rows, "
      f"{total_unreviewed} unreviewed changes)")
