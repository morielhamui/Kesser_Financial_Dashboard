"""Allure operator parser.

7th operator, discovered mid-project (not in the original 6, not covered
by the master account mapping). Facilities: Mendota, Peru, Sterling
(no files uploaded), Walnut. Format: "Income Statement Trending Detail -
GGM" -- a flat 2-level hierarchy (0-indent section/department headers and
their "TOTAL <name>" closers, 3-space-indent leaf accounts), no deeper
nesting at all. Two physical containers carry the identical logical
structure and are both handled here:

  - .csv files: one combined header cell per column, e.g.
    "July 25_Actual $" / "July 25_Actual / Day", plus a "TOTALS" pair.
  - .xlsx "2025_YE_*_Financial_Statements" files, sheet "P&L Detail
    Trending": two header rows -- a datetime (first-of-month) row and an
    "Actual $"/"Actual / Day" label row underneath it.

Both are normalized into the same in-memory grid + period-column map so
one row-walking parser handles both. Section routing is purely by the
0-indent header name (no master to confirm categories, so this is
heuristic-only, same posture as Aliya): "Revenue" -> revenue by payor,
"Patient Days" -> census, "Capital Costs" -> capital, every other named
department -> opex. "Total Expenses" already includes the Capital Costs
subtotal in this source (verified: Revenue - Total Expenses reproduces
Net Income exactly), which is why Capital Costs' own leaves must be
bucketed as "capital" here rather than folded into "opex" -- the 3-term
validation formula (Revenue - OpEx - Capital) only reproduces that same
Net Income if Capital's leaves are pulled out of the opex sum.
"""
from __future__ import annotations

import csv
import datetime
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3

from parsers.common import (
    FacilityResolver,
    default_sign_multiplier,
    get_or_create_mapping,
    insert_census_fact,
    insert_financial_fact,
    insert_reported_net_income,
    load_workbook_any,
    new_batch_id,
    normalize_payor,
)
from validation.validate import validate_facility_period

OPERATOR_NAME = "Allure"

DEPARTMENT_ALIASES = {
    "nursing & medical": "Nursing",
    "therapy & ancillary services": "Ancillary",
    "social services": "Social Service",
    "leisure time & activities": "Activities",
    "house & plant costs": "Plant",
    "food & nutrition": "Dietary",
    "employee welfare costs": "Employee Welfare",
    "general & administrative": "General and Administrative",
}

_MONTH_NAMES = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], start=1)}


def _last_day_of_month(year: int, month: int) -> str:
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    return (next_month - datetime.timedelta(days=1)).isoformat()


def _to_number(value):
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        v = value.strip().replace(",", "")
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None
    return None


_CSV_HEADER_RE = re.compile(r"^([A-Za-z]+)\s+(\d{2})_Actual \$$")


def load_grid_and_periods_csv(path: str) -> tuple[list[list], dict[int, str], str]:
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))
    facility_label = None
    for row in rows[:10]:
        for cell in row:
            if isinstance(cell, str) and cell.strip().lower().startswith("allure of"):
                facility_label = cell.strip()
    header_row_idx = None
    for i, row in enumerate(rows):
        if any(_CSV_HEADER_RE.match(c.strip()) for c in row if isinstance(c, str)):
            header_row_idx = i
            break
    if header_row_idx is None:
        raise ValueError("Could not find period header row")
    period_cols: dict[int, str] = {}
    for c, cell in enumerate(rows[header_row_idx]):
        if not isinstance(cell, str):
            continue
        m = _CSV_HEADER_RE.match(cell.strip())
        if m:
            month = _MONTH_NAMES.get(m.group(1).lower())
            if month:
                year = 2000 + int(m.group(2))
                period_cols[c] = _last_day_of_month(year, month)
    grid = rows[header_row_idx + 1:]
    grid = [[_to_number(v) if c != 0 else v for c, v in enumerate(row)] for row in grid]
    return grid, period_cols, facility_label


def load_grid_and_periods_xlsx(path: str) -> tuple[list[list], dict[int, str], str]:
    wb = load_workbook_any(path)
    ws = wb["P&L Detail Trending"]
    facility_label = ws.cell(row=1, column=1).value

    date_row = actual_row = None
    for r in range(1, 10):
        for c in range(2, ws.max_column + 1):
            if isinstance(ws.cell(row=r, column=c).value, datetime.datetime):
                date_row = r
                actual_row = r + 1
                break
        if date_row:
            break
    if date_row is None:
        raise ValueError("Could not find date header row")

    period_cols: dict[int, str] = {}
    for c in range(2, ws.max_column + 1):
        kind = ws.cell(row=actual_row, column=c).value
        date_val = ws.cell(row=date_row, column=c).value
        if isinstance(kind, str) and kind.strip().lower() == "actual $" and isinstance(date_val, datetime.datetime):
            period_cols[c - 1] = _last_day_of_month(date_val.year, date_val.month)  # -1: grid is 0-indexed below

    grid = []
    for r in range(actual_row + 1, ws.max_row + 1):
        row = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
        grid.append(row)
    return grid, period_cols, facility_label


def _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label):
    conn.execute(
        """
        INSERT INTO exceptions_log (facility_id, period_date, source_file, load_batch_id, exception_type, detail)
        VALUES (NULL, ?, ?, ?, 'unmapped_account', ?)
        """,
        (period_date, source_file, load_batch_id, f"No master mapping for Allure; heuristic classification: {raw_label!r}"),
    )


def parse_and_load(conn, grid, period_cols, facility_id, operator_id, source_file, load_batch_id):
    section = None  # 0-indent header currently open: None until we see one
    for row in grid:
        label = row[0]
        if not isinstance(label, str) or not label.strip():
            continue
        indent = len(label) - len(label.lstrip(" "))
        text = label.strip()
        lower = text.lower()

        if indent == 0:
            if lower.startswith("total "):
                continue  # closes whatever department/section was open
            if lower in ("net income - (loss)", "net income"):
                for c, period_date in period_cols.items():
                    v = row[c] if c < len(row) else None
                    if isinstance(v, (int, float)):
                        insert_reported_net_income(conn, facility_id, period_date, float(v), source_file, "grid", load_batch_id)
                section = None
                continue
            section = text
            continue

        # A 3-space-indent leaf under whatever section is currently open.
        if section is None:
            continue
        section_lower = section.lower()

        if section_lower == "patient days":
            payor = normalize_payor(text, OPERATOR_NAME, is_census=True)
            for c, period_date in period_cols.items():
                v = row[c] if c < len(row) else None
                if isinstance(v, (int, float)) and v != 0:
                    insert_census_fact(conn, facility_id, period_date, payor, float(v), source_file, load_batch_id)
            continue

        if section_lower == "revenue":
            statement_type, category = "revenue", normalize_payor(text, OPERATOR_NAME)
        elif section_lower == "capital costs":
            statement_type, category = "capital", "Capital Expenses"
        else:
            statement_type = "opex"
            category = DEPARTMENT_ALIASES.get(section_lower, section)

        sign = default_sign_multiplier(text)
        raw_label = f"{section}: {text}"
        mapping_id = get_or_create_mapping(
            conn, operator_id, None, raw_label, statement_type, category, None, text, sign,
            notes="source=heuristic_fallback",
        )
        for c, period_date in period_cols.items():
            v = row[c] if c < len(row) else None
            if isinstance(v, (int, float)) and v != 0:
                _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label)
                insert_financial_fact(conn, facility_id, period_date, mapping_id, float(v) * sign, source_file, "grid", load_batch_id)


def load_file(conn: sqlite3.Connection, path: str, operator_id: int, resolver: FacilityResolver) -> dict:
    source_file = os.path.basename(path)
    load_batch_id = new_batch_id()

    if path.lower().endswith(".csv"):
        grid, period_cols, facility_label = load_grid_and_periods_csv(path)
    else:
        grid, period_cols, facility_label = load_grid_and_periods_xlsx(path)
    if not period_cols:
        raise ValueError("No period columns found")

    # Walnut's combined label is "Allure of Walnut, Allure of Walnut ILF" --
    # take only the first facility named. dim_facility.facility_name is
    # the full "Allure of <X>" form, so no prefix-stripping here.
    facility_name = (facility_label or "").split(",")[0].strip()
    facility_id = resolver.resolve(facility_name)
    if facility_id is None:
        raise ValueError(f"Could not resolve facility for {facility_label!r}")

    parse_and_load(conn, grid, period_cols, facility_id, operator_id, source_file, load_batch_id)
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

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "allure")
    files = sorted(glob.glob(os.path.join(raw_dir, "*.csv"))) + sorted(glob.glob(os.path.join(raw_dir, "*.xlsx")))

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
