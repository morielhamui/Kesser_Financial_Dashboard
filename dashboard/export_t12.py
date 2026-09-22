"""Export fact_metrics_waterfall (+ department breakdown) to JSON for the
T12 P&L Waterfall dashboard artifact.

Usage:
    python3 dashboard/export_t12.py

Writes dashboard/t12_data.json, embedded by build_t12.py into the
published artifact -- run that next, then publish the resulting
dashboard/t12_waterfall.html via the Artifact tool.
"""
import json
import pathlib
import sqlite3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = pathlib.Path(__file__).resolve().parent

conn = sqlite3.connect(REPO_ROOT / "db" / "kesser_financials.sqlite3")
conn.row_factory = sqlite3.Row

facilities = {}
for row in conn.execute("""
    SELECT f.facility_id, f.facility_name, f.brand, o.operator_name, l.landlord_name, f.is_active
    FROM dim_facility f
    JOIN dim_operator o ON o.operator_id = f.operator_id
    LEFT JOIN dim_landlord l ON l.landlord_id = f.landlord_id
    WHERE f.is_active = 1
"""):
    facilities[row['facility_id']] = {
        'facility_id': row['facility_id'],
        'name': row['facility_name'],
        'manager': row['brand'],
        'operator': row['operator_name'],
        'landlord': row['landlord_name'] or 'Unassigned',
    }

# department amounts (opex excl G&A + Management Fees)
dept_rows = conn.execute("""
    SELECT f.facility_id, f.period_date, m.category, SUM(f.amount) as amt
    FROM fact_tenant_financials f
    JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
    JOIN fact_metrics_waterfall w ON w.facility_id=f.facility_id AND w.period_date=f.period_date AND w.source_file=f.source_file
    WHERE m.statement_type='opex' AND m.category NOT IN ('General and Administrative','Management Fees')
    GROUP BY f.facility_id, f.period_date, m.category
""").fetchall()

dept_map = {}
for r in dept_rows:
    key = (r['facility_id'], r['period_date'])
    dept_map.setdefault(key, {})[r['category']] = round(r['amt'], 2)

waterfall = []
for r in conn.execute("SELECT * FROM fact_metrics_waterfall"):
    key = (r['facility_id'], r['period_date'])
    if r['facility_id'] not in facilities:
        continue
    waterfall.append({
        'facility_id': r['facility_id'],
        'period': r['period_date'],
        'operating_revenue': round(r['operating_revenue'], 2),
        'operating_expense': round(r['operating_expense'], 2),
        'operating_income': round(r['operating_income'], 2),
        'ga': round(r['general_and_administrative'], 2),
        'ebitdarm': round(r['ebitdarm'], 2),
        'real_estate_tax': round(r['real_estate_tax'], 2),
        'ebidarm': round(r['ebidarm'], 2),
        'capital_expenses': round(r['capital_expenses_ex_ret'], 2),
        'earnings_before_mgmt_fees': round(r['earnings_before_management_fees'], 2),
        'management_fees': round(r['management_fees'], 2),
        'earnings': round(r['earnings'], 2),
        'other_income_expense': round(r['other_income_expense'], 2),
        'noi': round(r['noi'], 2),
        'departments': dept_map.get(key, {}),
    })

out = {
    'facilities': list(facilities.values()),
    'waterfall': waterfall,
}
out_path = OUT_DIR / "t12_data.json"
with open(out_path, 'w') as f:
    json.dump(out, f, separators=(',', ':'))

print('facilities:', len(facilities))
print('waterfall rows:', len(waterfall))
print('json size KB:', out_path.stat().st_size / 1024)
