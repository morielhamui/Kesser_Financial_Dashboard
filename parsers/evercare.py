"""Evercare operator parser.

Source format: "Petersen 4-Pack" workbook, one tab per facility
(Collinsville, Jerseyville, Lebanon, Swansea, Breese), single period per
file (Actual + PPD columns). Two Evercare facilities (Edwardsville,
Evercare University) have no raw files uploaded -- a tracked gap.

See PROJECT_RULES.md section 5: Evercare is the one operator that must
NOT fold Hospice into Medicaid for census/revenue -- it has its own real
Hospice line, and per-diem rates coincidentally matching Medicaid's in a
given period is real data, not a mapping bug (verified: Collinsville,
04/2026, both at $214.80/day). normalize_payor() already skips the fold
for any operator other than Curis/Lincoln, so this is handled by omission
here, not a special case.

Deep indentation (up to 7 levels, 2/4/6/8/10/12/14) uses the same generic
indentation-stack approach as Extendicare/Lincoln. The master mapping
uses bare leaf labels for Evercare (e.g. a single "Consultant" row maps
to Social Service, with no separate entry for the same bare label
appearing under Activities) -- so some raw leaf labels legitimately
collide across departments by the master's own design, not a bug in this
parser. This is harmless for Net Income validation because
insert_financial_fact sums on conflict rather than overwriting; it would
only blur department-level attribution in the later metrics layer.
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
)
from validation.validate import validate_facility_period

OPERATOR_NAME = "Evercare"

SECTION_ROUTES = {
    "census": "census",
    "prior period census adjustment": "census",
    "revenue": "revenue",
    "expenses": "opex",
    "capital expenses": "capital",
}


def _indent(cell_value: str) -> int:
    return len(cell_value) - len(cell_value.lstrip(" "))


def _find_row(ws, label_candidates, col=1, max_row=15):
    for r in range(1, min(max_row, ws.max_row) + 1):
        v = ws.cell(row=r, column=col).value
        if isinstance(v, str) and v.strip().lower() in label_candidates:
            return r
    return None


def find_period_date(ws) -> str:
    # "As of Date:" (row 4) is blank on some sheets within a multi-tab
    # workbook even though the date is right there under "Month Ending"
    # a few rows down (row 9) -- an apparent shared-formula/copy artifact
    # that drops the value on some tabs but not others in the same file.
    r = _find_row(ws, {"as of date:"})
    if r is not None:
        v = ws.cell(row=r, column=2).value
        if v:
            return excel_date_to_iso(v)
    r = _find_row(ws, {"month ending"}, col=2, max_row=12)
    if r is not None:
        v = ws.cell(row=r + 1, column=2).value
        if v:
            return excel_date_to_iso(v)
    raise ValueError("Could not find a usable period date")


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
    if "provider assessment" in raw_label.lower():
        fallback_category, detail = "General and Administrative", "Licenses and Provider Fee"
    mapping_id = get_or_create_mapping(
        conn, operator_id, None, raw_label, fallback_statement_type, fallback_category,
        None, detail, sign, notes="source=heuristic_fallback",
    )
    _log_unmapped(conn, period_date, source_file, load_batch_id, raw_label)
    return mapping_id, sign


def parse_and_load(conn, ws, facility_id, period_date, operator_id, master, source_file, load_batch_id):
    stack: list[tuple[int, str]] = []
    net_income_row = None
    for r in range(1, ws.max_row + 1):
        label = ws.cell(row=r, column=1).value
        if isinstance(label, str) and label.strip().lower() == "net income (loss)":
            net_income_row = r
            break
    end_row = net_income_row if net_income_row is not None else ws.max_row

    def closes(indent, label, top_indent, top_label):
        if indent != top_indent:
            return False
        return label.lower() == top_label.lower() or label.lower() == f"total {top_label.lower()}"

    for r in range(11, end_row + 1):
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
                break
            stack.pop()
        if consumed:
            continue

        if lower.startswith("total "):
            continue

        if r == net_income_row:
            v = ws.cell(row=r, column=2).value
            if isinstance(v, (int, float)):
                insert_reported_net_income(conn, facility_id, period_date, float(v), source_file, f"row{r}", load_batch_id)
            continue

        has_value = isinstance(ws.cell(row=r, column=2).value, (int, float))

        if not has_value:
            stack.append((indent, text))
            continue

        # Leaf. Section is whatever top-level (depth-0-in-stack) wrapper
        # is open, however deep this leaf is nested beneath it.
        section = SECTION_ROUTES.get(stack[0][1].lower()) if stack else None
        v = ws.cell(row=r, column=2).value

        if section == "census":
            payor = normalize_payor(text, OPERATOR_NAME, is_census=True)
            if v != 0:
                insert_census_fact(conn, facility_id, period_date, payor, float(v), source_file, load_batch_id)
            continue

        if section in ("revenue", "opex", "capital"):
            fallback_category = stack[-1][1] if stack else section
            mapping_id, sign = _resolve_mapping(
                conn, master, operator_id, text, section, fallback_category,
                period_date, source_file, load_batch_id,
            )
            if v != 0:
                insert_financial_fact(
                    conn, facility_id, period_date, mapping_id, float(v) * sign, source_file, f"row{r}", load_batch_id
                )
            continue

        # Bare top-level items with no wrapper section at all. Two kinds
        # share this exact shape (indent 2, direct value, no section):
        # real deductions the master mapping knows about ("Management
        # Fee", "One Time Expenses" both sit directly between "Total
        # Capital Expenses" and "Net Income (Loss)") vs. informational
        # rollups it does NOT ("EBITDARM", "EBITDAR" are recomputations of
        # figures already counted elsewhere -- loading them would double
        # count). The master mapping itself is what tells them apart:
        # only load a stackless leaf when master actually covers it; an
        # unmapped one is informational by construction, not a heuristic-
        # fallback candidate.
        if not stack:
            hit = master.lookup(text)
            if hit is None:
                continue
            mapping_id, statement_type, category, detail, payor, sign = hit
            if v != 0:
                insert_financial_fact(
                    conn, facility_id, period_date, mapping_id, float(v) * sign, source_file, f"row{r}", load_batch_id
                )


def load_file(conn: sqlite3.Connection, path: str, operator_id: int, resolver: FacilityResolver, master: MasterMappingLookup) -> list[dict]:
    wb = load_workbook_any(path)
    source_file = os.path.basename(path)
    results = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        facility_id = resolver.resolve(sheet_name)
        if facility_id is None:
            print(f"  WARNING: could not resolve facility for sheet {sheet_name!r} in {source_file}")
            continue
        try:
            load_batch_id = new_batch_id()
            period_date = find_period_date(ws)
            parse_and_load(conn, ws, facility_id, period_date, operator_id, master, source_file, load_batch_id)
            conn.commit()
            passed, recomputed, reported = validate_facility_period(conn, facility_id, period_date, source_file, load_batch_id)
            conn.commit()
            results.append({
                "source_file": source_file, "sheet": sheet_name, "period_date": period_date,
                "passed": passed, "recomputed": recomputed, "reported": reported,
            })
        except Exception as e:
            print(f"  FAILED to parse sheet {sheet_name!r} in {source_file}: {e}")
    return results


def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "kesser_financials.sqlite3")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    operator_id = conn.execute("SELECT operator_id FROM dim_operator WHERE operator_name = ?", (OPERATOR_NAME,)).fetchone()[0]
    resolver = FacilityResolver(conn, operator_id)
    master = MasterMappingLookup(conn, operator_id)

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "evercare")
    files = sorted(glob.glob(os.path.join(raw_dir, "*.xlsx")))

    total_pass = total_fail = 0
    for path in files:
        try:
            results = load_file(conn, path, operator_id, resolver, master)
        except Exception as e:
            print(f"FAILED to parse {os.path.basename(path)}: {e}")
            continue
        for r in results:
            status = "OK" if r["passed"] else f"FAILED diff={r['recomputed'] - r['reported']:.2f}"
            print(f"{r['source_file']} [{r['sheet']} {r['period_date']}]: {status}")
            total_pass += 1 if r["passed"] else 0
            total_fail += 0 if r["passed"] else 1

    n_unmapped = conn.execute(
        "SELECT COUNT(DISTINCT detail) FROM exceptions_log WHERE exception_type = 'unmapped_account'"
    ).fetchone()[0]
    print(f"\nTOTAL: {total_pass} passed, {total_fail} failed across {len(files)} files")
    print(f"Distinct unmapped raw account labels (heuristic fallback used): {n_unmapped}")
    conn.close()


if __name__ == "__main__":
    main()
