#!/usr/bin/env python3
"""Compare our calculated Medicaid PPD (revenue-by-payor / matching census
days, same methodology as the dashboard's Revenue PPD page) against
Illinois HFS's own published quarterly Medicaid rate, per facility per
quarter.

Compared against the traditional fee-for-service "Medicaid" payor bucket
only -- NOT "Managed Medicaid", since Medicaid MCOs negotiate their own
contracted rates and aren't bound to HFS's published FFS fee schedule, so
folding them in would compare against the wrong benchmark.

Usage:
    python3 scripts/compare_hfs_medicaid_rates.py [--db db/kesser_financials.sqlite3]
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sqlite3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "kesser_financials.sqlite3"

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--tolerance-pct", type=float, default=10.0)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    canon = set()
    for r in conn.execute(
        """
        WITH file_anchor AS (SELECT source_file, MAX(period_date) AS anchor FROM fact_reported_net_income GROUP BY source_file),
        candidates AS (SELECT r.facility_id, r.period_date, r.source_file, fa.anchor FROM fact_reported_net_income r JOIN file_anchor fa ON fa.source_file=r.source_file),
        ranked AS (SELECT facility_id, period_date, source_file, ROW_NUMBER() OVER (PARTITION BY facility_id, period_date ORDER BY anchor DESC, source_file DESC) rn FROM candidates)
        SELECT facility_id, period_date, source_file FROM ranked WHERE rn=1
        """
    ):
        canon.add((r["facility_id"], r["period_date"], r["source_file"]))

    quarters = sorted(
        r[0] for r in conn.execute("SELECT DISTINCT effective_date FROM fact_hfs_rates").fetchall()
    )

    facilities = conn.execute(
        "SELECT facility_id, facility_name, brand, hfs_building_id FROM dim_facility WHERE hfs_building_id IS NOT NULL ORDER BY facility_name"
    ).fetchall()

    financial_rows = conn.execute(
        """
        SELECT f.facility_id, f.period_date, f.source_file, m.detail, SUM(f.amount) amt
        FROM fact_tenant_financials f JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
        WHERE m.statement_type = 'revenue' AND m.category != 'Other Income / Expense'
        GROUP BY f.facility_id, f.period_date, f.source_file, m.detail
        """
    ).fetchall()
    census_rows = conn.execute(
        "SELECT facility_id, period_date, source_file, payor, SUM(resident_days) d FROM fact_census GROUP BY facility_id, period_date, source_file, payor"
    ).fetchall()

    medicaid_rev = {}  # (facility_id, period) -> $
    for r in financial_rows:
        key = (r["facility_id"], r["period_date"], r["source_file"])
        if key not in canon or norm_payor(r["detail"]) != "Medicaid":
            continue
        fp = (r["facility_id"], r["period_date"])
        medicaid_rev[fp] = medicaid_rev.get(fp, 0.0) + r["amt"]

    medicaid_days = {}  # (facility_id, period) -> days
    for r in census_rows:
        key = (r["facility_id"], r["period_date"], r["source_file"])
        if key not in canon or norm_payor(r["payor"]) != "Medicaid":
            continue
        fp = (r["facility_id"], r["period_date"])
        medicaid_days[fp] = medicaid_days.get(fp, 0.0) + (r["d"] or 0.0)

    results = []
    for fac in facilities:
        fid = fac["facility_id"]
        for q in quarters:
            q_end = add_months(q, 3)
            hfs_row = conn.execute(
                "SELECT rate_amount FROM fact_hfs_rates WHERE facility_id=? AND effective_date=? AND rate_component='Total'",
                (fid, q),
            ).fetchone()
            if hfs_row is None:
                continue
            hfs_rate = hfs_row[0]

            periods_in_q = sorted(p for (f, p) in medicaid_rev if f == fid and q <= p < q_end)
            rev = sum(medicaid_rev.get((fid, p), 0.0) for p in periods_in_q)
            days = sum(medicaid_days.get((fid, p), 0.0) for p in periods_in_q)
            our_rate = rev / days if days > 0 else None

            results.append({
                "facility": fac["facility_name"], "brand": fac["brand"], "quarter": q,
                "our_rate": our_rate, "hfs_rate": hfs_rate,
                "diff": (our_rate - hfs_rate) if our_rate is not None else None,
                "pct": ((our_rate - hfs_rate) / hfs_rate * 100) if our_rate else None,
                "days": days,
            })

    with_data = [r for r in results if r["our_rate"] is not None]
    no_data = [r for r in results if r["our_rate"] is None]

    print(f"Comparisons with both our rate and HFS rate: {len(with_data)}")
    print(f"Comparisons where we have no Medicaid census/revenue that quarter: {len(no_data)}")
    print()

    within_tol = [r for r in with_data if abs(r["pct"]) <= args.tolerance_pct]
    outside_tol = [r for r in with_data if abs(r["pct"]) > args.tolerance_pct]
    print(f"Within +/-{args.tolerance_pct:.0f}%: {len(within_tol)} of {len(with_data)} ({100*len(within_tol)/len(with_data):.1f}%)")
    print()

    pcts = sorted(r["pct"] for r in with_data)
    n = len(pcts)
    median_pct = pcts[n // 2] if n % 2 else (pcts[n // 2 - 1] + pcts[n // 2]) / 2
    print(f"Median variance: {median_pct:+.1f}%")
    print(f"Mean variance: {sum(pcts)/n:+.1f}%")
    print()

    print(f"--- Largest {min(15, len(outside_tol))} variances (outside +/-{args.tolerance_pct:.0f}%) ---")
    for r in sorted(outside_tol, key=lambda x: -abs(x["pct"]))[:15]:
        print(f"  {r['facility']:38s} {r['quarter']}  ours=${r['our_rate']:7.2f}  hfs=${r['hfs_rate']:7.2f}  diff={r['pct']:+7.1f}%  (days={r['days']:.0f})")

    print()
    print("--- Sample within tolerance ---")
    for r in within_tol[:10]:
        print(f"  {r['facility']:38s} {r['quarter']}  ours=${r['our_rate']:7.2f}  hfs=${r['hfs_rate']:7.2f}  diff={r['pct']:+7.1f}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
