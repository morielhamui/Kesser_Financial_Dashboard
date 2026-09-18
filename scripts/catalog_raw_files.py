#!/usr/bin/env python3
"""Inspect every uploaded raw source file, classify it by operator/format
using structural signatures (not just filename), and copy it into
data/raw/<operator>/ with a manifest.

Usage:
    python3 scripts/catalog_raw_files.py --src <upload_dir> [--dest data/raw] [--manifest data/raw/MANIFEST.csv] [--dry-run]
"""
import argparse
import csv
import pathlib
import re
import shutil
import sys

import openpyxl

try:
    import xlrd
except ImportError:
    xlrd = None


def sniff_xlsx(path: pathlib.Path):
    """Return (sheet_names, header_text) for an openpyxl-readable file.

    Pass a file object rather than the path so openpyxl's extension check
    (which rejects ".xls" outright, even when the content is really a zip-
    based xlsx) is bypassed -- some sources here are mislabeled that way.
    """
    fh = open(path, "rb")
    try:
        wb = openpyxl.load_workbook(fh, data_only=True, read_only=True)
        sheet_names = wb.sheetnames
        ws = wb[sheet_names[0]]
        header_cells = []
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=12, values_only=True)):
            for v in row:
                if isinstance(v, str) and v.strip():
                    header_cells.append(v.strip())
            if i > 12:
                break
        wb.close()
        return sheet_names, header_cells
    finally:
        fh.close()


def sniff_xls_legacy(path: pathlib.Path):
    if xlrd is None:
        return [], []
    book = xlrd.open_workbook(path)
    sheet_names = book.sheet_names()
    sh = book.sheet_by_index(0)
    header_cells = []
    for r in range(min(12, sh.nrows)):
        for c in range(sh.ncols):
            v = sh.cell_value(r, c)
            if isinstance(v, str) and v.strip():
                header_cells.append(v.strip())
    return sheet_names, header_cells


def sniff_csv(path: pathlib.Path):
    header_cells = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            for v in row:
                if v and v.strip():
                    header_cells.append(v.strip())
            if i > 12:
                break
    return [], header_cells


def sniff(path: pathlib.Path):
    ext = path.suffix.lower()
    try:
        if ext in (".xlsx", ".xlsm"):
            return sniff_xlsx(path)
        if ext == ".xls":
            try:
                return sniff_xlsx(path)  # many ".xls" here are actually xlsx content
            except Exception:
                return sniff_xls_legacy(path)
        if ext == ".csv":
            return sniff_csv(path)
    except Exception as e:
        return [], [f"__SNIFF_ERROR__: {e}"]
    return [], []


EVERCARE_FOUR_PACK_TABS = {"Collinsville", "Jerseyville", "Lebanon", "Swansea", "Breese"}

ALLURE_FACILITIES = {"Peru", "Mendota", "Walnut", "Sterling"}
LINEAGE_XLSM_FACILITIES = {"North_Aurora", "Sandwich", "Irving_Park", "South_Elgin", "Ironwood"}


def classify(filename: str, sheet_names, header_cells):
    # Uploaded filenames are prefixed with an 8-hex-char id, e.g.
    # "067eff45-Lincoln_Income_Statement...xlsx" -- strip it so filename
    # patterns anchored with ^ still match the real basename.
    filename = re.sub(r"^[0-9a-f]{8}-", "", filename)
    header_blob = " | ".join(header_cells)
    sheet_set = set(sheet_names)

    if "ALIYA" in header_blob.upper() or re.match(r"^\d{6}_Aliya_of_", filename, re.IGNORECASE):
        return "Aliya", "ALIYA HEALTHCARE CONSULTING LLC multi-sheet workbook (Balance Sheet + P&L Trailing YTD Detailed)"

    if "Curis Services" in header_blob or (
        "Petersen Group" in header_blob or "Facility Group" in header_blob or "Facility group" in header_blob
    ):
        return "Curis", "Petersen Group consolidated statement"

    if sheet_set and sheet_set.issubset(EVERCARE_FOUR_PACK_TABS | {"Edwardsville", "University"}):
        return "Evercare", "Petersen 4-Pack by-tab workbook (Evercare)"

    if "Evercare" in header_blob:
        return "Evercare", "Evercare-labeled statement"

    if re.match(r"^Lincoln_Income_Statement", filename):
        return "Lincoln", "Multi-facility income statement by facility"

    if re.match(r"^(North_Aurora|Sandwich|Irving_Park|South_Elgin|Ironwood)_PL_", filename):
        return "Lineage", "Facility PL export (.xlsm)"

    if any(fac in filename for fac in ("Peru", "Mendota", "Walnut", "Sterling")) or "GGM" in header_blob:
        return "Allure", "Income Statement Trending Detail - GGM"

    if re.match(r"^(Arcola|Bement|Bridgeport|Farmer_City|Meadowbrook|St_Elmo|Tuscola)_", filename):
        return "Extendicare", "T12 Budget vs Actual / Balance Sheet, single facility"

    return "UNKNOWN", f"sheets={sheet_names[:5]} header_sample={header_cells[:8]}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=pathlib.Path, required=True)
    parser.add_argument("--dest", type=pathlib.Path, default=pathlib.Path("data/raw"))
    parser.add_argument("--manifest", type=pathlib.Path, default=pathlib.Path("data/raw/MANIFEST.csv"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = sorted(p for p in args.src.iterdir() if p.is_file())
    rows = []
    for path in files:
        if path.name.startswith("f3cd16f7") or "Facility_listing" in path.name:
            continue  # already handled separately
        sheet_names, header_cells = sniff(path)
        operator, detail = classify(path.name, sheet_names, header_cells)
        dest_dir = args.dest / operator.lower()
        dest_path = dest_dir / path.name
        rows.append(
            {
                "original_filename": path.name,
                "operator": operator,
                "detail": detail,
                "dest_path": str(dest_path),
                "size_bytes": path.stat().st_size,
            }
        )
        if not args.dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest_path)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifest, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["original_filename", "operator", "detail", "dest_path", "size_bytes"])
        writer.writeheader()
        writer.writerows(rows)

    by_operator = {}
    for r in rows:
        by_operator.setdefault(r["operator"], 0)
        by_operator[r["operator"]] += 1

    print(f"Catalogued {len(rows)} files.")
    for op, count in sorted(by_operator.items()):
        print(f"  {op}: {count}")
    unknown = [r for r in rows if r["operator"] == "UNKNOWN"]
    if unknown:
        print("\nUNKNOWN files (need manual review):")
        for r in unknown:
            print(f"  {r['original_filename']}: {r['detail']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
