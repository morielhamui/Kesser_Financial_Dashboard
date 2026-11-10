#!/usr/bin/env python3
"""Load CMS Care Compare data (NH_ProviderInfo + NH_HealthCitations) into
fact_cms_provider_info and fact_cms_citations (migration 010).

CCN crosswalk: dim_facility.ccn is built once here from a hardcoded
facility_id -> CCN map (CCN_MAP below), resolved by matching
NH_ProviderInfo's "Provider Name"/"City/Town" against each Petersen SNF
facility's brand+town naming (e.g. "Arcadia Aledo" -> "ARCADIA CARE
ALEDO", "Axiom Gardens Flora" -> "Axiom Gardens of Flora"), confirmed
where ambiguous by exact certified-bed-count match against the partner's
August 2026 portfolio scorecard (e.g. the Lineage HC facilities are
CMS-listed under "... Living & Rehab Center", not their brand name).
ALF and independent-living units (Gardens Kewanee, Villas Bushnell,
Villas Herscher, Villas at Galva, Villas Kewanee, Villas at Havana) are
correctly left with no CCN -- they aren't Medicare/Medicaid SNF-certified.

Ironwood is confirmed ALF (not Medicare/Medicaid SNF-certified, per the
user) -- correctly has no CCN. The Haven of Meadowbrook is CMS-listed
under a different name entirely ("Haven of Champaign", CCN 146017,
Champaign IL) -- "Meadowbrook" isn't a CMS city/provider name at all,
confirmed by the user.

Usage:
    python3 db/seed/load_cms_data.py --provider-info <path to NH_ProviderInfo*.csv>
    python3 db/seed/load_cms_data.py --citations <path to NH_HealthCitations*.xlsx or .csv>
    (either or both; run with --db to point at a non-default database)
"""
from __future__ import annotations

import argparse
import csv
import datetime
import pathlib
import sqlite3

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"

# facility_id (dim_facility, Petersen SNF landlord) -> CCN
CCN_MAP: dict[int, str] = {
    7: "145886",   # Arcadia Aledo
    8: "145774",   # Arcadia Havana
    9: "145968",   # Arcadia Kewanee
    10: "145442",  # Arcadia Toulon
    11: "145389",  # Arcadia Watseka
    12: "14E361",  # Avenues at Quad Cities (CMS: "Avenues at Quad Cities", Silvis)
    13: "145418",  # Avenues at Royal Oaks (CMS: "Avenues at Royal Oak", Kewanee)
    20: "145692",  # Axiom Flora (CMS: "Axiom Healthcare of Flora")
    21: "145624",  # Axiom Gardens Flora (CMS: "Axiom Gardens of Flora")
    22: "146201",  # Axiom Gardens Mount Vernon
    23: "145978",  # Axiom Harrisburg
    24: "145517",  # Axiom Mount Vernon
    25: "145759",  # Axiom Rosiclare
    26: "145664",  # Axiom West Frankfort
    29: "145438",  # Evercare of Collinsville
    33: "146040",  # Evercare of Jerseyville
    34: "145897",  # Evercare of Lebanon
    35: "145981",  # Evercare of Swansea
    36: "146050",  # The Haven of Arcola
    37: "145948",  # The Haven of Bement
    38: "146104",  # The Haven of Farmer City
    39: "146017",  # The Haven of Meadowbrook (CMS: "Haven of Champaign")
    40: "146086",  # The Haven of Tuscola
    41: "145239",  # Goldwater Peoria Heights
    42: "146020",  # Goldwater Roseville
    45: "146039",  # Eastview Healthcare & Senior Living
    46: "145514",  # Effingham Healthcare & Senior Living
    47: "145584",  # Mattoon Healthcare & Senior Living (CMS: "Palm Garden of Mattoon")
    49: "145411",  # Pana Healthcare & Senior Living (CMS: "Rose Garden of Pana")
    50: "145836",  # Shelbyville Healthcare & Senior Living
    51: "145370",  # Sullivan Healthcare & Senior Living
    52: "145903",  # Vandalia Healthcare & Senior Living
    55: "14E306",  # North Aurora (CMS: "North Aurora Living & Rehab Ctr")
    56: "146133",  # Sandwich (CMS: "Sandwich Living & Rehab Center")
    57: "145825",  # South Elgin (CMS: "South Elgin Living & Rehab Center")
    # 53 (Ironwood): confirmed ALF, not CMS-certified -- no CCN, not a gap.
}

PROVIDER_INFO_COLUMNS = [
    ("Ownership Type", "ownership_type", str),
    ("Number of Certified Beds", "number_of_certified_beds", int),
    ("Average Number of Residents per Day", "avg_residents_per_day", float),
    ("Chain Name", "chain_name", str),
    ("Number of Facilities in Chain", "number_of_facilities_in_chain", int),
    ("Special Focus Status", "special_focus_status", str),
    ("Abuse Icon", "abuse_icon", str),
    ("High Performing Icon", "high_performing_icon", str),
    ("Overall Rating", "overall_rating", int),
    ("Health Inspection Rating", "health_inspection_rating", int),
    ("Staffing Rating", "staffing_rating", int),
    ("QM Rating", "qm_rating", int),
    ("Long-Stay QM Rating", "long_stay_qm_rating", int),
    ("Short-Stay QM Rating", "short_stay_qm_rating", int),
    ("Reported Nurse Aide Staffing Hours per Resident per Day", "reported_nurse_aide_hprd", float),
    ("Reported LPN Staffing Hours per Resident per Day", "reported_lpn_hprd", float),
    ("Reported RN Staffing Hours per Resident per Day", "reported_rn_hprd", float),
    ("Reported Total Nurse Staffing Hours per Resident per Day", "reported_total_nurse_hprd", float),
    ("Case-Mix Total Nurse Staffing Hours per Resident per Day", "case_mix_total_nurse_hprd", float),
    ("Total nursing staff turnover", "total_nursing_staff_turnover", float),
    ("Registered Nurse turnover", "rn_turnover", float),
    ("Number of administrators who have left the nursing home", "administrator_turnover", int),
    ("Number of Citations from Infection Control Inspections", "number_of_citations_infection_control", int),
    ("Number of Fines", "number_of_fines", int),
    ("Total Amount of Fines in Dollars", "total_fines_dollars", float),
    ("Number of Payment Denials", "number_of_payment_denials", int),
    ("Total Number of Penalties", "total_number_of_penalties", int),
]

CITATION_COLUMNS = [
    ("Survey Type", "survey_type"),
    ("Deficiency Prefix", "deficiency_prefix"),
    ("Deficiency Category", "deficiency_category"),
    ("Deficiency Tag Number", "deficiency_tag_number"),
    ("Deficiency Description", "deficiency_description"),
    ("Scope Severity Code", "scope_severity_code"),
    ("Deficiency Corrected", "deficiency_corrected"),
    ("Inspection Cycle", "inspection_cycle"),
    ("Standard Deficiency", "standard_deficiency"),
    ("Complaint Deficiency", "complaint_deficiency"),
    ("Infection Control Inspection Deficiency", "infection_control_deficiency"),
    ("Citation under IDR", "citation_under_idr"),
    ("Citation under IIDR", "citation_under_iidr"),
]


def _coerce(value, typ):
    if value in (None, ""):
        return None
    try:
        return typ(value)
    except (ValueError, TypeError):
        return None


def _excel_serial_to_iso(value) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    try:
        serial = int(value)
    except (ValueError, TypeError):
        return None
    # Excel epoch (1899-12-30) matches openpyxl/Excel's leap-year quirk.
    return (datetime.date(1899, 12, 30) + datetime.timedelta(days=serial)).isoformat()


def ensure_ccns(conn: sqlite3.Connection) -> dict[str, int]:
    """Writes CCN_MAP onto dim_facility, returns {ccn: facility_id}."""
    for facility_id, ccn in CCN_MAP.items():
        conn.execute(
            "UPDATE dim_facility SET ccn = ? WHERE facility_id = ?", (ccn, facility_id)
        )
    conn.commit()
    rows = conn.execute(
        "SELECT ccn, facility_id FROM dim_facility WHERE ccn IS NOT NULL"
    ).fetchall()
    return {ccn: facility_id for ccn, facility_id in rows}


def load_provider_info(conn: sqlite3.Connection, path: pathlib.Path) -> None:
    ccn_to_facility = ensure_ccns(conn)
    matched = 0
    skipped_ccns: set[str] = set()
    with path.open(encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ccn = row["CMS Certification Number (CCN)"]
            facility_id = ccn_to_facility.get(ccn)
            if facility_id is None:
                continue
            processing_date = row.get("Processing Date")
            processing_date_iso = _excel_serial_to_iso(processing_date) or processing_date
            values = {
                field: _coerce(row.get(src_col), typ)
                for src_col, field, typ in PROVIDER_INFO_COLUMNS
            }
            columns = ["facility_id", "processing_date", "source_file"] + list(values.keys())
            placeholders = ", ".join("?" for _ in columns)
            conn.execute(
                f"""
                INSERT INTO fact_cms_provider_info ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(facility_id, processing_date) DO UPDATE SET
                    {", ".join(f"{c} = excluded.{c}" for c in columns if c not in ("facility_id", "processing_date"))}
                """,
                [facility_id, processing_date_iso, path.name] + list(values.values()),
            )
            matched += 1
    conn.commit()
    print(f"fact_cms_provider_info: {matched} rows loaded from {path.name}")
    print(f"  {len(ccn_to_facility)} facilities have a CCN on file")


def load_citations(conn: sqlite3.Connection, path: pathlib.Path) -> None:
    ccn_to_facility = ensure_ccns(conn)
    matched = 0
    unmatched_ccns: set[str] = set()

    if path.suffix.lower() == ".xlsx":
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows_iter = ws.iter_rows(values_only=True)
        header = [str(h).strip() if h is not None else "" for h in next(rows_iter)]
        rows = (dict(zip(header, r)) for r in rows_iter)
    else:
        fh = path.open(encoding="utf-8-sig")
        rows = csv.DictReader(fh)

    for row in rows:
        ccn = str(row.get("CMS Certification Number (CCN)") or "").strip()
        facility_id = ccn_to_facility.get(ccn)
        if facility_id is None:
            if ccn:
                unmatched_ccns.add(ccn)
            continue
        survey_date = _excel_serial_to_iso(row.get("Survey Date"))
        correction_date = _excel_serial_to_iso(row.get("Correction Date"))
        if survey_date is None:
            continue
        values = {field: row.get(src_col) for src_col, field in CITATION_COLUMNS}
        values["correction_date"] = correction_date
        columns = ["facility_id", "survey_date", "source_file"] + list(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        conn.execute(
            f"""
            INSERT OR IGNORE INTO fact_cms_citations ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            [facility_id, survey_date, path.name] + list(values.values()),
        )
        matched += 1
    conn.commit()
    print(f"fact_cms_citations: {matched} rows loaded from {path.name}")
    if unmatched_ccns:
        print(f"  {len(unmatched_ccns)} distinct CCNs in file have no matching facility_id (expected -- file covers other facilities too)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--provider-info", type=pathlib.Path)
    parser.add_argument("--citations", type=pathlib.Path)
    args = parser.parse_args()

    if not args.provider_info and not args.citations:
        parser.error("pass --provider-info and/or --citations")

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        if args.provider_info:
            load_provider_info(conn, args.provider_info)
        if args.citations:
            load_citations(conn, args.citations)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
