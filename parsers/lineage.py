"""Lineage operator parser.

Source format: QuickBooks Desktop P&L Trending export (.xlsm), one file
per facility, many trailing months as columns. Facility name comes from
the filename itself (no "Location:" row in this export); period name
comes from row 1's date headers.

Unlike the other operators' leading-space indentation, QuickBooks encodes
depth as COLUMN POSITION: the first non-empty cell among columns 1-6 in a
row is both the label and, via its column index, the depth. Otherwise
this is the same shape as Extendicare/Lincoln (a "Total <label>" or exact-
label-repeat closes a group) and reuses the same indentation-stack
approach. Two QuickBooks-standard subtotal lines ("Gross Profit", "Net
Ordinary Income"/"Net Other Income") aren't in the master mapping and
naturally fall outside any two-deep routed section, so no special-casing
is needed for them -- they're skipped as an emergent property of the
stack algorithm, not by keyword.

See PROJECT_RULES.md section 8 for the known "Merged.2" duplicate-column
bug in Lineage's OWN prior mapping spreadsheet -- moot now that mapping
comes from the master account mapping file (dim_account_mapping) instead
of that artifact, but noted here in case a similar duplicate-header
problem ever resurfaces in a raw source file itself.
"""
from __future__ import annotations

import datetime
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3

from parsers.common import (
    FacilityResolver,
    MasterMappingLookup,
    default_sign_multiplier,
    get_or_create_mapping,
    insert_financial_fact,
    insert_reported_net_income,
    load_workbook_any,
    new_batch_id,
)
from validation.validate import validate_facility_period

OPERATOR_NAME = "Lineage"

_FACILITY_FROM_FILENAME_RE = re.compile(r"^(?:[0-9a-f]{8}-)?(.+?)_PL_", re.IGNORECASE)


def facility_name_from_filename(filename: str) -> str:
    m = _FACILITY_FROM_FILENAME_RE.match(filename)
    if not m:
        raise ValueError(f"Could not derive facility name from filename: {filename!r}")
    return m.group(1).replace("_", " ").strip()


def find_label_and_indent(ws, row: int, max_col: int = 6) -> tuple[str, int] | None:
    for c in range(1, max_col + 1):
        v = ws.cell(row=row, column=c).value
        if isinstance(v, str) and v.strip():
            return v.strip(), c
    return None


def find_period_columns(ws, header_row: int = 1, max_col: int = 60) -> dict[int, str]:
    """QuickBooks date headers like "Nov 30, 24" in odd columns starting
    at 7; a final "TOTAL" column is skipped (it's an aggregate, not a
    period).
    """
    cols = {}
    for c in range(2, max_col + 1):
        v = ws.cell(row=header_row, column=c).value
        if isinstance(v, str) and v.strip().upper() == "TOTAL":
            continue
        if isinstance(v, datetime.datetime):
            cols[c] = v.date().isoformat()
        elif isinstance(v, datetime.date):
            cols[c] = v.isoformat()
        elif isinstance(v, str) and v.strip():
            try:
                cols[c] = datetime.datetime.strptime(v.strip(), "%b %d, %y").date().isoformat()
            except ValueError:
                continue
    return cols


def _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label):
    conn.execute(
        """
        INSERT INTO exceptions_log (facility_id, period_date, source_file, load_batch_id, exception_type, detail)
        VALUES (NULL, ?, ?, ?, 'unmapped_account', ?)
        """,
        (period_date, source_file, load_batch_id, f"Not in master mapping, used heuristic fallback: {raw_label!r}"),
    )


# The master mapping's "810150-MCA Sequester Reduction" row is
# Grouping=Revenue with sign_multiplier=1, but the raw value is stored
# POSITIVE inside the Expense section of every Lineage file it appears in
# (verified across South Elgin, Sandwich, Irving Park -- never negative).
# Reclassifying it into Revenue with sign=+1 doesn't move its NI
# contribution, it DOUBLES the swing (was -V in Expense, becomes +V in
# Revenue = +2V vs. the source's own Net Income). Confirmed by hand: every
# one of this parser's validation failures was exactly 2x this account's
# value for that period; sign=-1 reproduces reported Net Income exactly.
# Overridden here rather than in the master mapping file itself.
_SIGN_OVERRIDES = {"810150-mca sequester reduction": -1}


def _resolve_mapping(conn, master, operator_id, raw_label, fallback_statement_type, fallback_category, period_date, source_file, load_batch_id):
    hit = master.lookup(raw_label)
    if hit is not None:
        mapping_id, statement_type, category, detail, payor, sign = hit
        sign = _SIGN_OVERRIDES.get(raw_label.strip().lower(), sign)
        return mapping_id, sign
    sign = default_sign_multiplier(raw_label)
    detail = "Cherry" if raw_label.strip().lower() == "consulting" else raw_label
    mapping_id = get_or_create_mapping(
        conn, operator_id, None, raw_label, fallback_statement_type, fallback_category,
        None, detail, sign, notes="source=heuristic_fallback",
    )
    _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label)
    return mapping_id, sign


def parse_and_load(conn, ws, facility_id, period_cols, operator_id, master, source_file, load_batch_id):
    stack: list[tuple[int, str]] = []

    def closes(indent, label, top_indent, top_label):
        if indent != top_indent:
            return False
        return label.lower() == top_label.lower() or label.lower() == f"total {top_label.lower()}"

    for r in range(2, ws.max_row + 1):
        found = find_label_and_indent(ws, r)
        if found is None:
            continue
        text, indent = found
        lower = text.lower()

        consumed = False
        while stack and indent <= stack[-1][0]:
            top_indent, top_label = stack[-1]
            if closes(indent, text, top_indent, top_label):
                stack.pop()
                consumed = True
                break
            stack.pop()
        if consumed:
            continue

        if lower.startswith("total "):
            continue

        if lower == "net income":
            for c, period_date in period_cols.items():
                v = ws.cell(row=r, column=c).value
                if isinstance(v, (int, float)):
                    insert_reported_net_income(
                        conn, facility_id, period_date, float(v), source_file, f"row{r}", load_batch_id
                    )
            continue

        has_value = any(
            isinstance(ws.cell(row=r, column=c).value, (int, float)) for c in period_cols
        )

        if not has_value:
            stack.append((indent, text))
            continue

        # Leaf. Routing is the immediate child of whichever top-level
        # wrapper is open ("Ordinary Income/Expense" -> Income/Expense;
        # "Other Income/Expense" -> Other Expense), i.e. stack[1] --
        # regardless of how deep this specific leaf is nested beneath
        # that. QuickBooks-standard subtotal lines that aren't real
        # accounts ("Gross Profit", "Net Ordinary Income", "Net Other
        # Income") naturally have no matching 2-deep stack at the point
        # they appear, so they fall through here with section=None and
        # are skipped without needing a keyword special case.
        section = stack[1][1].lower() if len(stack) >= 2 else None
        if section == "income":
            fallback_statement_type = "revenue"
        elif section in ("expense", "other expense"):
            fallback_statement_type = "opex"
        else:
            continue

        fallback_category = stack[-1][1] if stack else section
        mapping_id, sign = _resolve_mapping(
            conn, master, operator_id, text, fallback_statement_type, fallback_category,
            None, source_file, load_batch_id,
        )
        for c, period_date in period_cols.items():
            v = ws.cell(row=r, column=c).value
            if isinstance(v, (int, float)) and v != 0:
                insert_financial_fact(
                    conn, facility_id, period_date, mapping_id, float(v) * sign, source_file, f"row{r}", load_batch_id
                )


def load_file(conn: sqlite3.Connection, path: str, operator_id: int, resolver: FacilityResolver, master: MasterMappingLookup) -> dict:
    wb = load_workbook_any(path)
    source_file = os.path.basename(path)
    load_batch_id = new_batch_id()

    facility_name = facility_name_from_filename(source_file)
    facility_id = resolver.resolve(facility_name)
    if facility_id is None:
        raise ValueError(f"Could not resolve facility for filename-derived name: {facility_name!r}")

    ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb[wb.sheetnames[-1]]
    period_cols = find_period_columns(ws)
    if not period_cols:
        raise ValueError("No period columns found")

    parse_and_load(conn, ws, facility_id, period_cols, operator_id, master, source_file, load_batch_id)
    conn.commit()

    results = []
    for period_date in sorted(set(period_cols.values())):
        has_reported = conn.execute(
            "SELECT 1 FROM fact_reported_net_income WHERE facility_id=? AND period_date=? AND source_file=?",
            (facility_id, period_date, source_file),
        ).fetchone()
        if not has_reported:
            continue
        passed, recomputed, reported = validate_facility_period(conn, facility_id, period_date, source_file, load_batch_id)
        results.append((period_date, passed, recomputed, reported))
    conn.commit()
    return {"source_file": source_file, "facility_id": facility_id, "results": results}


def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "kesser_financials.sqlite3")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    operator_id = conn.execute("SELECT operator_id FROM dim_operator WHERE operator_name = ?", (OPERATOR_NAME,)).fetchone()[0]
    resolver = FacilityResolver(conn, operator_id)
    master = MasterMappingLookup(conn, operator_id)

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "lineage")
    files = sorted(glob.glob(os.path.join(raw_dir, "*.xlsm")))

    total_pass = total_fail = 0
    for path in files:
        try:
            summary = load_file(conn, path, operator_id, resolver, master)
        except Exception as e:
            print(f"FAILED to parse {os.path.basename(path)}: {e}")
            continue
        n_pass = sum(1 for _, passed, _, _ in summary["results"] if passed)
        n_fail = sum(1 for _, passed, _, _ in summary["results"] if not passed)
        total_pass += n_pass
        total_fail += n_fail
        status = "OK" if n_fail == 0 else f"{n_fail} FAILED"
        print(f"{summary['source_file']}: {n_pass}/{len(summary['results'])} periods validated ({status})")
        if n_fail:
            for period_date, passed, recomputed, reported in summary["results"]:
                if not passed:
                    print(f"    {period_date}: recomputed={recomputed:.2f} reported={reported:.2f} diff={recomputed - reported:.2f}")

    n_unmapped = conn.execute(
        "SELECT COUNT(DISTINCT detail) FROM exceptions_log WHERE exception_type = 'unmapped_account'"
    ).fetchone()[0]
    print(f"\nTOTAL: {total_pass} passed, {total_fail} failed across {len(files)} files")
    print(f"Distinct unmapped raw account labels (heuristic fallback used): {n_unmapped}")
    conn.close()


if __name__ == "__main__":
    main()
