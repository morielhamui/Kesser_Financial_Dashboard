#!/usr/bin/env python3
"""Load data/reference/kesser_master_account_mapping.xlsx into
dim_account_mapping. This is the source-of-truth mapping (see the
workbook's own README tab) for Curis, Lineage, Extendicare, Evercare,
Lincoln -- it does not cover Aliya or Allure (discovered after this file
was built; those two get parser-local heuristic mappings until/unless a
master mapping is provided for them).

"All Mappings" columns: Operator, Raw Account, Grouping, Sub-Group,
Detail, Payor, Sign Multiplier, Exclude (subtotal).

  - Grouping   -> dim_account_mapping.statement_type ('revenue'/'opex'/'capital')
  - Sub-Group  -> dim_account_mapping.category (department: Nursing, Ancillary, ...)
  - Detail     -> dim_account_mapping.detail (Salaries, Supplies, Therapy, ...)
  - Payor      -> dim_account_mapping.payor (nullable; mainly Ancillary opex + Revenue)

Rows with a blank Grouping and/or Exclude=1 are section/department
subtotals, not real accounts (e.g. "Nursing Expenses" the bare department
header, or "Gross Resident Income" the AC-sheet aggregate) -- these are
NOT loaded into dim_account_mapping at all. Parsers must recognize and
skip them structurally (by section/indentation), independent of this
table, since a subtotal row that slips through would double-count.

Grouping="Census" rows are also not loaded into dim_account_mapping
(census isn't GL-coded and doesn't flow through fact_tenant_financials) --
instead they seed the canonical payor lookup used by each operator's
census parser (via get_census_payor_map()).

The "Sign Adjustments" tab is merged in on top (same shape minus Payor),
covering accounts the source stores negative that must flip sign (e.g.
Extendicare's Bed Tax / Rev-Assessment Tax).
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"
DEFAULT_MAPPING_PATH = REPO_ROOT / "data" / "reference" / "kesser_master_account_mapping.xlsx"

GROUPING_TO_STATEMENT_TYPE = {
    "revenue": "revenue",
    "operating expense": "opex",
    "capital expenses": "capital",
}


def _operator_id(conn: sqlite3.Connection, operator_name: str) -> int | None:
    row = conn.execute(
        "SELECT operator_id FROM dim_operator WHERE operator_name = ?", (operator_name,)
    ).fetchone()
    return row[0] if row else None


def load(conn: sqlite3.Connection, path: pathlib.Path) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["All Mappings"]

    operator_id_cache: dict[str, int | None] = {}
    n_loaded = 0
    n_skipped_subtotal = 0
    n_skipped_census = 0
    n_skipped_unknown_operator = 0

    def get_op_id(name: str):
        if name not in operator_id_cache:
            operator_id_cache[name] = _operator_id(conn, name)
        return operator_id_cache[name]

    for r in range(2, ws.max_row + 1):
        operator_name = ws.cell(row=r, column=1).value
        raw_account = ws.cell(row=r, column=2).value
        grouping = ws.cell(row=r, column=3).value
        sub_group = ws.cell(row=r, column=4).value
        detail = ws.cell(row=r, column=5).value
        payor = ws.cell(row=r, column=6).value
        sign = ws.cell(row=r, column=7).value
        exclude = ws.cell(row=r, column=8).value

        if not operator_name or not raw_account:
            continue
        operator_name = str(operator_name).strip()
        raw_account = str(raw_account).strip()

        if exclude or not grouping:
            n_skipped_subtotal += 1
            continue

        grouping_key = str(grouping).strip().lower()
        if grouping_key == "census":
            n_skipped_census += 1
            continue

        statement_type = GROUPING_TO_STATEMENT_TYPE.get(grouping_key)
        if statement_type is None:
            continue

        operator_id = get_op_id(operator_name)
        if operator_id is None:
            n_skipped_unknown_operator += 1
            continue

        conn.execute(
            """
            INSERT INTO dim_account_mapping
                (operator_id, raw_account_code, raw_account_label, statement_type,
                 category, sub_group, detail, payor, sign_multiplier, notes)
            VALUES (?, NULL, ?, ?, ?, NULL, ?, ?, ?, 'source=master_mapping')
            ON CONFLICT(operator_id, raw_account_code, raw_account_label) DO UPDATE SET
                statement_type = excluded.statement_type,
                category = excluded.category,
                detail = excluded.detail,
                payor = excluded.payor,
                sign_multiplier = excluded.sign_multiplier,
                notes = excluded.notes
            """,
            (
                operator_id,
                raw_account,
                statement_type,
                sub_group,
                detail,
                payor,
                int(sign) if sign is not None else 1,
            ),
        )
        n_loaded += 1

    # Sign Adjustments tab: same shape minus Payor. Applies on top (a
    # later load of the same raw_account_label wins via the same upsert).
    ws_signs = wb["Sign Adjustments"]
    n_sign_adjustments = 0
    for r in range(2, ws_signs.max_row + 1):
        operator_name = ws_signs.cell(row=r, column=1).value
        raw_account = ws_signs.cell(row=r, column=2).value
        grouping = ws_signs.cell(row=r, column=3).value
        sub_group = ws_signs.cell(row=r, column=4).value
        detail = ws_signs.cell(row=r, column=5).value
        sign = ws_signs.cell(row=r, column=6).value
        if not operator_name or not raw_account or not grouping:
            continue
        operator_name = str(operator_name).strip()
        operator_id = get_op_id(operator_name)
        if operator_id is None:
            continue
        statement_type = GROUPING_TO_STATEMENT_TYPE.get(str(grouping).strip().lower())
        if statement_type is None:
            continue
        conn.execute(
            """
            INSERT INTO dim_account_mapping
                (operator_id, raw_account_code, raw_account_label, statement_type,
                 category, sub_group, detail, payor, sign_multiplier, notes)
            VALUES (?, NULL, ?, ?, ?, NULL, ?, NULL, ?, 'source=master_mapping_sign_adjustment')
            ON CONFLICT(operator_id, raw_account_code, raw_account_label) DO UPDATE SET
                statement_type = excluded.statement_type,
                category = excluded.category,
                detail = excluded.detail,
                sign_multiplier = excluded.sign_multiplier,
                notes = excluded.notes
            """,
            (operator_id, str(raw_account).strip(), statement_type, sub_group, detail, int(sign)),
        )
        n_sign_adjustments += 1

    conn.commit()
    return {
        "loaded": n_loaded,
        "sign_adjustments": n_sign_adjustments,
        "skipped_subtotal": n_skipped_subtotal,
        "skipped_census": n_skipped_census,
        "skipped_unknown_operator": n_skipped_unknown_operator,
    }


def get_census_payor_map(path: pathlib.Path = DEFAULT_MAPPING_PATH) -> dict[str, dict[str, str]]:
    """Returns {operator_name: {raw_census_label_lower: canonical_payor}}
    from the master mapping's Grouping="Census" rows (the Detail column
    holds the canonical payor bucket, e.g. "Hospice Medicaid" -> "Medicaid").
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["All Mappings"]
    result: dict[str, dict[str, str]] = {}
    for r in range(2, ws.max_row + 1):
        operator_name = ws.cell(row=r, column=1).value
        raw_account = ws.cell(row=r, column=2).value
        grouping = ws.cell(row=r, column=3).value
        detail = ws.cell(row=r, column=5).value
        if not operator_name or not raw_account or not grouping:
            continue
        if str(grouping).strip().lower() != "census":
            continue
        result.setdefault(str(operator_name).strip(), {})[str(raw_account).strip().lower()] = detail
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--mapping", type=pathlib.Path, default=DEFAULT_MAPPING_PATH)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    stats = load(conn, args.mapping)
    conn.close()

    print(f"Loaded {stats['loaded']} account mappings + {stats['sign_adjustments']} sign adjustments.")
    print(f"Skipped {stats['skipped_subtotal']} subtotal/excluded rows, {stats['skipped_census']} census rows.")
    if stats["skipped_unknown_operator"]:
        print(f"WARNING: skipped {stats['skipped_unknown_operator']} rows for operators not in dim_operator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
