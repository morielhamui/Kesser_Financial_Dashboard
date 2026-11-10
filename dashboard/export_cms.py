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

# --- citations, full history, grouped by facility ---
citations_by_facility = {}
for row in conn.execute("""
    SELECT facility_id, survey_date, survey_type, deficiency_prefix, deficiency_category,
           deficiency_tag_number, deficiency_description, scope_severity_code,
           deficiency_corrected, correction_date, standard_deficiency,
           complaint_deficiency, infection_control_deficiency
    FROM fact_cms_citations
    WHERE facility_id IN ({})
    ORDER BY facility_id, survey_date DESC
""".format(",".join("?" * len(fac_ids))), list(fac_ids)):
    citations_by_facility.setdefault(row["facility_id"], []).append(dict(row))

for f in facilities:
    f["citations"] = citations_by_facility.get(f["facility_id"], [])

out = {"facilities": facilities}
out_path = pathlib.Path(__file__).resolve().parent / "cms_data.json"
out_path.write_text(json.dumps(out, default=str))
print(f"Wrote {out_path} ({len(facilities)} facilities, "
      f"{sum(len(f['citations']) for f in facilities)} citation rows)")
