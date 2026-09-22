#!/usr/bin/env python3
"""Load Lincoln and Lineage's historical census backfill files into
fact_census -- filling PROJECT_RULES.md section 10a's known gap ("Lincoln:
no census file ever provided"; Lineage: partial).

These are interim, manually-consolidated files (a flat Facility/Payor/
Date/Days table per operator, one row per historical month), NOT the
operator's native raw monthly format -- there is no recurring parser here
yet. The user has said proper raw files will follow later so a real
parser can be built for ongoing monthly loads; until then, re-running
this script is how new manually-consolidated exports get loaded.

Because these are standalone census-only files with no corresponding P&L
workbook (unlike every other operator, where the census tab lives in the
same file as the financials), the usual canonical-source-file dedup rule
doesn't apply to them -- there's no overlapping T12 export to collide
with. dashboard/export_ppd.py and dashboard/export_census.py both special-
case this: a fact_census row is included if its source_file has no
matching rows in fact_reported_net_income at all (a standalone census
file), in addition to the usual canonical-source match.

Usage:
    python3 db/seed/load_lincoln_lineage_census.py [--db db/kesser_financials.sqlite3]
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sqlite3

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"
LINCOLN_PATH = REPO_ROOT / "data" / "raw" / "lincoln" / "Lincoln_final_census.xlsx"
LINEAGE_PATH = REPO_ROOT / "data" / "raw" / "lineage" / "Lineage_final_census.xlsx"

# Lineage's file names facilities as "<Name> Living and rehab" /
# "<Name> Living and Rehab Center LLC", which doesn't match any existing
# dim_facility_alias. Mapped explicitly (not by stripping a suffix and
# fuzzy-matching) because Lineage has TWO Sandwich-area facilities --
# "Sandwich" itself and "Ironwood" (aliased as "Ironwood Estates of
# Sandwich") -- and a generic town-name match would risk conflating them.
LINEAGE_FACILITY_ALIASES = {
    "Irving Park Living and Rehab Center LLC": "Irving Park",
    "North Aurora Living and rehab": "North Aurora",
    "Sandwich  Living and rehab": "Sandwich",
    "South Elgin Living and rehab": "South Elgin",
}

# Lineage's payor labels are already close to canonical; only a couple
# need renaming. "Residential" (assisted/independent-living-style beds
# distinct from skilled days) doesn't fold into any existing payor, so it
# stays its own bucket rather than being force-fit into one.
LINEAGE_PAYOR_MAP = {
    "il medicaid": "Medicaid",
    "private pay": "Private",
    "hmo/private insurance": "Insurance/Commercial",
    "medicare": "Medicare",
    "hospice": "Hospice",
    "veterans": "Veterans",
    "residential": "Residential",
}


def _last_day_of_month(dt: datetime.datetime) -> str:
    if dt.month == 12:
        next_month = datetime.date(dt.year + 1, 1, 1)
    else:
        next_month = datetime.date(dt.year, dt.month + 1, 1)
    return (next_month - datetime.timedelta(days=1)).isoformat()


def _insert_census(conn, facility_id, period_date, payor, days, source_file, load_batch_id):
    conn.execute(
        """
        INSERT INTO fact_census (facility_id, period_date, payor, resident_days, source_file, load_batch_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(facility_id, period_date, payor, source_file) DO UPDATE SET
            resident_days = fact_census.resident_days + excluded.resident_days,
            load_batch_id = excluded.load_batch_id,
            loaded_at = datetime('now')
        """,
        (facility_id, period_date, payor, days, source_file, load_batch_id),
    )


def build_lincoln_payor_map(wb) -> dict[str, str]:
    """Reads the Table2_1 sheet (a raw-label -> canonical-payor crosswalk
    embedded in the workbook itself) rather than hardcoding Lincoln's ~50
    messy MCO plan-name variants here."""
    ws = wb["Table2_1"]
    mapping = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        canonical, raw = row[0], row[1]
        if not raw:
            continue
        canonical = (canonical or "").strip()
        if canonical == "Managed":  # one truncated cell in the source table
            canonical = "Managed Medicare"
        mapping[raw.strip().lower()] = canonical
    return mapping


def resolve_facility(conn, operator_id, name_by_alias=None):
    by_name = {}
    for facility_id, facility_name in conn.execute(
        "SELECT facility_id, facility_name FROM dim_facility WHERE operator_id = ?", (operator_id,)
    ):
        by_name[facility_name.strip().lower()] = facility_id
    for facility_id, alias in conn.execute(
        """
        SELECT a.facility_id, a.alias_name FROM dim_facility_alias a
        JOIN dim_facility f ON f.facility_id = a.facility_id WHERE f.operator_id = ?
        """,
        (operator_id,),
    ):
        by_name.setdefault(alias.strip().lower(), facility_id)

    def resolve(raw_name: str) -> int | None:
        key = raw_name.strip().lower()
        if name_by_alias and raw_name in name_by_alias:
            key = name_by_alias[raw_name].strip().lower()
        return by_name.get(key)

    return resolve


def load_lincoln(conn, load_batch_id) -> int:
    operator_id = conn.execute("SELECT operator_id FROM dim_operator WHERE operator_name = 'Lincoln'").fetchone()[0]
    resolve = resolve_facility(conn, operator_id)
    wb = openpyxl.load_workbook(LINCOLN_PATH, data_only=True)
    payor_map = build_lincoln_payor_map(wb)
    ws = wb["Lincoln"]

    source_file = LINCOLN_PATH.name
    inserted = 0
    unresolved_facilities = set()
    unmapped_payors = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        _manager, date, facility_name, payor, days = row[:5]
        if not isinstance(days, (int, float)) or days == 0:
            continue
        facility_id = resolve(facility_name)
        if facility_id is None:
            unresolved_facilities.add(facility_name)
            continue
        canonical_payor = payor_map.get(payor.strip().lower())
        if canonical_payor is None:
            unmapped_payors.add(payor)
            continue
        period_date = _last_day_of_month(date)
        _insert_census(conn, facility_id, period_date, canonical_payor, float(days), source_file, load_batch_id)
        inserted += 1

    if unresolved_facilities:
        print("  Lincoln: unresolved facility names:", sorted(unresolved_facilities))
    if unmapped_payors:
        print("  Lincoln: unmapped payor labels:", sorted(unmapped_payors))
    return inserted


def load_lineage(conn, load_batch_id) -> int:
    operator_id = conn.execute("SELECT operator_id FROM dim_operator WHERE operator_name = 'Lineage'").fetchone()[0]
    resolve = resolve_facility(conn, operator_id, name_by_alias=LINEAGE_FACILITY_ALIASES)
    wb = openpyxl.load_workbook(LINEAGE_PATH, data_only=True)
    ws = wb["Lineage"]

    source_file = LINEAGE_PATH.name
    inserted = 0
    unresolved_facilities = set()
    unmapped_payors = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        facility_name, payor, days, date = row[:4]
        if not isinstance(days, (int, float)) or days == 0:
            continue
        facility_id = resolve(facility_name)
        if facility_id is None:
            unresolved_facilities.add(facility_name)
            continue
        canonical_payor = LINEAGE_PAYOR_MAP.get(payor.strip().lower())
        if canonical_payor is None:
            unmapped_payors.add(payor)
            continue
        period_date = _last_day_of_month(date)
        _insert_census(conn, facility_id, period_date, canonical_payor, float(days), source_file, load_batch_id)
        inserted += 1

    if unresolved_facilities:
        print("  Lineage: unresolved facility names:", sorted(unresolved_facilities))
    if unmapped_payors:
        print("  Lineage: unmapped payor labels:", sorted(unmapped_payors))
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    load_batch_id = "lincoln_lineage_final_census_backfill"

    n_lincoln = load_lincoln(conn, load_batch_id)
    print(f"Lincoln: {n_lincoln} census rows loaded")
    n_lineage = load_lineage(conn, load_batch_id)
    print(f"Lineage: {n_lineage} census rows loaded")

    conn.commit()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
