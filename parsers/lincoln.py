"""Lincoln operator parser.

Source format: multi-facility income statements, one column per facility
plus an "All Locations" total column. See PROJECT_RULES.md sections 2, 2b,
8 for the rules this implements, in particular:

  - Dynamic header detection, not fixed row numbers: some files insert an
    extra "Location group:" metadata row above the real facility header,
    shifting everything down by one row. Handled the same way as Curis's
    header-row search (pick the row with the most resolved facility
    matches in a search window), which is naturally robust to this.
  - Facility renames: "Palm Garden of Mattoon" -> "Mattoon Healthcare &
    Senior Living" and "Rose Garden of Pana" -> "Pana Healthcare & Senior
    Living" both appear across the file set. Already handled by
    FacilityResolver, which checks dim_facility_alias (populated from the
    facility master's Previous/New Name columns) case-insensitively.
  - No separate census file was actually provided for Lincoln (the spec
    calls for one) -- this parser loads the income statement only; census
    is a known gap until one is supplied.
  - The whole P&L is nested one level deeper than Curis/Extendicare: a
    top "Net Income" wrapper section contains "Revenue" and "Expenses" as
    children, with "Total Net Income" as its closing rollup (which is also
    the reported bottom line). No separate "Capital Expenses" section
    exists in the raw layout -- items like Interest/Depreciation/Rent are
    nested inside "Expenses" subgroups, but the master mapping reclassifies
    them to Capital Expenses regardless of where Lincoln nests them.
"""
from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3

from parsers.common import (
    FacilityResolver,
    MasterMappingLookup,
    default_sign_multiplier,
    excel_date_to_iso,
    get_or_create_mapping,
    insert_financial_fact,
    insert_reported_net_income,
    load_workbook_any,
    new_batch_id,
)
from validation.validate import validate_facility_period

OPERATOR_NAME = "Lincoln"


def _indent(cell_value: str) -> int:
    return len(cell_value) - len(cell_value.lstrip(" "))


def _find_row(ws, label_candidates, col=1, max_row=15):
    for r in range(1, min(max_row, ws.max_row) + 1):
        v = ws.cell(row=r, column=col).value
        if isinstance(v, str) and v.strip().lower() in label_candidates:
            return r
    return None


def find_facility_columns(ws, resolver: FacilityResolver, header_search_rows=6) -> dict[int, int]:
    """Same strategy as Curis: pick the header row with the MOST resolved
    matches in a search window (not the first candidate row), since some
    files insert an extra metadata row ("Location group:") that shifts
    the real header down by one.
    """
    start_row = (_find_row(ws, {"as of date:"}) or 4) + 1
    best_cols: dict[int, int] = {}
    for r in range(start_row, min(start_row + header_search_rows, ws.max_row) + 1):
        cols = {}
        for c in range(2, ws.max_column + 1):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and v.strip() and v.strip().lower() != "all locations":
                fid = resolver.resolve(v.strip())
                if fid is not None:
                    cols[c] = fid
        if len(cols) > len(best_cols):
            best_cols = cols
    if len(best_cols) >= 3:
        return best_cols
    raise ValueError("Could not locate facility header row")


def find_period_date(ws) -> str:
    r = _find_row(ws, {"as of date:"})
    if r is None:
        raise ValueError("Could not find 'As of Date:' row")
    return excel_date_to_iso(ws.cell(row=r, column=2).value)


def _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label):
    conn.execute(
        """
        INSERT INTO exceptions_log (facility_id, period_date, source_file, load_batch_id, exception_type, detail)
        VALUES (NULL, ?, ?, ?, 'unmapped_account', ?)
        """,
        (period_date, source_file, load_batch_id, f"Not in master mapping, used heuristic fallback: {raw_label!r}"),
    )


def _resolve_mapping(conn, master, operator_id, raw_label, fallback_statement_type, fallback_category, period_date, source_file, load_batch_id):
    hit = master.lookup(raw_label)
    if hit is not None:
        mapping_id, statement_type, category, detail, payor, sign = hit
        return mapping_id, sign
    sign = default_sign_multiplier(raw_label)
    detail = "Cherry" if raw_label.strip().lower() == "consulting" else raw_label
    mapping_id = get_or_create_mapping(
        conn, operator_id, None, raw_label, fallback_statement_type, fallback_category,
        None, detail, sign, notes="source=heuristic_fallback",
    )
    _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label)
    return mapping_id, sign


def parse_and_load(conn, ws, facility_cols, operator_id, master, period_date, source_file, load_batch_id):
    stack: list[tuple[int, str]] = []

    def closes(indent, label, top_indent, top_label):
        if indent != top_indent:
            return False
        return label.lower() == top_label.lower() or label.lower() == f"total {top_label.lower()}"

    for r in range(10, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if not isinstance(label, str) or not label.strip():
            continue
        indent = _indent(label)
        text = label.strip()
        lower = text.lower()

        consumed = False
        while stack and indent <= stack[-1][0]:
            top_indent, top_label = stack[-1]
            if closes(indent, text, top_indent, top_label):
                stack.pop()
                consumed = True
                if lower == "total net income":
                    for c, fid in facility_cols.items():
                        v = ws.cell(row=r, column=c).value
                        if isinstance(v, (int, float)):
                            insert_reported_net_income(
                                conn, fid, period_date, float(v), source_file, f"row{r}", load_batch_id
                            )
                break
            stack.pop()
        if consumed:
            continue

        if lower.startswith("total "):
            continue  # orphaned subtotal not matching any open group

        has_value = any(
            isinstance(ws.cell(row=r, column=c).value, (int, float)) for c in facility_cols
        )

        if not has_value:
            stack.append((indent, text))
            continue

        # Leaf with a value. "Revenue"/"Expenses" always sit at depth 1 in
        # the stack (directly under the "Net Income" wrapper at depth 0),
        # however many more levels this leaf is nested under (e.g.
        # "General Expenses" > "Bed Tax" > "Bed Tax" is 3 deep) -- so the
        # section is read fresh from stack[1] rather than tracked as
        # separate mutable state that a multi-level pop could desync.
        current_section = stack[1][1].lower() if len(stack) >= 2 else None
        if current_section in ("revenue", "expenses"):
            fallback_statement_type = "revenue" if current_section == "revenue" else "opex"
            fallback_category = stack[-1][1] if stack else current_section
            mapping_id, sign = _resolve_mapping(
                conn, master, operator_id, text, fallback_statement_type, fallback_category,
                period_date, source_file, load_batch_id,
            )
            for c, fid in facility_cols.items():
                v = ws.cell(row=r, column=c).value
                if isinstance(v, (int, float)) and v != 0:
                    insert_financial_fact(
                        conn, fid, period_date, mapping_id, float(v) * sign, source_file, f"row{r}", load_batch_id
                    )
        # Leaves outside Revenue/Expenses (shouldn't normally occur) are skipped.


def load_file(conn: sqlite3.Connection, path: str, operator_id: int, resolver: FacilityResolver, master: MasterMappingLookup) -> dict:
    wb = load_workbook_any(path)
    source_file = os.path.basename(path)
    load_batch_id = new_batch_id()

    ws = wb[wb.sheetnames[0]]
    period_date = find_period_date(ws)
    facility_cols = find_facility_columns(ws, resolver)

    parse_and_load(conn, ws, facility_cols, operator_id, master, period_date, source_file, load_batch_id)
    conn.commit()

    results = []
    for fid in set(facility_cols.values()):
        passed, recomputed, reported = validate_facility_period(conn, fid, period_date, source_file, load_batch_id)
        results.append((fid, passed, recomputed, reported))
    conn.commit()
    return {"source_file": source_file, "period_date": period_date, "n_facilities": len(facility_cols), "results": results}


def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "kesser_financials.sqlite3")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    operator_id = conn.execute("SELECT operator_id FROM dim_operator WHERE operator_name = ?", (OPERATOR_NAME,)).fetchone()[0]
    resolver = FacilityResolver(conn, operator_id)
    master = MasterMappingLookup(conn, operator_id)

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "lincoln")
    files = sorted(glob.glob(os.path.join(raw_dir, "*.xlsx")))

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
        print(f"{summary['source_file']} [{summary['period_date']}]: {n_pass}/{summary['n_facilities']} facilities validated ({status})")
        if n_fail:
            for fid, passed, recomputed, reported in summary["results"]:
                if not passed:
                    print(f"    facility_id={fid} recomputed={recomputed:.2f} reported={reported:.2f} diff={recomputed - reported:.2f}")

    n_unmapped = conn.execute(
        "SELECT COUNT(DISTINCT detail) FROM exceptions_log WHERE exception_type = 'unmapped_account'"
    ).fetchone()[0]
    print(f"\nTOTAL: {total_pass} passed, {total_fail} failed across {len(files)} files")
    print(f"Distinct unmapped raw account labels (heuristic fallback used): {n_unmapped}")
    conn.close()


if __name__ == "__main__":
    main()
