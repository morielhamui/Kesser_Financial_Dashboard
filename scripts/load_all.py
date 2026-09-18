#!/usr/bin/env python3
"""Run the full pipeline end-to-end: schema, reference data, all 7
operator parsers, then the metrics/waterfall layer.

Usage:
    python3 scripts/load_all.py [--fresh]

--fresh rebuilds the database from scratch (db/init_db.py --force)
before loading. Without it, re-runs load into the existing database
(safe: every insert is an upsert).
"""
import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import sqlite3

from parsers.common import FacilityResolver, MasterMappingLookup
from db.seed.load_master_mapping import load as load_master_mapping_rows, DEFAULT_MAPPING_PATH
from metrics.waterfall import compute_and_store_all

DB_PATH = os.path.join(REPO_ROOT, "db", "kesser_financials.sqlite3")

OPERATOR_MODULES = ["curis", "extendicare", "lincoln", "lineage", "evercare", "aliya", "allure"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    if args.fresh:
        subprocess.run([sys.executable, os.path.join(REPO_ROOT, "db", "init_db.py"), "--force"], check=True)

    subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "db", "seed", "load_facility_listing.py")], check=True
    )
    subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "db", "seed", "add_extendicare_aliases.py")], check=True
    )

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    stats = load_master_mapping_rows(conn, DEFAULT_MAPPING_PATH)
    conn.close()
    print(f"Master mapping: {stats['loaded']} rows loaded, {stats['sign_adjustments']} sign adjustments.")

    total_pass = total_fail = 0
    for name in OPERATOR_MODULES:
        print(f"\n=== {name} ===")
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "parsers", f"{name}.py")],
            capture_output=True, text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("TOTAL:"):
                parts = line.replace("TOTAL:", "").split(",")
                total_pass += int(parts[0].strip().split()[0])
                total_fail += int(parts[1].strip().split()[0])

    print(f"\n=== GRAND TOTAL: {total_pass} passed, {total_fail} failed across all operators ===")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    n_metrics = compute_and_store_all(conn)
    conn.close()
    print(f"Computed waterfall metrics for {n_metrics} facility-periods.")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
