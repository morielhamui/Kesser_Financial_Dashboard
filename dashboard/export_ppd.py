"""Export revenue/expense-by-payor-and-department + GL detail to JSON for
the Revenue & Expense PPD dashboard artifact.

Usage:
    python3 dashboard/export_ppd.py

Writes dashboard/ppd_data.json, embedded by build_ppd.py into the
published artifact -- run that next, then publish the resulting
dashboard/ppd.html via the Artifact tool.
"""
import sqlite3, json, pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
SCRATCH = pathlib.Path(__file__).resolve().parent
conn = sqlite3.connect(REPO / "db" / "kesser_financials.sqlite3")
conn.row_factory = sqlite3.Row

# Canonical payor vocabulary shared by BOTH the revenue side (dim_account_
# mapping.detail -- which for Allure equals its own category, since Allure
# has no "Resident Income" wrapper and names each payor as its own top-level
# category) and the census side (fact_census.payor). The two sides use
# different spellings for the same payor (e.g. revenue's "Insurance/
# Commerical" typo vs census's "Commercial Insurance"), so a Medicare $
# figure can only be divided by Medicare census days if both are folded to
# the same key first -- otherwise every payor row silently falls back to
# matching nothing. Extends PROJECT_RULES.md section 5's PAYOR_ALIASES
# table with the extra variants Aliya/Allure use (not covered by the
# master-mapping census alias table, which only covers the other 5
# operators).
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

# Revenue lines with no matching census payor bucket at all (Allure blends
# Medicare and its managed-care book into one category; a few lump-sum
# payments aren't payor-attributable) -- these fold into "Other" and can
# only ever use blended (whole-facility) days, never a payor-matched
# denominator, because no such census breakdown exists to match against.
def norm_payor(raw):
    d = (raw or "Other").strip()
    return PAYOR_CANON.get(d.lower(), d if d else "Other")

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
    SELECT f.facility_id, f.facility_name, f.brand, o.operator_name, l.landlord_name, f.is_active
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

# --- census: resident days per facility/period, both total AND by payor ---
# Census tabs live in the SAME workbooks as the financials (same source_file
# names), which overlap across rolling T12 exports -- e.g. Tuscola/Arcola
# each have a dozen+ monthly T12 files that all cover the same historical
# months. Without restricting to the one canonical source_file per
# facility/period (the same de-dup already used for the financials), those
# months get summed 12-13x over, wildly inflating resident-days and
# understating every PPD figure that depends on it.
census_days = {}          # (facility_id, period) -> total days, all payors
census_days_by_payor = {} # (facility_id, period) -> {canonical_payor: days}
for row in conn.execute("SELECT facility_id, period_date, source_file, payor, SUM(resident_days) d FROM fact_census GROUP BY facility_id, period_date, source_file, payor"):
    key = (row["facility_id"], row["period_date"], row["source_file"])
    if key not in canon:
        continue
    fp = (row["facility_id"], row["period_date"])
    d = row["d"] or 0.0
    census_days[fp] = census_days.get(fp, 0.0) + d
    payor = norm_payor(row["payor"])
    bucket = census_days_by_payor.setdefault(fp, {})
    bucket[payor] = bucket.get(payor, 0.0) + d

# --- department (opex) $ totals per facility/period ---
dept_sql = conn.execute("""
    SELECT f.facility_id, f.period_date, f.source_file, m.category, SUM(f.amount) amt
    FROM fact_tenant_financials f JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
    WHERE m.statement_type = 'opex' AND m.category NOT IN ('General and Administrative', 'Management Fees')
    GROUP BY f.facility_id, f.period_date, f.source_file, m.category
""").fetchall()

# --- payor (revenue) $ totals per facility/period ---
# Every payor-attributable revenue row, keyed by `detail` -- which holds the
# actual payor name (Medicaid, Medicare, Private, ...) for the master-mapped
# operators' "Resident Income"/"Ancillary" categories, AND for Allure, whose
# parser sets detail equal to its own category since it has no "Resident
# Income" wrapper (e.g. category="Medicare A", detail="Medicare A"). Only
# exclusion is the "Other Income / Expense" catch-all (grants, interest
# income, QIP, vaccines, etc.) -- same rule metrics/waterfall.py uses for
# Operating Revenue, so this total reconciles with that page's definition
# minus QIP (QIP isn't payor-attributable, so it's out of scope for a
# by-payor PPD view).
payor_sql = conn.execute("""
    SELECT f.facility_id, f.period_date, f.source_file, m.detail, SUM(f.amount) amt
    FROM fact_tenant_financials f JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
    WHERE m.statement_type = 'revenue' AND m.category != 'Other Income / Expense'
    GROUP BY f.facility_id, f.period_date, f.source_file, m.detail
""").fetchall()

rows_map = {}  # (facility_id, period) -> {expense_by_dept: {}, revenue_by_payor: {}}
for r in dept_sql:
    key = (r["facility_id"], r["period_date"], r["source_file"])
    if key not in canon:
        continue
    bucket = rows_map.setdefault((r["facility_id"], r["period_date"]), {"expense_by_dept": {}, "revenue_by_payor": {}})
    bucket["expense_by_dept"][r["category"]] = bucket["expense_by_dept"].get(r["category"], 0.0) + r["amt"]

for r in payor_sql:
    key = (r["facility_id"], r["period_date"], r["source_file"])
    if key not in canon:
        continue
    bucket = rows_map.setdefault((r["facility_id"], r["period_date"]), {"expense_by_dept": {}, "revenue_by_payor": {}})
    payor = norm_payor(r["detail"])
    bucket["revenue_by_payor"][payor] = bucket["revenue_by_payor"].get(payor, 0.0) + r["amt"]

rows = []
for (facility_id, period), bucket in rows_map.items():
    if facility_id not in facilities:
        continue
    expense_total = round(sum(bucket["expense_by_dept"].values()), 2)
    revenue_total = round(sum(bucket["revenue_by_payor"].values()), 2)
    rows.append({
        "facility_id": facility_id,
        "period": period,
        "resident_days": round(census_days.get((facility_id, period), 0.0), 1),
        "resident_days_by_payor": {k: round(v, 1) for k, v in census_days_by_payor.get((facility_id, period), {}).items()},
        "expense_total": expense_total,
        "expense_by_dept": {k: round(v, 2) for k, v in bucket["expense_by_dept"].items()},
        "revenue_total": revenue_total,
        "revenue_by_payor": {k: round(v, 2) for k, v in bucket["revenue_by_payor"].items()},
    })

# --- GL-account-level detail (for the drill-down), same opex/revenue scope ---
gl_sql = conn.execute("""
    SELECT f.facility_id, f.period_date, f.source_file, m.statement_type, m.category, m.detail, m.raw_account_label, SUM(f.amount) amt
    FROM fact_tenant_financials f JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
    WHERE (m.statement_type = 'opex' AND m.category NOT IN ('General and Administrative', 'Management Fees'))
       OR (m.statement_type = 'revenue' AND m.category != 'Other Income / Expense')
    GROUP BY f.facility_id, f.period_date, f.source_file, m.statement_type, m.category, m.detail, m.raw_account_label
""").fetchall()

labels = []
label_idx = {}
groups = []
group_idx = {}
periods_set = set()
gl = []

for r in gl_sql:
    key = (r["facility_id"], r["period_date"], r["source_file"])
    if key not in canon or r["facility_id"] not in facilities:
        continue
    label = r["raw_account_label"]
    if label not in label_idx:
        label_idx[label] = len(labels)
        labels.append(label)
    if r["statement_type"] == "opex":
        group = "E:" + r["category"]
    else:
        group = "R:" + norm_payor(r["detail"])
    if group not in group_idx:
        group_idx[group] = len(groups)
        groups.append(group)
    periods_set.add(r["period_date"])
    gl.append([r["facility_id"], r["period_date"], group_idx[group], label_idx[label], round(r["amt"], 2)])

periods = sorted(periods_set)
period_idx = {p: i for i, p in enumerate(periods)}
gl_compact = [[fid, period_idx[p], gidx, lidx, amt] for fid, p, gidx, lidx, amt in gl]

out = {
    "facilities": list(facilities.values()),
    "periods": periods,
    "labels": labels,
    "groups": groups,
    "rows": rows,
    "gl": gl_compact,
}

out_path = SCRATCH / "ppd_data.json"
with open(out_path, "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(f"facilities={len(facilities)} rows={len(rows)} periods={len(periods)} labels={len(labels)} groups={len(groups)} gl={len(gl_compact)}")
print("size:", out_path.stat().st_size / 1024, "KB")
