"""Metrics / waterfall layer (PROJECT_RULES.md section 7).

Computes, per facility-period, the business metrics used to assess a
tenant's ability to pay rent:

    Operating Revenue                = Resident Income + Ancillary + QIP
    Operating Expense                = all department sub-groups except
                                        G&A and Management Fees (includes
                                        Evercare's opex-side "Other Income
                                        / Expense" sub-group, per rule)
    Operating Income                 = Operating Revenue - Operating Expense
    EBITDARM                         = Operating Income - G&A
    EBIDARM                          = EBITDARM - Real Estate Tax
    Earnings before Management Fees  = EBIDARM - Capital Expenses (ex RE Tax)
    Earnings                         = Earnings before Mgmt Fees - Mgmt Fees
    NOI                              = Earnings + Other Income/Expense
                                        (excluding QIP -- already counted
                                        in Operating Revenue)

This is a DIFFERENT, narrower "Operating Expense" than the broad
statement_type="opex" bucket the validation module sums (see
validation/validate.py's module docstring) -- it excludes G&A and
Management Fees, which the broad bucket includes. Both are computed from
the same underlying fact_tenant_financials rows via category/detail
filters; nothing here re-parses source files.

Every raw file loaded so far passed Net Income validation to the dollar,
so there is no additional pass/fail gate here -- this module only
reshapes already-validated facts into the waterfall's line items.

De-duplication: several operators' files cover overlapping trailing
periods (T12-style exports). For a given facility/period, the canonical
source_file is the one whose own anchor period (the latest period_date
it reports, taken from fact_reported_net_income) is the most recent --
i.e. prefer the freshest available report for that historical period,
since later re-pulls are more likely to carry corrections/reclassifications
than the original submission. Ties broken by source_file name for
determinism.
"""
from __future__ import annotations

import sqlite3

# Categories that make up "Operating Revenue" per the formula above.
# QIP is identified by detail, not category, since it's tagged
# category="Other Income / Expense", detail="QIP" across operators.
_REVENUE_CATEGORIES_IN_OPERATING = ("Resident Income", "Ancillary")


def pick_canonical_source(conn: sqlite3.Connection) -> list[tuple[int, str, str]]:
    """Returns [(facility_id, period_date, source_file), ...] -- the one
    canonical source_file to use per facility/period, per the
    de-duplication rule in this module's docstring.
    """
    rows = conn.execute(
        """
        WITH file_anchor AS (
            SELECT source_file, MAX(period_date) AS anchor
            FROM fact_reported_net_income
            GROUP BY source_file
        ),
        candidates AS (
            SELECT r.facility_id, r.period_date, r.source_file, fa.anchor
            FROM fact_reported_net_income r
            JOIN file_anchor fa ON fa.source_file = r.source_file
        ),
        ranked AS (
            SELECT facility_id, period_date, source_file,
                   ROW_NUMBER() OVER (
                       PARTITION BY facility_id, period_date
                       ORDER BY anchor DESC, source_file DESC
                   ) AS rn
            FROM candidates
        )
        SELECT facility_id, period_date, source_file FROM ranked WHERE rn = 1
        """
    ).fetchall()
    return rows


def _sum(conn, facility_id, period_date, source_file, where_sql, params=()):
    row = conn.execute(
        f"""
        SELECT COALESCE(SUM(f.amount), 0)
        FROM fact_tenant_financials f
        JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
        WHERE f.facility_id = ? AND f.period_date = ? AND f.source_file = ? AND ({where_sql})
        """,
        (facility_id, period_date, source_file, *params),
    ).fetchone()
    return row[0] or 0.0


def compute_one(conn: sqlite3.Connection, facility_id: int, period_date: str, source_file: str) -> dict:
    revenue_ancillary_resident = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'revenue' AND m.category IN (?, ?)",
        _REVENUE_CATEGORIES_IN_OPERATING,
    )
    qip = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'revenue' AND m.detail = 'QIP'",
    )
    operating_revenue = revenue_ancillary_resident + qip

    operating_expense = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'opex' AND m.category NOT IN ('General and Administrative', 'Management Fees')",
    )
    ga = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'opex' AND m.category = 'General and Administrative'",
    )
    management_fees = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'opex' AND m.category = 'Management Fees'",
    )
    real_estate_tax = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'capital' AND m.detail = 'RE Tax'",
    )
    capital_ex_ret = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'capital' AND (m.detail IS NULL OR m.detail != 'RE Tax')",
    )
    other_income_expense = _sum(
        conn, facility_id, period_date, source_file,
        "m.statement_type = 'revenue' AND m.category = 'Other Income / Expense' AND (m.detail IS NULL OR m.detail != 'QIP')",
    )

    operating_income = operating_revenue - operating_expense
    ebitdarm = operating_income - ga
    ebidarm = ebitdarm - real_estate_tax
    earnings_before_mgmt_fees = ebidarm - capital_ex_ret
    earnings = earnings_before_mgmt_fees - management_fees
    noi = earnings + other_income_expense

    return {
        "facility_id": facility_id,
        "period_date": period_date,
        "source_file": source_file,
        "operating_revenue": operating_revenue,
        "operating_expense": operating_expense,
        "operating_income": operating_income,
        "general_and_administrative": ga,
        "ebitdarm": ebitdarm,
        "real_estate_tax": real_estate_tax,
        "ebidarm": ebidarm,
        "capital_expenses_ex_ret": capital_ex_ret,
        "earnings_before_management_fees": earnings_before_mgmt_fees,
        "management_fees": management_fees,
        "earnings": earnings,
        "other_income_expense": other_income_expense,
        "noi": noi,
    }


def compute_and_store_all(conn: sqlite3.Connection) -> int:
    conn.execute("DELETE FROM fact_metrics_waterfall")
    targets = pick_canonical_source(conn)
    for facility_id, period_date, source_file in targets:
        m = compute_one(conn, facility_id, period_date, source_file)
        conn.execute(
            """
            INSERT INTO fact_metrics_waterfall
                (facility_id, period_date, source_file, operating_revenue, operating_expense,
                 operating_income, general_and_administrative, ebitdarm, real_estate_tax, ebidarm,
                 capital_expenses_ex_ret, earnings_before_management_fees, management_fees,
                 earnings, other_income_expense, noi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                m["facility_id"], m["period_date"], m["source_file"], m["operating_revenue"],
                m["operating_expense"], m["operating_income"], m["general_and_administrative"],
                m["ebitdarm"], m["real_estate_tax"], m["ebidarm"], m["capital_expenses_ex_ret"],
                m["earnings_before_management_fees"], m["management_fees"], m["earnings"],
                m["other_income_expense"], m["noi"],
            ),
        )
    conn.commit()
    return len(targets)


def main():
    import os

    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "kesser_financials.sqlite3")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    n = compute_and_store_all(conn)
    print(f"Computed metrics for {n} facility-periods.")
    conn.close()


if __name__ == "__main__":
    main()
