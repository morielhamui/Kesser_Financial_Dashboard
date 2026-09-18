#!/usr/bin/env python3
"""Initialize (or re-initialize) the Kesser tenant financials SQLite database
from the migration scripts in db/migrations/, applied in filename order.

Usage:
    python3 db/init_db.py [--path db/kesser_financials.sqlite3] [--force]
"""
import argparse
import pathlib
import sqlite3
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--force", action="store_true", help="Delete existing DB file first"
    )
    args = parser.parse_args()

    if args.force and args.path.exists():
        args.path.unlink()

    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migrations:
        print(f"No migrations found in {MIGRATIONS_DIR}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(args.path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        for migration in migrations:
            sql = migration.read_text()
            print(f"Applying {migration.name} ...")
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()

    print(f"Database ready at {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
