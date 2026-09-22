#!/usr/bin/env python3
"""Load data/reference/purchase_option_listing.xlsx into
fact_purchase_price, for the Covenant & EBIDAR dashboard page.

The file lists one Purchase Price per (Landlord, Manager) package --
e.g. all 7 Arcadia facilities under the Petersen SNF master lease were
bought as one package, not priced individually -- with the Facility
column left blank for package-level rows. Currently covers all 8 of
Petersen SNF's manager packages plus one individually-owned property
(1155 N First St / Evercare); the ~11 other individually-owned
properties have no purchase price yet and are simply not in this file
(not an error -- the dashboard flags them as "no purchase price data").

Usage:
    python3 db/seed/load_purchase_prices.py [--db db/kesser_financials.sqlite3]
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"
DEFAULT_PATH = REPO_ROOT / "data" / "reference" / "purchase_option_listing.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--path", type=pathlib.Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")

    wb = openpyxl.load_workbook(args.path, data_only=True)
    ws = wb["Sheet1"]

    inserted = 0
    unresolved_landlords = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        landlord_name, brand, _facility, purchase_price = row[:4]
        landlord_name = landlord_name.strip()
        brand = (brand or "").strip()
        if not isinstance(purchase_price, (int, float)):
            continue

        landlord_row = conn.execute(
            "SELECT landlord_id FROM dim_landlord WHERE landlord_name = ?", (landlord_name,)
        ).fetchone()
        if landlord_row is None:
            unresolved_landlords.add(landlord_name)
            continue
        landlord_id = landlord_row[0]

        conn.execute(
            """
            INSERT INTO fact_purchase_price (landlord_id, brand, purchase_price, source_file)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(landlord_id, brand) DO UPDATE SET
                purchase_price = excluded.purchase_price,
                source_file = excluded.source_file
            """,
            (landlord_id, brand, float(purchase_price), args.path.name),
        )
        inserted += 1

    conn.commit()
    print(f"Loaded {inserted} landlord/brand purchase price packages.")
    if unresolved_landlords:
        print("Unresolved landlord names (not loaded):", sorted(unresolved_landlords))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
