"""Aliya operator parser.

Source format: "ALIYA HEALTHCARE CONSULTING LLC" workbook, one file per
facility (Glenwood, Palatine), multiple trailing YTD-through-month
columns on the "P& L Trailing YTD Detailed Cons" sheet.

Not covered by the master account mapping (data/reference/
kesser_master_account_mapping.xlsx covers only Curis, Lineage,
Extendicare, Evercare, Lincoln) -- Aliya was discovered/added after that
file was built, so classification here is heuristic-only: category is
the indent-4 department name, qualified into the raw label to avoid the
same GL-code-collision failure mode found in Curis (e.g. "502000 - REG -
Regular" recurs under Nursing, Dietary, Housekeeping, etc.).

Per PROJECT_RULES.md section 8, this source has up to 5 levels of
indentation (in practice observed up to 6: 2/4/6/8/10/12) and is parsed
with the same indentation-stack approach used for Extendicare/Lincoln/
Lineage/Evercare, NOT keyword matching. One additional wrinkle here: the
source has typos in some of its own closing "Total X" rows (e.g. "Tota
Days Medicaid Traditional", "Total Days Privat") that would fail an
exact "total <label>" string match -- closing detection is loosened to
"starts with a total-flavored prefix" rather than an exact match.

Per PROJECT_RULES.md section 4, "Regional Allocation" costs (seen at an
intermediate group level, e.g. under Nursing Administration) stay in
their originating department but get Detail="Other" -- implemented by
checking the whole open stack, since the "Regional Allocation" label
sits above the actual GL leaf, not on it.

Note on period semantics: unlike the other 5 operators, this sheet's
columns are YTD-CUMULATIVE-through-month ("01/01/2026 Through 01/31/2026",
"01/01/2026 Through 02/28/2026", ...), not standalone monthly actuals --
and the reported Net Income for each column is cumulative on the same
basis, so validation still ties out correctly. fact_tenant_financials
rows loaded here for a given period_date are therefore YTD-through-that-
date figures, not that month alone; a later monthly view would need to
diff consecutive periods. A duplicate final column labeled "Period
Ending" (a true single-month actual, not cumulative) shares the last
column's calendar date but a different basis -- excluded in
find_period_columns, since summing it with the cumulative column for
that date silently blends two different bases and breaks the tie-out.
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
    default_sign_multiplier,
    excel_date_to_iso,
    get_or_create_mapping,
    insert_census_fact,
    insert_financial_fact,
    insert_reported_net_income,
    load_workbook_any,
    new_batch_id,
    normalize_payor,
    salaries_or_other,
    split_code_and_label,
)
from validation.validate import validate_facility_period

OPERATOR_NAME = "Aliya"

DEPARTMENT_TO_CATEGORY = {
    "nursing expenses": "Nursing",
    "activities expenses": "Activities",
    "dietary expenses": "Dietary",
    "housekeeping expenses": "Housekeeping",
    "laundry expenses": "Laundry and Linen",
    "plant and maintenance expenses": "Plant",
    "social service expenses": "Social Service",
    "employee welfare expenses": "Employee Welfare",
    "general and administrative expenses": "General and Administrative",
}

NON_OPERATING_TO_CATEGORY = {
    "rent-building": "Rent",
    "real estate taxes": "RE Tax",
    "interest expense": "Interest",
    "depreciation and amortization": "Depreciation",
    "appraisal fees": "Other",
    "income taxes": "Other",
}


def _indent(cell_value: str) -> int:
    return len(cell_value) - len(cell_value.lstrip(" "))


def _find_row(ws, label_candidates, col=1, max_row=15):
    for r in range(1, min(max_row, ws.max_row) + 1):
        v = ws.cell(row=r, column=col).value
        if isinstance(v, str) and v.strip().lower() in label_candidates:
            return r
    return None


def find_location_facility_id(ws, resolver: FacilityResolver) -> int:
    r = _find_row(ws, {"location:"})
    if r is None:
        raise ValueError("Could not find 'Location:' row")
    name = ws.cell(row=r, column=2).value
    if isinstance(name, str):
        # "ALIYA OF GLENWOOD LLC" -> match against dim_facility's
        # "Aliya Glenwood" / alias "Aliya of Glenwood" case-insensitively;
        # strip the operator prefix and legal suffix, resolver handles casing.
        cleaned = re.sub(r"\bLLC\b", "", name, flags=re.IGNORECASE).strip()
        fid = resolver.resolve(cleaned) or resolver.resolve(name.strip())
        if fid is not None:
            return fid
    raise ValueError(f"Could not resolve facility for Location: {name!r}")


def find_period_columns(ws, header_rows=(7, 8, 9), max_col=40) -> dict[int, str]:
    """Every real period column is labeled "<MM>/01/<YYYY> Through" in the
    label row (cumulative YTD-through-that-month). One extra column
    duplicates the final month's date under a "Period Ending" header
    instead -- a single-month (non-cumulative) figure for the same
    calendar date as the last YTD column. Summing both into one
    period_date would blend two different bases and break validation, so
    only "... Through" columns are kept.
    """
    label_row, date_row, actual_row = header_rows
    cols = {}
    for c in range(2, max_col + 1):
        kind = ws.cell(row=actual_row, column=c).value
        if not (isinstance(kind, str) and kind.strip().lower() == "actual"):
            continue
        header = ws.cell(row=label_row, column=c).value
        if not (isinstance(header, str) and "through" in header.lower()):
            continue
        date_val = ws.cell(row=date_row, column=c).value
        if date_val:
            try:
                cols[c] = excel_date_to_iso(date_val)
            except ValueError:
                continue
    return cols


def _closes(label: str, top_label: str) -> bool:
    label_l, top_l = label.lower(), top_label.lower()
    if label_l == top_l:
        return True
    # Some closing rows have typos ("Tota Days Medicaid Traditional",
    # "Total Days Privat") that break an exact "total <label>" match --
    # any total-flavored prefix at this indent is treated as a closer.
    for prefix in ("total ", "tota "):
        if label_l.startswith(prefix):
            return True
    return False


def _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label):
    conn.execute(
        """
        INSERT INTO exceptions_log (facility_id, period_date, source_file, load_batch_id, exception_type, detail)
        VALUES (NULL, ?, ?, ?, 'unmapped_account', ?)
        """,
        (period_date, source_file, load_batch_id, f"No master mapping for Aliya; heuristic classification: {raw_label!r}"),
    )


def parse_and_load(conn, ws, facility_id, period_cols, operator_id, source_file, load_batch_id):
    stack: list[tuple[int, str]] = []

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
            if indent == top_indent and _closes(text, top_label):
                stack.pop()
                consumed = True
                break
            stack.pop()
        if consumed:
            continue

        if lower.startswith("total ") or lower.startswith("tota "):
            continue

        if lower == "net income":
            for c, period_date in period_cols.items():
                v = ws.cell(row=r, column=c).value
                if isinstance(v, (int, float)):
                    insert_reported_net_income(conn, facility_id, period_date, float(v), source_file, f"row{r}", load_batch_id)
            continue

        has_value = any(isinstance(ws.cell(row=r, column=c).value, (int, float)) for c in period_cols)

        if not has_value:
            stack.append((indent, text))
            continue

        top_section = stack[0][1].lower() if stack else None

        if top_section == "total days current and past":
            # Payor is whatever group most immediately named one (deepest
            # stack entry below the Days Current/Past wrapper); bare GL-code
            # leaves with no payor group above them (e.g. a grand-total
            # "911010 - Days-In House_Current" sibling to "Days Current"/
            # "Days Past") are skipped -- they'd double count the payor-
            # level rows that already sum to the same total.
            if len(stack) < 3:
                continue
            payor_label = re.sub(r"^Days\s+", "", stack[-1][1], flags=re.IGNORECASE)
            payor = normalize_payor(payor_label, OPERATOR_NAME, is_census=True)
            for c, period_date in period_cols.items():
                v = ws.cell(row=r, column=c).value
                if isinstance(v, (int, float)) and v != 0:
                    insert_census_fact(conn, facility_id, period_date, payor, float(v), source_file, load_batch_id)
            continue

        if top_section == "revenue":
            statement_type, category = "revenue", "Other Income / Expense"
        elif top_section == "operating expenses":
            statement_type = "opex"
            department_label = stack[1][1].lower() if len(stack) >= 2 else ""
            category = DEPARTMENT_TO_CATEGORY.get(department_label, stack[1][1] if len(stack) >= 2 else "Other")
        elif top_section == "non operating expenses":
            statement_type, category = "capital", "Capital Expenses"
        else:
            continue

        code, gl_label = split_code_and_label(text)
        qualifier = stack[1][1] if len(stack) >= 2 else (stack[-1][1] if stack else "")
        raw_label = f"{qualifier}: {gl_label}"
        sub_group = salaries_or_other(gl_label)
        detail = NON_OPERATING_TO_CATEGORY.get(qualifier.lower(), gl_label) if top_section == "non operating expenses" else gl_label
        if any("regional allocation" in s[1].lower() for s in stack):
            detail = "Other"
        sign = default_sign_multiplier(gl_label)

        mapping_id = get_or_create_mapping(
            conn, operator_id, code, raw_label, statement_type, category, sub_group, detail, sign,
            notes="source=heuristic_fallback",
        )
        _log_unmapped(conn, None, source_file, load_batch_id, raw_label)
        for c, period_date in period_cols.items():
            v = ws.cell(row=r, column=c).value
            if isinstance(v, (int, float)) and v != 0:
                insert_financial_fact(
                    conn, facility_id, period_date, mapping_id, float(v) * sign, source_file, f"row{r}", load_batch_id
                )


def load_file(conn: sqlite3.Connection, path: str, operator_id: int, resolver: FacilityResolver) -> dict:
    wb = load_workbook_any(path)
    source_file = os.path.basename(path)
    load_batch_id = new_batch_id()

    ws = wb["P& L Trailing YTD Detailed Cons"]
    facility_id = find_location_facility_id(ws, resolver)
    period_cols = find_period_columns(ws)
    if not period_cols:
        raise ValueError("No Actual period columns found")

    parse_and_load(conn, ws, facility_id, period_cols, operator_id, source_file, load_batch_id)
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

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "aliya")
    files = sorted(glob.glob(os.path.join(raw_dir, "*.xlsx")))

    total_pass = total_fail = 0
    for path in files:
        try:
            summary = load_file(conn, path, operator_id, resolver)
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

    print(f"\nTOTAL: {total_pass} passed, {total_fail} failed across {len(files)} files")
    conn.close()


if __name__ == "__main__":
    main()
