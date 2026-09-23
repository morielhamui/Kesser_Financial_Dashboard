#!/usr/bin/env python3
"""Load Petersen SNF's monthly lease rent per manager package into
fact_lease_rent, for the Covenant & EBIDAR dashboard page's rent-coverage
covenant test (kept separate from fact_purchase_price's cap-rate-on-
purchase-price test -- see migration 008).

Source: data/reference/portfolio_spread_and_mid_month_bank_balances.xlsx,
"Portfolio Spread" sheet, "Petersen SNF Facilities" section -- a manually
laid-out block (not a clean table) of manager-name rows each followed by
a "Rent credit" row holding that package's monthly rent. Parsed
structurally (label position, not fixed row numbers, since the
individually-owned-properties section above it uses the same "Rent
credit" label for a different concept -- rent stopping at the section
boundary keeps the two from being conflated) and cross-checked against
the sheet's own "Total rent credit from all Petersen SNF facilities"
cell so a layout change fails loudly instead of silently loading wrong
numbers.

Usage:
    python3 db/seed/load_lease_rent.py [--db db/kesser_financials.sqlite3]
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"
DEFAULT_PATH = REPO_ROOT / "data" / "reference" / "portfolio_spread_and_mid_month_bank_balances.xlsx"
LANDLORD_NAME = "Petersen SNF"

# Sheet's manager labels -> dim_facility.brand (matches fact_purchase_price's
# brand spelling exactly, so the two tables join cleanly on (landlord, brand)).
BRAND_MAP = {
    "arcadia care": "Arcadia",
    "arcadia alf": "Arcadia - ALF",
    "axiom care": "Axiom",
    "evercare": "Evercare",
    "extended care": "Extended Care",
    "goldwater care": "Goldwater",
    "lineage hc": "Lineage",
    "lincoln hc": "Lincoln",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--path", type=pathlib.Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.path, data_only=True)
    ws = wb["Portfolio Spread"]

    section_start = None
    checksum_cell = None
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                text = cell.value.strip()
                if text == "Petersen SNF Facilities":
                    section_start = cell.row
                elif text == "Total rent credit from all Petersen SNF facilities":
                    checksum_cell = (cell.row, cell.column)
    if section_start is None:
        raise SystemExit("Could not find 'Petersen SNF Facilities' section header -- sheet layout changed?")

    rents: dict[str, float] = {}
    current_label = None
    for r in range(section_start + 1, ws.max_row + 1):
        label = ws.cell(row=r, column=2).value
        if isinstance(label, str) and label.strip():
            text = label.strip()
            if text.lower() == "rent credit":
                if current_label is None:
                    continue
                value = ws.cell(row=r, column=3).value
                if isinstance(value, (int, float)):
                    brand = BRAND_MAP.get(current_label.lower())
                    if brand:
                        rents[brand] = float(value)
                current_label = None
            else:
                current_label = text
        # A second labelled section (e.g. a different landlord) would introduce
        # a new "Facilities" header; stop once all 8 known packages are found
        # or the label pattern breaks down, rather than reading past this
        # section into unrelated data.
        if len(rents) == len(BRAND_MAP):
            break

    missing = set(BRAND_MAP.values()) - set(rents)
    if missing:
        raise SystemExit(f"Missing expected Petersen SNF packages: {sorted(missing)} -- sheet layout changed?")

    total = sum(rents.values())
    if checksum_cell:
        expected = ws.cell(row=checksum_cell[0], column=checksum_cell[1] + 1).value
        if expected is not None and abs(total - expected) > 1.0:
            raise SystemExit(f"Checksum mismatch: parsed total {total:,.2f} != sheet's own total {expected:,.2f}")

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    landlord_row = conn.execute(
        "SELECT landlord_id FROM dim_landlord WHERE landlord_name = ?", (LANDLORD_NAME,)
    ).fetchone()
    if landlord_row is None:
        raise SystemExit(f"Landlord '{LANDLORD_NAME}' not found in dim_landlord")
    landlord_id = landlord_row[0]

    effective_date = "2026-09-23"  # date this snapshot of the rent roll was captured
    for brand, monthly_rent in rents.items():
        conn.execute(
            """
            INSERT INTO fact_lease_rent (landlord_id, brand, monthly_rent, effective_date, source_file)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(landlord_id, brand, effective_date) DO UPDATE SET
                monthly_rent = excluded.monthly_rent,
                source_file = excluded.source_file
            """,
            (landlord_id, brand, monthly_rent, effective_date, args.path.name),
        )
    conn.commit()
    print(f"Loaded {len(rents)} Petersen SNF package rents, total ${total:,.2f}/mo (checksum OK).")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
