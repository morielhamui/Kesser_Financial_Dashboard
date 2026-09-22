#!/usr/bin/env python3
"""Load data/reference/facility_listing.xlsx into dim_operator, dim_facility,
and dim_facility_alias.

See PROJECT_RULES.md section 2/2a for the brand -> operator grouping and
the excluded-manager rules (Stern, COR HC Partners LLC).

Usage:
    python3 db/seed/load_facility_listing.py [--db db/kesser_financials.sqlite3]
"""
import argparse
import pathlib
import sqlite3

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"
DEFAULT_LISTING_PATH = REPO_ROOT / "data" / "reference" / "facility_listing.xlsx"

# brand (Manager column, trimmed) -> operator_name
BRAND_TO_OPERATOR = {
    "Axiom": "Curis",
    "Arcadia": "Curis",
    "Arcadia - ALF": "Curis",
    "Goldwater": "Curis",
    "Extended Care": "Extendicare",
    "Haven": "Extendicare",
    "Lincoln": "Lincoln",
    "Lineage": "Lineage",
    "Evercare": "Evercare",
    "Aliya": "Aliya",
    "Allure": "Allure",
}

# Managers that are tenants/managers with no financials to load. Kept in
# dim_facility for traceability, marked inactive.
EXCLUDED_BRANDS = {"Stern", "COR HC Partners LLC"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--listing", type=pathlib.Path, default=DEFAULT_LISTING_PATH)
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.listing, data_only=True)
    ws = wb["Dim_Facility"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    operator_ids: dict[str, int] = {}
    landlord_ids: dict[str, int] = {}

    def get_landlord_id(landlord_name: str) -> int:
        landlord_name = landlord_name.strip()
        if landlord_name in landlord_ids:
            return landlord_ids[landlord_name]
        cur.execute(
            "INSERT INTO dim_landlord (landlord_name) VALUES (?) "
            "ON CONFLICT(landlord_name) DO UPDATE SET landlord_name = excluded.landlord_name",
            (landlord_name,),
        )
        cur.execute("SELECT landlord_id FROM dim_landlord WHERE landlord_name = ?", (landlord_name,))
        lid = cur.fetchone()[0]
        landlord_ids[landlord_name] = lid
        return lid

    def get_operator_id(operator_name: str, is_active: int) -> int:
        if operator_name in operator_ids:
            return operator_ids[operator_name]
        cur.execute(
            "INSERT INTO dim_operator (operator_name, is_active) VALUES (?, ?) "
            "ON CONFLICT(operator_name) DO UPDATE SET is_active = excluded.is_active",
            (operator_name, is_active),
        )
        cur.execute(
            "SELECT operator_id FROM dim_operator WHERE operator_name = ?",
            (operator_name,),
        )
        op_id = cur.fetchone()[0]
        operator_ids[operator_name] = op_id
        return op_id

    inserted = 0
    skipped_unmapped = []

    for row in rows:
        if row[0] is None:
            continue
        (
            facility_key,
            manager_raw,
            landlord_name,
            previous_name,
            financial_name,
            new_name,
            address,
            city,
            state,
            facility_type,
            zipcode,
            county,
            total_beds,
            skilled_beds,
            intermediate_care,
            sheltered_care,
            facility_id_ext,
            licensee_id,
            medicare_cert_no,
            natural_name,
        ) = row[:20]

        brand = (manager_raw or "").strip()
        if not brand:
            continue

        if brand in EXCLUDED_BRANDS:
            operator_name = brand
            is_active = 0
        elif brand in BRAND_TO_OPERATOR:
            operator_name = BRAND_TO_OPERATOR[brand]
            is_active = 1
        else:
            skipped_unmapped.append((facility_key, brand, financial_name))
            continue

        operator_id = get_operator_id(operator_name, is_active)
        facility_name = (financial_name or new_name or natural_name or "").strip()
        if not facility_name:
            continue

        notes_parts = [f"FacilityKey={facility_key}"]
        if landlord_name:
            notes_parts.append(f"Landlord={landlord_name}")
        if facility_type:
            notes_parts.append(f"Type={facility_type}")
        notes = "; ".join(notes_parts)

        landlord_id = get_landlord_id(landlord_name) if landlord_name and landlord_name.strip() else None
        total_beds_val = int(total_beds) if isinstance(total_beds, (int, float)) else None
        skilled_beds_val = int(skilled_beds) if isinstance(skilled_beds, (int, float)) else None

        cur.execute(
            """
            INSERT INTO dim_facility
                (operator_id, facility_name, brand, facility_group, state, is_active, notes, landlord_id, total_beds, skilled_beds)
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(operator_id, facility_name) DO UPDATE SET
                brand = excluded.brand,
                state = excluded.state,
                is_active = excluded.is_active,
                notes = excluded.notes,
                landlord_id = excluded.landlord_id,
                total_beds = excluded.total_beds,
                skilled_beds = excluded.skilled_beds
            """,
            (operator_id, facility_name, brand, (state or "").strip() or None, is_active, notes, landlord_id, total_beds_val, skilled_beds_val),
        )
        cur.execute(
            "SELECT facility_id FROM dim_facility WHERE operator_id = ? AND facility_name = ?",
            (operator_id, facility_name),
        )
        facility_pk = cur.fetchone()[0]
        inserted += 1

        for alias in {previous_name, new_name, natural_name}:
            alias = (alias or "").strip()
            if alias and alias != facility_name:
                cur.execute(
                    "INSERT OR IGNORE INTO dim_facility_alias (facility_id, alias_name) VALUES (?, ?)",
                    (facility_pk, alias),
                )

    conn.commit()
    conn.close()

    print(f"Loaded {inserted} facilities across {len(operator_ids)} operators.")
    for name, op_id in sorted(operator_ids.items()):
        print(f"  operator_id={op_id}: {name}")
    if skipped_unmapped:
        print("Unmapped brands (not loaded):")
        for facility_key, brand, financial_name in skipped_unmapped:
            print(f"  FacilityKey={facility_key} brand={brand!r} financial_name={financial_name!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
