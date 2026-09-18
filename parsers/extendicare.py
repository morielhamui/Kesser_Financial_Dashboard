"""Extendicare operator parser.

Source format: T12 Budget vs Actual, single-facility files. Each file
covers ONE facility but MANY trailing months (a "Month Ending <date>
Actual/PPD" column pair per month, plus a current-month Budget block we
skip -- monitoring is about actuals). All Actual columns found in a file
are loaded, each validated independently as its own period.

See PROJECT_RULES.md sections 2, 2b, 8 for the rules this implements, in
particular the "narrow subtotal detection" bug: this sheet closes a group
two different ways -- either the exact same label repeated verbatim
("Hospice" header ... children ... "Hospice" again with the rollup value),
or a "Total <label>" line -- and does so at every indentation depth (2/4/
6/8), not just department level. A naive check ("does this label match
any label seen before?") would wrongly swallow a real leaf account that
happens to share text with an unrelated group. The fix here is a genuine
indentation stack: a row only closes a group when its indent equals the
CURRENTLY OPEN group's indent AND its label matches that specific open
group's label (verbatim or "Total "-prefixed) -- never a broader lookup.
"""
from __future__ import annotations

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
    excel_date_to_iso,
    get_or_create_mapping,
    insert_census_fact,
    insert_financial_fact,
    insert_reported_net_income,
    load_workbook_any,
    new_batch_id,
    normalize_payor,
)
from validation.validate import validate_facility_period

OPERATOR_NAME = "Extendicare"

# Top-level (indent-2) section label -> routing key. "Prior Period
# Census" rows (e.g. "Private Days - Prior") are still Grouping="Census"
# in the master mapping, folded to the same canonical payor as their
# non-prior counterpart -- so they route to census too, additively merged
# into the same period by insert_census_fact's own ON CONFLICT handling.
SECTION_ROUTES = {
    "census": "census",
    "prior period census": "census",
    "revenue": "revenue",
    "expenses": "opex",
    "capital expenses": "capital",
}


def _indent(cell_value: str) -> int:
    return len(cell_value) - len(cell_value.lstrip(" "))


def find_location_facility_id(ws, resolver: FacilityResolver) -> int:
    for r in range(1, 10):
        label = ws.cell(row=r, column=1).value
        if isinstance(label, str) and label.strip().lower() == "location:":
            name = ws.cell(row=r, column=2).value
            if isinstance(name, str):
                fid = resolver.resolve(name.strip())
                if fid is not None:
                    return fid
                raise ValueError(f"Could not resolve facility for Location: {name!r}")
    raise ValueError("Could not find 'Location:' row")


def find_period_columns(ws, header_rows=(7, 8, 9), max_col=60) -> dict[int, str]:
    """Returns {column_index: period_date} for every column whose header
    row is exactly "Actual" (case-insensitive) -- skips Budget, PPD, and
    Variance columns, which share the same header block.
    """
    label_row, date_row, actual_row = header_rows
    cols = {}
    for c in range(2, max_col + 1):
        kind = ws.cell(row=actual_row, column=c).value
        if isinstance(kind, str) and kind.strip().lower() == "actual":
            date_val = ws.cell(row=date_row, column=c).value
            if date_val:
                try:
                    cols[c] = excel_date_to_iso(date_val)
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


def _resolve_mapping(conn, master, operator_id, raw_label, fallback_statement_type, fallback_category, period_date, source_file, load_batch_id):
    hit = master.lookup(raw_label)
    if hit is not None:
        mapping_id, statement_type, category, detail, payor, sign = hit
        return mapping_id, sign
    sign = default_sign_multiplier(raw_label)
    # PROJECT_RULES.md section 4: a bare "Consulting" label is Cherry (a
    # software/vendor cost), not a generic consulting expense.
    detail = "Cherry" if raw_label.strip().lower() == "consulting" else raw_label
    mapping_id = get_or_create_mapping(
        conn, operator_id, None, raw_label, fallback_statement_type, fallback_category,
        None, detail, sign, notes="source=heuristic_fallback",
    )
    _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label)
    return mapping_id, sign


def parse_and_load(conn, ws, facility_id, period_cols, operator_id, master, source_file, load_batch_id):
    stack: list[tuple[int, str]] = []
    current_top_section: str | None = None

    def closes(indent, label, top_indent, top_label):
        if indent != top_indent:
            return False
        label_l, top_l = label.lower(), top_label.lower()
        return label_l == top_l or label_l == f"total {top_l}"

    for r in range(10, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if not isinstance(label, str) or not label.strip():
            continue
        indent = _indent(label)
        text = label.strip()
        lower = text.lower()

        # Pop/close any open groups this row's indent returns to or past.
        consumed = False
        while stack and indent <= stack[-1][0]:
            top_indent, top_label = stack[-1]
            if closes(indent, text, top_indent, top_label):
                stack.pop()
                consumed = True
                break
            stack.pop()
        if consumed:
            if not stack:
                current_top_section = None
            continue

        if lower.startswith("total "):
            continue  # an orphaned "Total X" not matching any open group -- a subtotal, skip

        if lower in ("net income (loss)", "net income"):
            for c, period_date in period_cols.items():
                v = ws.cell(row=r, column=c).value
                if isinstance(v, (int, float)):
                    insert_reported_net_income(
                        conn, facility_id, period_date, float(v), source_file, f"row{r}", load_batch_id
                    )
            continue

        # Does this row have a numeric value in at least one period column?
        has_value = any(
            isinstance(ws.cell(row=r, column=c).value, (int, float)) for c in period_cols
        )

        if not stack:
            # Top-level (indent 2) row: either a section we track (Census,
            # Revenue, Expenses, Capital Expenses, "Prior Period Census")
            # or an informational line outside any section (EBITDAR) --
            # the latter is never loaded.
            if not has_value:
                stack.append((indent, text))
                current_top_section = SECTION_ROUTES.get(lower)
                continue
            # A top-level leaf with a value and no open section context
            # (e.g. EBITDAR) is informational only.
            continue

        if not has_value:
            stack.append((indent, text))
            continue

        # Leaf with a value, inside an open section.
        if current_top_section == "census":
            payor = normalize_payor(text, OPERATOR_NAME, is_census=True)
            for c, period_date in period_cols.items():
                v = ws.cell(row=r, column=c).value
                if isinstance(v, (int, float)) and v != 0:
                    insert_census_fact(conn, facility_id, period_date, payor, float(v), source_file, load_batch_id)
            continue

        if current_top_section in ("revenue", "opex", "capital"):
            mapping_id, sign = _resolve_mapping(
                conn, master, operator_id, text, current_top_section, stack[-1][1] if stack else current_top_section,
                None, source_file, load_batch_id,
            )
            for c, period_date in period_cols.items():
                v = ws.cell(row=r, column=c).value
                if isinstance(v, (int, float)) and v != 0:
                    insert_financial_fact(
                        conn, facility_id, period_date, mapping_id, float(v) * sign, source_file, f"row{r}", load_batch_id
                    )
            continue
        # Outside any routed section (e.g. under "Prior Period Census"
        # duplicate closing row, or other informational lines) -- skip.


def load_file(conn: sqlite3.Connection, path: str, operator_id: int, resolver: FacilityResolver, master: MasterMappingLookup) -> dict:
    wb = load_workbook_any(path)
    source_file = os.path.basename(path)
    load_batch_id = new_batch_id()

    ws = wb["T12 & Budget vs Actual"] if "T12 & Budget vs Actual" in wb.sheetnames else wb[wb.sheetnames[0]]
    facility_id = find_location_facility_id(ws, resolver)
    period_cols = find_period_columns(ws)
    if not period_cols:
        raise ValueError("No Actual period columns found")

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

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "extendicare")
    files = sorted(glob.glob(os.path.join(raw_dir, "*")))

    total_pass = total_fail = 0
    for path in files:
        if "MANIFEST" in path:
            continue
        if "Balance_Sheet" in os.path.basename(path):
            print(f"{os.path.basename(path)}: skipped (balance sheet, no P&L/Net Income data)")
            continue
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
