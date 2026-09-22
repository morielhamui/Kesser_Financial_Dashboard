"""Export census-by-payor, occupancy inputs, and the HFS Medicaid rate
comparison to JSON for the Census dashboard artifact.

Usage:
    python3 dashboard/export_census.py

Writes dashboard/census_data.json, embedded by build_census.py into the
published artifact -- run that next, then publish the resulting
dashboard/census.html via the Artifact tool.
"""
import json
import pathlib
import sqlite3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = pathlib.Path(__file__).resolve().parent

conn = sqlite3.connect(REPO_ROOT / "db" / "kesser_financials.sqlite3")
conn.row_factory = sqlite3.Row

# Same canonical payor vocabulary as the PPD export (PROJECT_RULES.md
# section 5) -- shared here so a payor's census mix % lines up with how
# it's labeled on the Revenue PPD page.
PAYOR_CANON = {
    "medicaid": "Medicaid", "medicaid pending": "Medicaid",
    "managed medicaid": "Managed Medicaid", "medicaid mmai": "Managed Medicaid",
    "medicare": "Medicare", "medicare a": "Medicare",
    "managed medicare": "Managed Medicare", "medicare advantage": "Managed Medicare", "medicare mmai": "Managed Medicare",
    "medicare b": "Medicare B",
    "private": "Private", "private pay": "Private",
    "insurance/commercial": "Insurance/Commercial", "insurance/commerical": "Insurance/Commercial",
    "insurance - commercial": "Insurance/Commercial", "insurance": "Insurance/Commercial",
    "commercial insurance": "Insurance/Commercial",
    "veterans": "Veterans", "veteran affairs": "Veterans",
    "hospice": "Hospice",
    "assisted living": "Assisted Living",
    "independent living": "Independent Living", "private pay independent living": "Independent Living",
}


def norm_payor(raw):
    d = (raw or "Other").strip()
    return PAYOR_CANON.get(d.lower(), d if d else "Other")


def add_months(date_str: str, months: int) -> str:
    y, m, d = (int(x) for x in date_str.split("-"))
    m0 = m - 1 + months
    y += m0 // 12
    m = m0 % 12 + 1
    return f"{y:04d}-{m:02d}-{d:02d}"


# --- canonical facility-period-source, same de-dup rule as metrics/waterfall.py ---
canon_rows = conn.execute("""
    WITH file_anchor AS (
        SELECT source_file, MAX(period_date) AS anchor
        FROM fact_reported_net_income GROUP BY source_file
    ),
    candidates AS (
        SELECT r.facility_id, r.period_date, r.source_file, fa.anchor
        FROM fact_reported_net_income r JOIN file_anchor fa ON fa.source_file = r.source_file
    ),
    ranked AS (
        SELECT facility_id, period_date, source_file,
               ROW_NUMBER() OVER (PARTITION BY facility_id, period_date ORDER BY anchor DESC, source_file DESC) AS rn
        FROM candidates
    )
    SELECT facility_id, period_date, source_file FROM ranked WHERE rn = 1
""").fetchall()
canon = set((r["facility_id"], r["period_date"], r["source_file"]) for r in canon_rows)
reported_source_files = set(r[0] for r in conn.execute("SELECT DISTINCT source_file FROM fact_reported_net_income"))

# --- facilities ---
facilities = {}
for row in conn.execute("""
    SELECT f.facility_id, f.facility_name, f.brand, o.operator_name, l.landlord_name, f.total_beds
    FROM dim_facility f
    JOIN dim_operator o ON o.operator_id = f.operator_id
    LEFT JOIN dim_landlord l ON l.landlord_id = f.landlord_id
    WHERE f.is_active = 1
"""):
    facilities[row["facility_id"]] = {
        "facility_id": row["facility_id"], "name": row["facility_name"],
        "manager": row["brand"], "operator": row["operator_name"],
        "landlord": row["landlord_name"] or "Unassigned",
        "total_beds": row["total_beds"],
    }

# --- census by payor per facility/period, canonical-source filtered ---
# Exception: Lincoln/Lineage's census comes from a standalone historical
# backfill file (db/seed/load_lincoln_lineage_census.py) with no
# corresponding P&L workbook, so it never appears in fact_reported_net_income
# and can never match `canon` -- there's also no overlapping T12 export to
# dedupe against, so a source_file with zero rows in fact_reported_net_income
# at all is let through unfiltered rather than being silently dropped.
census_by_fp: dict[tuple, dict[str, float]] = {}
for row in conn.execute("SELECT facility_id, period_date, source_file, payor, SUM(resident_days) d FROM fact_census GROUP BY facility_id, period_date, source_file, payor"):
    key = (row["facility_id"], row["period_date"], row["source_file"])
    if row["facility_id"] not in facilities:
        continue
    if row["source_file"] in reported_source_files and key not in canon:
        continue
    fp = (row["facility_id"], row["period_date"])
    payor = norm_payor(row["payor"])
    bucket = census_by_fp.setdefault(fp, {})
    bucket[payor] = bucket.get(payor, 0.0) + (row["d"] or 0.0)

rows = []
periods_set = set()
for (facility_id, period), by_payor in census_by_fp.items():
    periods_set.add(period)
    rows.append({
        "facility_id": facility_id,
        "period": period,
        "resident_days": round(sum(by_payor.values()), 1),
        "census_by_payor": {k: round(v, 1) for k, v in by_payor.items()},
    })
periods = sorted(periods_set)

# --- HFS Medicaid rate comparison (same methodology as
#     scripts/compare_hfs_medicaid_rates.py) -- Medicaid FFS payor only,
#     never Managed Medicaid, since MCOs negotiate their own rates. ---
medicaid_rev: dict[tuple, float] = {}
for row in conn.execute("""
    SELECT f.facility_id, f.period_date, f.source_file, m.detail, SUM(f.amount) amt
    FROM fact_tenant_financials f JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
    WHERE m.statement_type = 'revenue' AND m.category != 'Other Income / Expense'
    GROUP BY f.facility_id, f.period_date, f.source_file, m.detail
"""):
    key = (row["facility_id"], row["period_date"], row["source_file"])
    if key not in canon or norm_payor(row["detail"]) != "Medicaid":
        continue
    fp = (row["facility_id"], row["period_date"])
    medicaid_rev[fp] = medicaid_rev.get(fp, 0.0) + row["amt"]

medicaid_days: dict[tuple, float] = {}
for (facility_id, period), by_payor in census_by_fp.items():
    if "Medicaid" in by_payor:
        medicaid_days[(facility_id, period)] = by_payor["Medicaid"]

hfs_quarters = sorted(r[0] for r in conn.execute("SELECT DISTINCT effective_date FROM fact_hfs_rates").fetchall())

hfs_compare = []
for facility_id in facilities:
    for q in hfs_quarters:
        q_end = add_months(q, 3)
        hfs_row = conn.execute(
            "SELECT rate_amount FROM fact_hfs_rates WHERE facility_id=? AND effective_date=? AND rate_component='Total'",
            (facility_id, q),
        ).fetchone()
        if hfs_row is None:
            continue
        periods_in_q = [p for p in periods if q <= p < q_end]
        rev = sum(medicaid_rev.get((facility_id, p), 0.0) for p in periods_in_q)
        days = sum(medicaid_days.get((facility_id, p), 0.0) for p in periods_in_q)
        hfs_compare.append({
            "facility_id": facility_id,
            "quarter": q,
            "hfs_rate": round(hfs_row[0], 2),
            "our_rate": round(rev / days, 2) if days > 0 else None,
        })

out = {
    "facilities": list(facilities.values()),
    "periods": periods,
    "rows": rows,
    "hfs_quarters": hfs_quarters,
    "hfs_compare": hfs_compare,
}
out_path = OUT_DIR / "census_data.json"
with open(out_path, "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(f"facilities={len(facilities)} rows={len(rows)} periods={len(periods)} hfs_compare={len(hfs_compare)}")
print("size:", out_path.stat().st_size / 1024, "KB")
