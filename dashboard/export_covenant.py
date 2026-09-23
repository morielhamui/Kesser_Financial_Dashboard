"""Export EBIDAR + purchase price by landlord/brand package for the
Covenant & EBIDAR dashboard artifact.

Usage:
    python3 dashboard/export_covenant.py

Writes dashboard/covenant_data.json, embedded by build_covenant.py into
the published artifact -- run that next, then publish the resulting
dashboard/covenant.html via the Artifact tool.
"""
import json
import pathlib
import sqlite3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = pathlib.Path(__file__).resolve().parent

conn = sqlite3.connect(REPO_ROOT / "db" / "kesser_financials.sqlite3")
conn.row_factory = sqlite3.Row

# --- facilities (for filter chips) ---
facilities = {}
for row in conn.execute("""
    SELECT f.facility_id, f.facility_name, f.brand, l.landlord_id, l.landlord_name
    FROM dim_facility f
    LEFT JOIN dim_landlord l ON l.landlord_id = f.landlord_id
    WHERE f.is_active = 1
"""):
    facilities[row["facility_id"]] = {
        "facility_id": row["facility_id"], "name": row["facility_name"],
        "manager": row["brand"], "landlord": row["landlord_name"] or "Unassigned",
        "landlord_id": row["landlord_id"],
    }

# --- purchase price packages, keyed by (landlord_id, brand) ---
packages = []
package_facility_ids = {}  # (landlord_id, brand) -> [facility_id, ...]
for row in conn.execute("SELECT landlord_id, brand, purchase_price FROM fact_purchase_price"):
    key = (row["landlord_id"], row["brand"])
    fac_ids = [fid for fid, f in facilities.items() if f["landlord_id"] == row["landlord_id"] and f["manager"] == row["brand"]]
    package_facility_ids[key] = fac_ids
    landlord_name = next((f["landlord"] for f in facilities.values() if f["landlord_id"] == row["landlord_id"]), "Unknown")
    packages.append({
        "landlord_id": row["landlord_id"], "landlord": landlord_name, "brand": row["brand"],
        "purchase_price": row["purchase_price"], "facility_ids": fac_ids,
    })

# --- lease rent, landlord-level (migration 009) -- a COLLECTIVE test: the
# lease covenant sums Covenant Income (EBIDAR) across ALL of a landlord's
# operator brands and compares it to the ONE rent that landlord itself
# pays its own upstream owner (e.g. Petersen SNF -> CareTrust), NOT what
# it collects from its operators. Separate from purchase price -- "Lease
# Covenant" and "Cap Rate Supportable" are two distinct tests and must
# never be combined into one number. See PROJECT_RULES.md section 9a.
landlord_rents = []
for row in conn.execute("SELECT landlord_id, monthly_rent FROM fact_lease_rent"):
    fac_ids = [fid for fid, f in facilities.items() if f["landlord_id"] == row["landlord_id"]]
    landlord_name = next((f["landlord"] for f in facilities.values() if f["landlord_id"] == row["landlord_id"]), "Unknown")
    landlord_rents.append({
        "landlord_id": row["landlord_id"], "landlord": landlord_name,
        "monthly_rent": row["monthly_rent"], "facility_ids": fac_ids,
    })

# --- EBIDARM (and NOI, operating revenue) per facility/period, straight
# from the already-validated metrics/waterfall layer. EBIDARM is NOT the
# covenant metric itself -- the covenant "EBIDAR" subtracts a normalized
# management-fee add-back (5% of Operating Revenue, not the operator's
# actual reported management fee) from EBIDARM; that arithmetic happens
# client-side in build_covenant.py so operating_revenue needs to travel
# alongside ebidarm here. See PROJECT_RULES.md section 9a.
rows = []
for row in conn.execute("SELECT facility_id, period_date, ebidarm, noi, operating_revenue FROM fact_metrics_waterfall"):
    if row["facility_id"] not in facilities:
        continue
    rows.append({
        "facility_id": row["facility_id"], "period": row["period_date"],
        "ebidarm": round(row["ebidarm"], 2), "noi": round(row["noi"], 2),
        "operating_revenue": round(row["operating_revenue"], 2),
    })

out = {
    "facilities": list(facilities.values()),
    "packages": packages,
    "landlord_rents": landlord_rents,
    "rows": rows,
}
out_path = OUT_DIR / "covenant_data.json"
with open(out_path, "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(f"facilities={len(facilities)} packages={len(packages)} landlord_rents={len(landlord_rents)} rows={len(rows)}")
print("size:", out_path.stat().st_size / 1024, "KB")
