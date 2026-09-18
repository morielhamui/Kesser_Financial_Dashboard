"""Curis operator parser.

Source format: consolidated multi-facility statements, one workbook per
facility group ("Petersen Group") per month, one column per facility plus
a "Total" column. See PROJECT_RULES.md sections 2, 2b, 3-8 for the
business rules this implements, in particular:

  - The master account mapping (PROJECT_RULES.md section 2b) is the
    primary source for every raw account's classification. Raw labels are
    built to match its exact convention (department/payor-qualified,
    dash-separated, GL code stripped) so lookups hit; a parser-local
    heuristic is only a fallback for labels the master doesn't cover, and
    every such gap is logged to exceptions_log for visibility.
  - Structural (not keyword-whitelist) addbacks detection: everything
    after the "Net Income" row in "AC - Statement of Operations" is
    EBITDAR-addback metadata, regardless of how that section happens to
    be labeled this month (varies: "additional addbacks", "Related
    Party/Non Recurring Addbacks", or absent in *_NO_ADDBACKS files).
  - Facility column position is NOT consistent across sheets within the
    same workbook -- re-derived independently per sheet (see
    find_facility_columns).
  - Curis-only hospice-Medicaid census fold (sourced from the master
    mapping's Census rows via normalize_payor).
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

OPERATOR_NAME = "Curis"


def _indent(cell_value: str) -> int:
    return len(cell_value) - len(cell_value.lstrip(" "))


def _find_row(ws, label_candidates, col=1, max_row=15):
    for r in range(1, min(max_row, ws.max_row) + 1):
        v = ws.cell(row=r, column=col).value
        if isinstance(v, str) and v.strip().lower() in label_candidates:
            return r
    return None


def find_facility_columns(ws, resolver: FacilityResolver, header_search_rows=12):
    """Dynamically locate the header row listing facility names and return
    {column_index: facility_id}, skipping the group "Total" column and any
    column that doesn't resolve to a known Curis facility.

    Picks the row with the MOST resolved matches in the search window,
    not the first row clearing a minimum threshold -- some files have a
    stray extra header row (fewer facilities, shifted columns) above the
    real one, the same structural failure mode as Lincoln's extra
    metadata row. Taking the first match-worthy row would silently lock
    onto the wrong, shorter column layout.
    """
    group_row = _find_row(ws, {"facility group:"})
    start = (group_row or 1) + 1
    best_cols: dict[int, int] = {}
    for r in range(start, min(start + header_search_rows, ws.max_row) + 1):
        cols = {}
        for c in range(2, ws.max_column + 1):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and v.strip():
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


def _resolve_mapping(
    conn, master: MasterMappingLookup, operator_id, raw_label,
    fallback_statement_type, fallback_category, fallback_detail, fallback_payor,
    period_date, source_file, load_batch_id,
):
    """Master mapping first, parser heuristic fallback second (logged)."""
    hit = master.lookup(raw_label)
    if hit is not None:
        mapping_id, statement_type, category, detail, payor, sign = hit
        return mapping_id, sign
    sign = default_sign_multiplier(raw_label)
    mapping_id = get_or_create_mapping(
        conn, operator_id, None, raw_label, fallback_statement_type, fallback_category,
        None, fallback_detail, sign, payor=fallback_payor, notes="source=heuristic_fallback",
    )
    _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label)
    return mapping_id, sign


def _insert_line(conn, ws, row, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id):
    for c, fid in facility_cols.items():
        v = ws.cell(row=row, column=c).value
        if isinstance(v, (int, float)) and v != 0:
            insert_financial_fact(
                conn, fid, period_date, mapping_id, float(v) * sign, source_file, f"row{row}", load_batch_id
            )


def parse_ac_statement_of_operations(
    conn, ws, facility_cols, operator_id, master, period_date, source_file, load_batch_id
):
    """Parses AC - Statement of Operations for: capital items, Management
    Fees, Nursing Home Fee, and Other Income/Expense detail, plus the
    reported Net Income line. Stops at "Net Income" -- everything after
    that (EBITDAR, addbacks) is informational only and never loaded.
    "Gross Resident Income" and the "Ancillary Expenses" aggregate are
    subtotal-exclude per the master mapping (real detail comes from the
    Schedule of Resident Income and Ancillary Expenses by Payor Detail
    sheets instead) -- skipped here to avoid double counting.
    """
    net_income_row = None
    for r in range(1, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if isinstance(label, str) and label.strip().lower() == "net income":
            net_income_row = r
            break
    if net_income_row is None:
        raise ValueError(f"No 'Net Income' row found in {source_file}")

    section = None
    for r in range(11, net_income_row + 1):
        label = ws.cell(row=r, column=1).value
        if not isinstance(label, str) or not label.strip():
            continue
        indent = _indent(label)
        text = label.strip()
        lower = text.lower()

        if indent == 2:
            if lower in ("net resident income", "operating expenses", "other income / expenses"):
                section = lower
                continue
            if lower.startswith("total ") or lower == "income before general and administrative expenses":
                continue  # subtotal row, not an account
            if lower == "net income":
                for c, fid in facility_cols.items():
                    v = ws.cell(row=r, column=c).value
                    if isinstance(v, (int, float)):
                        insert_reported_net_income(
                            conn, fid, period_date, float(v), source_file, f"row{r}", load_batch_id
                        )
                continue
            if lower == "general and administrative expenses":
                continue  # detail comes from the G&A sheet
            # Management Fees, and Capital items (Rent, Real Estate Tax -
            # CY, Interest, Interest - Other, Depreciation, Amortization)
            mapping_id, sign = _resolve_mapping(
                conn, master, operator_id, text,
                "opex" if lower == "management fees" else "capital",
                "Management Fees" if lower == "management fees" else "Capital Expenses",
                text, None,
                period_date, source_file, load_batch_id,
            )
            _insert_line(conn, ws, r, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id)
            continue

        if indent == 4:
            if lower.startswith("total "):
                continue
            if section == "net resident income":
                if lower == "nursing home fee":
                    mapping_id, sign = _resolve_mapping(
                        conn, master, operator_id, text, "opex", "General and Administrative",
                        "Licenses and Provider Fee", None,
                        period_date, source_file, load_batch_id,
                    )
                    _insert_line(conn, ws, r, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id)
                # Gross Resident Income and Ancillary Expenses are
                # subtotal-exclude aggregates -- real detail loaded
                # separately from the payor-level sheets.
                continue
            if section == "other income / expenses":
                mapping_id, sign = _resolve_mapping(
                    conn, master, operator_id, text, "revenue", "Other Income / Expense", text, None,
                    period_date, source_file, load_batch_id,
                )
                _insert_line(conn, ws, r, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id)
                continue


def parse_department_sheet(
    conn, ws, facility_cols, operator_id, master, period_date, source_file, load_batch_id,
    fallback_statement_type="opex",
):
    """Shared 3-level indent parser for "Operating Expenses by Department"
    and "G&A Expenses by Department": section(2) / department-or-subgroup(4)
    / GL account(6). Raw labels are built as "{group_label} - {gl_label}"
    (dash-separated, GL code stripped) to match the master mapping's own
    convention exactly -- e.g. "Nursing Expenses - Salaries - Regular",
    "G&A Dept Expenses - Bad debts Write-Off", "Marketing Expenses -
    Advertising/Marketing". The master mapping (not this parser) is what
    reclassifies Marketing out of the G&A sheet into its own category, and
    reclassifies specific "G&A Dept Expenses" lines into Nursing/Plant/etc
    where that's the true originating department.
    """
    current_group_label = None
    for r in range(11, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if not isinstance(label, str) or not label.strip():
            continue
        indent = _indent(label)
        text = label.strip()
        lower = text.lower()

        if indent <= 2:
            continue  # top-level section header

        if indent == 4:
            if lower.startswith("total "):
                continue
            current_group_label = text
            next_label = ws.cell(row=r + 1, column=1).value if r + 1 <= ws.max_row else None
            has_children = isinstance(next_label, str) and _indent(next_label) == 6
            if has_children:
                continue  # header only; GL accounts follow at indent 6
            # No children this period -- the subgroup line IS the account
            # (e.g. a bare "Other Professional" total with nothing under it).
            raw_label = text
            mapping_id, sign = _resolve_mapping(
                conn, master, operator_id, raw_label, fallback_statement_type,
                current_group_label, salaries_or_other(text), None,
                period_date, source_file, load_batch_id,
            )
            _insert_line(conn, ws, r, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id)
            continue

        if indent == 6:
            _, gl_label = split_code_and_label(text)
            raw_label = f"{current_group_label} - {gl_label}"
            mapping_id, sign = _resolve_mapping(
                conn, master, operator_id, raw_label, fallback_statement_type,
                current_group_label, salaries_or_other(gl_label), None,
                period_date, source_file, load_batch_id,
            )
            _insert_line(conn, ws, r, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id)


def parse_resident_income_sheet(conn, ws, facility_cols, operator_id, master, period_date, source_file, load_batch_id):
    for r in range(11, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if not isinstance(label, str) or not label.strip():
            continue
        indent = _indent(label)
        text = label.strip()
        if indent != 4 or text.lower().startswith("total "):
            continue
        payor = normalize_payor(text, OPERATOR_NAME)
        mapping_id, sign = _resolve_mapping(
            conn, master, operator_id, text, "revenue", "Resident Income", payor, payor,
            period_date, source_file, load_batch_id,
        )
        _insert_line(conn, ws, r, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id)


def parse_ancillary_expense_detail_sheet(
    conn, ws, facility_cols, operator_id, master, period_date, source_file, load_batch_id
):
    """"Ancillary Expenses by Payor Detail": section(2) / payor-group(4,
    e.g. "Ancillary Expense Medicaid") / GL account(6, e.g. "503100 -
    Ancillary Costs - Physical Therapy"). Reclassified by the master
    mapping as Operating Expense, category="Ancillary" -- NOT a revenue
    contra, despite Curis's own AC sheet netting it against gross revenue
    in the "Net Resident Income" section.
    """
    current_group_label = None
    for r in range(11, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if not isinstance(label, str) or not label.strip():
            continue
        indent = _indent(label)
        text = label.strip()
        lower = text.lower()

        if indent <= 2:
            continue
        if indent == 4:
            if lower.startswith("total "):
                continue
            current_group_label = text
            continue
        if indent == 6:
            _, gl_label = split_code_and_label(text)
            raw_label = f"{current_group_label} - {gl_label}"
            payor = normalize_payor(current_group_label, OPERATOR_NAME)
            mapping_id, sign = _resolve_mapping(
                conn, master, operator_id, raw_label, "opex", "Ancillary", "Other", payor,
                period_date, source_file, load_batch_id,
            )
            _insert_line(conn, ws, r, facility_cols, mapping_id, sign, period_date, source_file, load_batch_id)


def parse_census_sheet(conn, ws, facility_cols, period_date, source_file, load_batch_id):
    for r in range(11, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if not isinstance(label, str) or not label.strip():
            continue
        indent = _indent(label)
        text = label.strip()
        if indent != 4 or text.lower().startswith("total "):
            continue
        payor = normalize_payor(text, OPERATOR_NAME, is_census=True)
        for c, fid in facility_cols.items():
            v = ws.cell(row=r, column=c).value
            if isinstance(v, (int, float)) and v != 0:
                insert_census_fact(conn, fid, period_date, payor, float(v), source_file, load_batch_id)


def _sheet(wb, *name_fragments):
    for name in wb.sheetnames:
        if all(frag.lower() in name.lower() for frag in name_fragments):
            return wb[name]
    raise KeyError(f"No sheet matching {name_fragments} in {wb.sheetnames}")


def load_file(conn: sqlite3.Connection, path: str, operator_id: int, resolver: FacilityResolver, master: MasterMappingLookup) -> dict:
    wb = load_workbook_any(path)
    source_file = os.path.basename(path)
    load_batch_id = new_batch_id()

    ws_ac = _sheet(wb, "AC", "Statement of Operations")
    period_date = find_period_date(ws_ac)
    # Facility column position is NOT consistent across sheets within the
    # same workbook -- some sheets drop a facility column entirely or add
    # an extra blank one. Every sheet's facility header must be re-derived
    # independently; reusing one sheet's column map on another silently
    # cross-wires facilities.
    facility_cols_ac = find_facility_columns(ws_ac, resolver)

    parse_ac_statement_of_operations(conn, ws_ac, facility_cols_ac, operator_id, master, period_date, source_file, load_batch_id)

    ws_opex = _sheet(wb, "Operating Expenses by Depart")
    parse_department_sheet(
        conn, ws_opex, find_facility_columns(ws_opex, resolver), operator_id, master,
        period_date, source_file, load_batch_id, fallback_statement_type="opex",
    )
    ws_ga = _sheet(wb, "G&A Expenses by Depart")
    parse_department_sheet(
        conn, ws_ga, find_facility_columns(ws_ga, resolver), operator_id, master,
        period_date, source_file, load_batch_id, fallback_statement_type="opex",
    )
    ws_sched = _sheet(wb, "Schedule of Resident Income")
    parse_resident_income_sheet(
        conn, ws_sched, find_facility_columns(ws_sched, resolver), operator_id, master,
        period_date, source_file, load_batch_id,
    )
    ws_anc = _sheet(wb, "Ancillary Expenses by Payor Det")
    parse_ancillary_expense_detail_sheet(
        conn, ws_anc, find_facility_columns(ws_anc, resolver), operator_id, master,
        period_date, source_file, load_batch_id,
    )
    ws_census = _sheet(wb, "Monthly Census by Payor")
    parse_census_sheet(conn, ws_census, find_facility_columns(ws_census, resolver), period_date, source_file, load_batch_id)

    conn.commit()

    results = []
    for fid in set(facility_cols_ac.values()):
        passed, recomputed, reported = validate_facility_period(conn, fid, period_date, source_file, load_batch_id)
        results.append((fid, passed, recomputed, reported))
    conn.commit()
    return {
        "source_file": source_file,
        "period_date": period_date,
        "n_facilities": len(facility_cols_ac),
        "results": results,
    }


def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "kesser_financials.sqlite3")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    operator_id = conn.execute("SELECT operator_id FROM dim_operator WHERE operator_name = ?", (OPERATOR_NAME,)).fetchone()[0]
    resolver = FacilityResolver(conn, operator_id)
    master = MasterMappingLookup(conn, operator_id)

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "curis")
    files = sorted(glob.glob(os.path.join(raw_dir, "*")))

    total_pass = total_fail = 0
    for path in files:
        if path.endswith(".csv") or "MANIFEST" in path:
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
