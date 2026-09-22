#!/usr/bin/env python3
"""Load Illinois HFS quarterly Medicaid rate lists into fact_hfs_rates.

Two things happen here:

1. Build the facility crosswalk. data/reference/facility_listing.xlsx
   already carries each facility's HFS "Building Id" in its
   `facility_id_ext` column (parsed but never persisted by
   load_facility_listing.py) -- this is exactly HFS's own "Building Id",
   so it matches directly against every rate file's "Building Id" column
   with no fuzzy name matching needed. Stored on
   dim_facility.hfs_building_id (see migration 005) for reuse.

   One known correction: our reference file has Allure of Peru as
   6004304, but HFS's own files consistently list it as 6004303
   ("ALLURE OF PERU", Peru IL) -- 6004304 does not appear in any HFS file.
   Treated as a typo in our source data, corrected here.

2. Parse each quarterly rate file's *_SNF sheet (header at row 4, data
   from row 5) and load one fact_hfs_rates row per facility per
   rate_component (Capital, Support, Nursing, Total) per quarter. The
   effective_date is parsed from the sheet's title line ("... as of
   MM-DD-YY"), not the per-row "Capital Rate Change Eff Date" column
   (that one only tracks capital-component-specific changes).

Facilities the rate list doesn't cover (assisted living/ALF brands, which
aren't Medicaid SNF rate recipients, and facilities with no recorded
Building Id) are simply not matched -- expected, not an error.

Usage:
    python3 db/seed/load_hfs_rates.py [--db db/kesser_financials.sqlite3]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sqlite3

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"
LISTING_PATH = REPO_ROOT / "data" / "reference" / "facility_listing.xlsx"
RATES_DIR = REPO_ROOT / "data" / "reference" / "hfs_rates"

# Corrections to facility_listing.xlsx's facility_id_ext where it disagrees
# with HFS's own files (keyed by our facility_key from Dim_Facility).
BUILDING_ID_CORRECTIONS = {
    1005: "6004303",  # Allure of Peru: listing has 6004304, HFS has 6004303
}

RATE_COMPONENTS = [
    ("Capital Rate", "Capital"),
    ("Support Rate", "Support"),
    ("Nursing Rate", "Nursing"),
    ("Total Rate", "Total"),
]


def build_crosswalk(conn: sqlite3.Connection) -> dict[str, int]:
    """Returns {hfs_building_id: facility_id}, and writes
    dim_facility.hfs_building_id for every match."""
    wb = openpyxl.load_workbook(LISTING_PATH, data_only=True)
    ws = wb["Dim_Facility"]

    building_id_to_facility_id: dict[str, int] = {}
    matched = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        facility_key = row[0]
        if facility_key is None:
            continue
        financial_name, new_name, natural_name = row[4], row[5], row[19]
        facility_id_ext = row[16]
        name = (financial_name or new_name or natural_name or "").strip()
        if not name:
            continue

        building_id = BUILDING_ID_CORRECTIONS.get(facility_key, facility_id_ext)
        if not building_id:
            continue
        building_id = str(building_id).strip()

        row_db = conn.execute(
            "SELECT facility_id FROM dim_facility WHERE facility_name = ?", (name,)
        ).fetchone()
        if row_db is None:
            continue
        facility_id = row_db[0]
        building_id_to_facility_id[building_id] = facility_id
        conn.execute(
            "UPDATE dim_facility SET hfs_building_id = ? WHERE facility_id = ?",
            (building_id, facility_id),
        )
        matched += 1

    conn.commit()
    print(f"Crosswalk: matched {matched} facilities to an HFS Building Id.")
    return building_id_to_facility_id


def parse_effective_date(title: str) -> str:
    m = re.search(r"as of (\d{2})-(\d{2})-(\d{2})", title)
    if not m:
        raise ValueError(f"Could not parse effective date from title: {title!r}")
    mm, dd, yy = m.groups()
    year = 2000 + int(yy)
    return f"{year:04d}-{mm}-{dd}"


def find_header_row(ws) -> int:
    """Most files have the header at row 4, but at least one (7.1.26) has
    a couple of blank rows first and the header at row 7 instead -- search
    for it rather than assuming a fixed row."""
    for r in range(1, 15):
        if ws.cell(row=r, column=1).value == "Building Id":
            return r
    raise ValueError("Could not find header row (looked for 'Building Id' in column A)")


def load_file(conn: sqlite3.Connection, path: pathlib.Path, crosswalk: dict[str, int]) -> int:
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet_name = next(s for s in wb.sheetnames if s.endswith("_SNF"))
    ws = wb[sheet_name]

    title = ws.cell(row=3, column=1).value or ""
    effective_date = parse_effective_date(title)

    header_row = find_header_row(ws)
    header = [ws.cell(row=header_row, column=c).value for c in range(1, 12)]
    col_idx = {name: i + 1 for i, name in enumerate(header) if name}

    inserted = 0
    for r in range(header_row + 1, ws.max_row + 1):
        building_id = ws.cell(row=r, column=col_idx["Building Id"]).value
        if building_id is None:
            continue
        building_id = str(building_id).strip()
        facility_id = crosswalk.get(building_id)
        if facility_id is None:
            continue

        for col_name, rate_component in RATE_COMPONENTS:
            amount = ws.cell(row=r, column=col_idx[col_name]).value
            if not isinstance(amount, (int, float)):
                continue
            conn.execute(
                """
                INSERT INTO fact_hfs_rates
                    (facility_id, state, effective_date, rate_component, rate_amount, source_file)
                VALUES (?, 'IL', ?, ?, ?, ?)
                ON CONFLICT(facility_id, effective_date, rate_component) DO UPDATE SET
                    rate_amount = excluded.rate_amount,
                    source_file = excluded.source_file
                """,
                (facility_id, effective_date, rate_component, float(amount), path.name),
            )
            inserted += 1
    conn.commit()
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")

    crosswalk = build_crosswalk(conn)

    total = 0
    for path in sorted(RATES_DIR.glob("hfs_RATES_*.xlsx")):
        n = load_file(conn, path, crosswalk)
        print(f"{path.name}: {n} rate rows loaded")
        total += n

    print(f"\nTotal fact_hfs_rates rows loaded/updated: {total}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
