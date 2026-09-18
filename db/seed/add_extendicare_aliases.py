#!/usr/bin/env python3
"""Add facility aliases for Extendicare's "Extended Care"-brand facilities.

The facility master's Financial Name for these is a bare city/nickname
("Arcola", "Bement", "Farmer", "Meadowbrook", "Tuscola"), but Extendicare's
own P&L exports header every facility -- regardless of "Extended Care" vs
"Haven" brand in the facility master -- as "The Haven of <X>" (confirmed
directly from the raw source files' "Location:" row). The "Haven"-brand
facilities (Bridgeport, St. Elmo) already match by Financial Name alone;
only these five need an alias added.
"""
import pathlib
import sqlite3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"

ALIASES = {
    "Arcola": "The Haven of Arcola",
    "Bement": "The Haven of Bement",
    "Farmer": "The Haven of Farmer City",
    "Meadowbrook": "The Haven of Meadowbrook",
    "Tuscola": "The Haven of Tuscola",
}


def main():
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    operator_id = conn.execute(
        "SELECT operator_id FROM dim_operator WHERE operator_name = 'Extendicare'"
    ).fetchone()[0]
    added = 0
    for facility_name, alias in ALIASES.items():
        row = conn.execute(
            "SELECT facility_id FROM dim_facility WHERE operator_id = ? AND facility_name = ?",
            (operator_id, facility_name),
        ).fetchone()
        if row is None:
            print(f"WARNING: no facility named {facility_name!r} found for Extendicare")
            continue
        conn.execute(
            "INSERT OR IGNORE INTO dim_facility_alias (facility_id, alias_name) VALUES (?, ?)",
            (row[0], alias),
        )
        added += 1
    conn.commit()
    conn.close()
    print(f"Added/confirmed {added} Extendicare facility aliases.")


if __name__ == "__main__":
    main()
