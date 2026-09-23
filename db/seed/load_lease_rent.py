#!/usr/bin/env python3
"""Load the rent Petersen SNF itself pays upstream to CareTrust (the
actual real estate owner) into fact_lease_rent, for the Covenant &
EBIDAR dashboard page's lease covenant test.

This is a COLLECTIVE, landlord-level figure -- the covenant test sums
Covenant Income (EBIDAR) across ALL of Petersen SNF's operator brands
and compares it to this ONE combined rent, not to what Petersen SNF
itself collects from each operator brand ("Rent credit" in the same
sheet, a different, larger figure -- Petersen's own spread/margin is
the difference between the two). See PROJECT_RULES.md section 9a.

Source: data/reference/portfolio_spread_and_mid_month_bank_balances.xlsx,
"Portfolio Spread" sheet -- found structurally by searching for the
sheet's own "Total rent being paid to Caretrust" label rather than a
fixed cell reference, since the value sits one row below the label in
this manually laid-out sheet (not a clean table).

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
LABEL = "Total rent being paid to Caretrust"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--path", type=pathlib.Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.path, data_only=True)
    ws = wb["Portfolio Spread"]

    label_cell = None
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.strip() == LABEL:
                label_cell = cell
                break
        if label_cell:
            break
    if label_cell is None:
        raise SystemExit(f"Could not find '{LABEL}' label -- sheet layout changed?")

    value = ws.cell(row=label_cell.row + 1, column=label_cell.column + 1).value
    if not isinstance(value, (int, float)):
        raise SystemExit(f"Expected a number one row below and one column right of '{LABEL}', found {value!r}")
    monthly_rent = abs(float(value))  # stored as a negative outflow in the sheet

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    landlord_row = conn.execute(
        "SELECT landlord_id FROM dim_landlord WHERE landlord_name = ?", (LANDLORD_NAME,)
    ).fetchone()
    if landlord_row is None:
        raise SystemExit(f"Landlord '{LANDLORD_NAME}' not found in dim_landlord")
    landlord_id = landlord_row[0]

    effective_date = "2026-09-23"  # date this snapshot of the rent roll was captured
    conn.execute(
        """
        INSERT INTO fact_lease_rent (landlord_id, monthly_rent, effective_date, source_file)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(landlord_id, effective_date) DO UPDATE SET
            monthly_rent = excluded.monthly_rent,
            source_file = excluded.source_file
        """,
        (landlord_id, monthly_rent, effective_date, args.path.name),
    )
    conn.commit()
    print(f"Loaded {LANDLORD_NAME} rent-to-CareTrust: ${monthly_rent:,.2f}/mo.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
