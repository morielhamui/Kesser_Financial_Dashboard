"""Standing validation module (PROJECT_RULES.md section 6).

Runs after every load. For a given facility/period/source_file, sums the
mapped fact_tenant_financials rows by statement_type and recomputes:

    Net Income = Revenue - Operating Expense - Capital Expenses

This is the exact 3-term formula from the master account mapping's own
README ("Validation standard") and PROJECT_RULES.md section 6. It works
because "Operating Expense" here is the BROAD grouping bucket -- it
includes G&A, Management Fees, and (for Curis) Nursing Home Fee, not just
department-level opex -- and "Revenue" includes the Other Income/Expense
section (Interest Income, QIP, CNA Incentive, etc.), not just resident
income by payor. This matches operator statements' own arithmetic
exactly; a narrower "Operating Expense" (excluding G&A/Management Fees)
is a separate, later concept used only by the metrics/waterfall layer,
computed from the same rows via category/sub_group filters -- it is not
what this validation gate checks.

This must match fact_reported_net_income within $50, or the mismatch is
written to exceptions_log and the period is NOT considered loaded (callers
should treat a failed validation as a load failure and surface it -- this
module never silently drops the exception).

statement_type values used across parsers (== master mapping's Grouping):
    revenue   - resident income by payor + all Other Income/Expense items
    opex      - every department (Nursing, Dietary, Ancillary, G&A,
                Management Fees, Marketing, ...) -- the broad bucket
    capital   - Rent, RE Tax, Interest, Depreciation, Amortization, ...
"""
from __future__ import annotations

import sqlite3

TOLERANCE = 50.0


def recompute_net_income(conn: sqlite3.Connection, facility_id: int, period_date: str, source_file: str) -> float:
    row = conn.execute(
        """
        SELECT m.statement_type, SUM(f.amount)
        FROM fact_tenant_financials f
        JOIN dim_account_mapping m ON m.mapping_id = f.mapping_id
        WHERE f.facility_id = ? AND f.period_date = ? AND f.source_file = ?
        GROUP BY m.statement_type
        """,
        (facility_id, period_date, source_file),
    ).fetchall()
    totals = {statement_type: total or 0.0 for statement_type, total in row}

    revenue = totals.get("revenue", 0.0)
    opex = totals.get("opex", 0.0)
    capital = totals.get("capital", 0.0)

    return revenue - opex - capital


def validate_facility_period(
    conn: sqlite3.Connection,
    facility_id: int,
    period_date: str,
    source_file: str,
    load_batch_id: str,
) -> tuple[bool, float, float]:
    """Returns (passed, recomputed_ni, reported_ni). Writes exceptions_log on failure."""
    reported_row = conn.execute(
        "SELECT reported_net_income FROM fact_reported_net_income "
        "WHERE facility_id = ? AND period_date = ? AND source_file = ?",
        (facility_id, period_date, source_file),
    ).fetchone()
    if reported_row is None:
        conn.execute(
            """
            INSERT INTO exceptions_log
                (facility_id, period_date, source_file, load_batch_id, exception_type, detail)
            VALUES (?, ?, ?, ?, 'missing_reported_net_income', 'No reported Net Income row found for this facility/period/source_file')
            """,
            (facility_id, period_date, source_file, load_batch_id),
        )
        return False, float("nan"), float("nan")

    reported_ni = reported_row[0]
    recomputed_ni = recompute_net_income(conn, facility_id, period_date, source_file)
    diff = recomputed_ni - reported_ni
    passed = abs(diff) <= TOLERANCE

    if not passed:
        conn.execute(
            """
            INSERT INTO exceptions_log
                (facility_id, period_date, source_file, load_batch_id, exception_type, detail)
            VALUES (?, ?, ?, ?, 'net_income_mismatch', ?)
            """,
            (
                facility_id,
                period_date,
                source_file,
                load_batch_id,
                f"recomputed={recomputed_ni:.2f} reported={reported_ni:.2f} diff={diff:.2f} (tolerance={TOLERANCE})",
            ),
        )

    return passed, recomputed_ni, reported_ni
