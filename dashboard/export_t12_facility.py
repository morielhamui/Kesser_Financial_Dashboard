"""Export the full T12 waterfall + full GL-account detail (every line
item, not just Operating Expense) for the T12 by Facility dashboard
artifact -- one facility at a time, drilled all the way to the GL line.

Usage:
    python3 dashboard/export_t12_facility.py

Writes dashboard/t12_facility_data.json, embedded by build_t12_facility.py
into the published artifact -- run that next, then publish the resulting
dashboard/t12_facility.html via the Artifact tool.
"""
import json
import pathlib
import sqlite3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = pathlib.Path(__file__).resolve().parent

conn = sqlite3.connect(REPO_ROOT / "db" / "kesser_financials.sqlite3")
conn.row_factory = sqlite3.Row

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

# --- facilities ---
facilities = {}
for row in conn.execute("""
    SELECT f.facility_id, f.facility_name, f.brand, o.operator_name, l.landlord_name
    FROM dim_facility f
    JOIN dim_operator o ON o.operator_id = f.operator_id
    LEFT JOIN dim_landlord l ON l.landlord_id = f.landlord_id
    WHERE f.is_active = 1
"""):
    facilities[row["facility_id"]] = {
        "facility_id": row["facility_id"], "name": row["facility_name"],
        "manager": row["brand"], "operator": row["operator_name"],
        "landlord": row["landlord_name"] or "Unassigned",
    }

# --- department amounts (opex excl G&A + Management Fees), same as export_t12.py ---
dept_rows = conn.execute("""
    SELECT f.facility_id, f.period_date, f.source_file, m.category, SUM(f.amount) as amt
    FROM fact_tenant_financials f
    JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
    WHERE m.statement_type='opex' AND m.category NOT IN ('General and Administrative','Management Fees')
    GROUP BY f.facility_id, f.period_date, f.source_file, m.category
""").fetchall()
dept_map = {}
for r in dept_rows:
    key = (r["facility_id"], r["period_date"], r["source_file"])
    if key not in canon:
        continue
    fp = (r["facility_id"], r["period_date"])
    dept_map.setdefault(fp, {})[r["category"]] = round((dept_map.get(fp, {}).get(r["category"], 0) or 0) + r["amt"], 2)

# --- waterfall, straight from the already-validated metrics layer ---
waterfall = []
for r in conn.execute("SELECT * FROM fact_metrics_waterfall"):
    if r["facility_id"] not in facilities:
        continue
    fp = (r["facility_id"], r["period_date"])
    waterfall.append({
        "facility_id": r["facility_id"], "period": r["period_date"],
        "operating_revenue": round(r["operating_revenue"], 2),
        "operating_expense": round(r["operating_expense"], 2),
        "operating_income": round(r["operating_income"], 2),
        "ga": round(r["general_and_administrative"], 2),
        "ebitdarm": round(r["ebitdarm"], 2),
        "real_estate_tax": round(r["real_estate_tax"], 2),
        "ebidarm": round(r["ebidarm"], 2),
        "capital_expenses": round(r["capital_expenses_ex_ret"], 2),
        "earnings_before_mgmt_fees": round(r["earnings_before_management_fees"], 2),
        "management_fees": round(r["management_fees"], 2),
        "earnings": round(r["earnings"], 2),
        "other_income_expense": round(r["other_income_expense"], 2),
        "noi": round(r["noi"], 2),
        "departments": dept_map.get(fp, {}),
    })

# --- full GL-account detail, every line item (not just Operating Expense) ---
# line_key mirrors metrics/waterfall.py's compute_one() classification exactly,
# so "expand this waterfall row" always shows precisely the GL lines summed
# into it -- 'opex:<Department>' for each Operating Expense department (same
# grouping the departments dict above uses), plus one key per remaining
# top-line row (operating_revenue, ga, real_estate_tax, capital_expenses,
# management_fees, other_income_expense).
gl_sql = conn.execute("""
    SELECT f.facility_id, f.period_date, f.source_file, m.statement_type, m.category, m.detail, m.raw_account_label, SUM(f.amount) amt
    FROM fact_tenant_financials f JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
    GROUP BY f.facility_id, f.period_date, f.source_file, m.statement_type, m.category, m.detail, m.raw_account_label
""").fetchall()

labels, label_idx = [], {}
groups, group_idx = [], {}
periods_set = set()
gl = []

for r in gl_sql:
    key = (r["facility_id"], r["period_date"], r["source_file"])
    if key not in canon or r["facility_id"] not in facilities:
        continue

    st, cat, detail = r["statement_type"], r["category"], r["detail"]
    if st == "revenue" and (cat != "Other Income / Expense" or detail == "QIP"):
        line_key = "operating_revenue"
    elif st == "revenue" and cat == "Other Income / Expense":
        line_key = "other_income_expense"
    elif st == "opex" and cat == "General and Administrative":
        line_key = "ga"
    elif st == "opex" and cat == "Management Fees":
        line_key = "management_fees"
    elif st == "opex":
        line_key = "opex:" + cat
    elif st == "capital" and detail == "RE Tax":
        line_key = "real_estate_tax"
    elif st == "capital":
        line_key = "capital_expenses"
    else:
        continue

    label = r["raw_account_label"]
    if label not in label_idx:
        label_idx[label] = len(labels)
        labels.append(label)
    if line_key not in group_idx:
        group_idx[line_key] = len(groups)
        groups.append(line_key)
    periods_set.add(r["period_date"])
    gl.append([r["facility_id"], r["period_date"], group_idx[line_key], label_idx[label], round(r["amt"], 2)])

periods = sorted(periods_set)
period_idx = {p: i for i, p in enumerate(periods)}
gl_compact = [[fid, period_idx[p], gidx, lidx, amt] for fid, p, gidx, lidx, amt in gl]

out = {
    "facilities": list(facilities.values()),
    "periods": periods,
    "labels": labels,
    "groups": groups,
    "waterfall": waterfall,
    "gl": gl_compact,
}
out_path = OUT_DIR / "t12_facility_data.json"
with open(out_path, "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(f"facilities={len(facilities)} waterfall_rows={len(waterfall)} periods={len(periods)} labels={len(labels)} groups={len(groups)} gl={len(gl_compact)}")
print("size:", out_path.stat().st_size / 1024, "KB")
