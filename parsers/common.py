"""Shared helpers for all operator parsers.

See PROJECT_RULES.md for the business rules these implement:
  - section 5 (payor alias consolidation, incl. operator-specific hospice folds)
  - section 6 (validation gate)
  - section 9/10 (schema, parser responsibilities)
"""
from __future__ import annotations

import datetime
import re
import sqlite3
import uuid
from dataclasses import dataclass, field

# ---------------------------------------------------------------------
# Workbook loading
# ---------------------------------------------------------------------


def load_workbook_any(path, data_only=True):
    """Open an .xlsx/.xlsm/.xls file with openpyxl.

    Several source files here use a ".xls" extension but are actually
    zip-based xlsx content. openpyxl's own extension check rejects ".xls"
    outright, so we pass a file object (which bypasses that check) rather
    than the path.
    """
    import openpyxl

    fh = open(path, "rb")
    try:
        return openpyxl.load_workbook(fh, data_only=data_only)
    finally:
        fh.close()


# ---------------------------------------------------------------------
# Payor alias consolidation (PROJECT_RULES.md section 5)
# ---------------------------------------------------------------------

PAYOR_ALIASES = {
    "insurance/commerical": "Insurance/Commercial",
    "insurance": "Insurance/Commercial",
    "insurance - commercial": "Insurance/Commercial",
    "medicare advantage": "Managed Medicare",
    "medicare mmai": "Managed Medicare",
    "medicaid mmai": "Managed Medicaid",
    "medicaid pending": "Medicaid",
}


_CENSUS_PAYOR_MAP_CACHE: dict[str, dict[str, str]] | None = None


def _census_payor_map() -> dict[str, dict[str, str]]:
    """Lazily loaded {operator_name: {raw_label_lower: canonical_payor}}
    from the master account mapping's Grouping="Census" rows (see
    PROJECT_RULES.md section 2b). Covers Curis, Lineage, Extendicare,
    Evercare, Lincoln; empty/missing for Aliya and Allure.
    """
    global _CENSUS_PAYOR_MAP_CACHE
    if _CENSUS_PAYOR_MAP_CACHE is None:
        try:
            from db.seed.load_master_mapping import get_census_payor_map

            _CENSUS_PAYOR_MAP_CACHE = get_census_payor_map()
        except Exception:
            _CENSUS_PAYOR_MAP_CACHE = {}
    return _CENSUS_PAYOR_MAP_CACHE


def normalize_payor(raw_label: str, operator_name: str, is_census: bool = False) -> str:
    """Return the canonical payor name for a raw source label.

    For census labels, prefers the master account mapping's own
    Grouping="Census" rows (PROJECT_RULES.md section 2b) when the operator
    is covered by it -- this is what actually encodes the Curis/Lincoln
    hospice-Medicaid fold and the Evercare no-fold exception, rather than
    a hand-maintained alias table that could drift from the source of
    truth. Falls back to the general alias table (this module's
    PAYOR_ALIASES) for operators the master mapping doesn't cover
    (Aliya, Allure) or for revenue-side labels.
    """
    label = re.sub(r"^(Resident Income|Census|Ancillary Expense)\s+", "", raw_label, flags=re.IGNORECASE).strip()
    key = label.lower()

    if is_census:
        operator_map = _census_payor_map().get(operator_name)
        if operator_map and raw_label.strip().lower() in operator_map:
            return operator_map[raw_label.strip().lower()]

    return PAYOR_ALIASES.get(key, label)


# ---------------------------------------------------------------------
# Sign-multiplier keyword rules (PROJECT_RULES.md section 3)
# ---------------------------------------------------------------------

NEGATIVE_SIGN_KEYWORDS = ("bed tax", "rev-assessment tax", "rev assessment tax")


def default_sign_multiplier(raw_label: str) -> int:
    label = raw_label.lower()
    if any(kw in label for kw in NEGATIVE_SIGN_KEYWORDS):
        return -1
    return 1


# ---------------------------------------------------------------------
# GL account label parsing
# ---------------------------------------------------------------------

_CODE_LABEL_RE = re.compile(r"^\s*(\d{3,6})\s*-\s*(.+?)\s*$")


def split_code_and_label(raw_cell: str) -> tuple[str | None, str]:
    """'504000 - Salaries - Regular' -> ('504000', 'Salaries - Regular')."""
    m = _CODE_LABEL_RE.match(raw_cell.strip())
    if m:
        return m.group(1), m.group(2)
    return None, raw_cell.strip()


def salaries_or_other(label: str) -> str:
    """Heuristic sub_group split used within OpEx department detail:
    payroll-flavored accounts -> "Salaries", everything else -> "Other".
    Regional Allocation is force-mapped to "Other" per PROJECT_RULES
    section 4 regardless of this heuristic -- callers apply that override.
    """
    key = label.lower()
    if any(kw in key for kw in ("salaries", "salary", "payroll tax", "wages")):
        return "Salaries"
    return "Other"


# ---------------------------------------------------------------------
# Facility lookup (case-insensitive, alias-aware -- PROJECT_RULES section 8)
# ---------------------------------------------------------------------


class FacilityResolver:
    def __init__(self, conn: sqlite3.Connection, operator_id: int):
        self.conn = conn
        self.operator_id = operator_id
        self._by_name: dict[str, int] = {}
        for facility_id, name in conn.execute(
            "SELECT facility_id, facility_name FROM dim_facility WHERE operator_id = ?",
            (operator_id,),
        ):
            self._by_name[name.strip().lower()] = facility_id
        for facility_id, alias in conn.execute(
            """
            SELECT a.facility_id, a.alias_name
            FROM dim_facility_alias a
            JOIN dim_facility f ON f.facility_id = a.facility_id
            WHERE f.operator_id = ?
            """,
            (operator_id,),
        ):
            self._by_name.setdefault(alias.strip().lower(), facility_id)

    def resolve(self, name: str) -> int | None:
        return self._by_name.get(name.strip().lower())


# ---------------------------------------------------------------------
# Mapping / fact insert helpers
# ---------------------------------------------------------------------


class MasterMappingLookup:
    """Looks up a pre-loaded master-mapping row (see PROJECT_RULES.md
    section 2b / db/seed/load_master_mapping.py) by exact raw_account_label,
    case-insensitively. Parsers should try this FIRST for every raw line
    they encounter; only fall back to a parser-local heuristic (and log the
    gap) when the master mapping doesn't cover that operator or that
    specific label.
    """

    def __init__(self, conn: sqlite3.Connection, operator_id: int):
        self._by_label: dict[str, tuple] = {}
        for row in conn.execute(
            """
            SELECT raw_account_label, mapping_id, statement_type, category, detail, payor, sign_multiplier
            FROM dim_account_mapping
            WHERE operator_id = ? AND notes LIKE 'source=master_mapping%'
            """,
            (operator_id,),
        ):
            self._by_label[row[0].strip().lower()] = row[1:]

    def lookup(self, raw_account_label: str):
        """Returns (mapping_id, statement_type, category, detail, payor,
        sign_multiplier) or None if not covered by the master mapping."""
        return self._by_label.get(raw_account_label.strip().lower())


def get_or_create_mapping(
    conn: sqlite3.Connection,
    operator_id: int,
    raw_account_code: str | None,
    raw_account_label: str,
    statement_type: str,
    category: str,
    sub_group: str | None,
    detail: str | None,
    sign_multiplier: int,
    is_addback: bool = False,
    notes: str | None = None,
    payor: str | None = None,
) -> int:
    # sqlite3's cursor.lastrowid reflects the last row actually inserted by
    # this connection -- it is NOT updated when ON CONFLICT DO UPDATE takes
    # the update branch, so it cannot be trusted to identify this row.
    # Always look the id up explicitly after the upsert.
    conn.execute(
        """
        INSERT INTO dim_account_mapping
            (operator_id, raw_account_code, raw_account_label, statement_type,
             category, sub_group, detail, payor, sign_multiplier, is_addback, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(operator_id, raw_account_code, raw_account_label) DO UPDATE SET
            statement_type = excluded.statement_type,
            category = excluded.category,
            sub_group = excluded.sub_group,
            detail = excluded.detail,
            payor = excluded.payor,
            sign_multiplier = excluded.sign_multiplier,
            is_addback = excluded.is_addback,
            notes = excluded.notes
        """,
        (
            operator_id,
            raw_account_code,
            raw_account_label,
            statement_type,
            category,
            sub_group,
            detail,
            payor,
            sign_multiplier,
            int(is_addback),
            notes,
        ),
    )
    row = conn.execute(
        "SELECT mapping_id FROM dim_account_mapping WHERE operator_id = ? AND "
        "raw_account_code IS ? AND raw_account_label = ?",
        (operator_id, raw_account_code, raw_account_label),
    ).fetchone()
    return row[0]


def insert_financial_fact(
    conn: sqlite3.Connection,
    facility_id: int,
    period_date: str,
    mapping_id: int,
    amount: float,
    source_file: str,
    source_row_ref: str,
    load_batch_id: str,
) -> None:
    # Additive on conflict, not a replace: the same raw account label can
    # legitimately appear twice in one source file under two different
    # subgroups that both map to the same canonical mapping_id (e.g.
    # Lincoln's "Depreciation Expense" appears under both "General
    # Expenses" and "Property Expenses") -- both amounts are real and must
    # be summed, matching insert_census_fact's own merge behavior. A
    # REPLACE here would silently drop one of the two amounts.
    conn.execute(
        """
        INSERT INTO fact_tenant_financials
            (facility_id, period_date, mapping_id, amount, source_file, source_row_ref, load_batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(facility_id, period_date, mapping_id, source_file) DO UPDATE SET
            amount = fact_tenant_financials.amount + excluded.amount,
            source_row_ref = fact_tenant_financials.source_row_ref || ',' || excluded.source_row_ref,
            load_batch_id = excluded.load_batch_id,
            loaded_at = datetime('now')
        """,
        (facility_id, period_date, mapping_id, amount, source_file, source_row_ref, load_batch_id),
    )


def insert_census_fact(
    conn: sqlite3.Connection,
    facility_id: int,
    period_date: str,
    payor: str,
    resident_days: float,
    source_file: str,
    load_batch_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO fact_census (facility_id, period_date, payor, resident_days, source_file, load_batch_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(facility_id, period_date, payor, source_file) DO UPDATE SET
            resident_days = fact_census.resident_days + excluded.resident_days,
            load_batch_id = excluded.load_batch_id,
            loaded_at = datetime('now')
        """,
        (facility_id, period_date, payor, resident_days, source_file, load_batch_id),
    )


def insert_reported_net_income(
    conn: sqlite3.Connection,
    facility_id: int,
    period_date: str,
    reported_net_income: float,
    source_file: str,
    source_row_ref: str,
    load_batch_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO fact_reported_net_income
            (facility_id, period_date, reported_net_income, source_file, source_row_ref, load_batch_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(facility_id, period_date, source_file) DO UPDATE SET
            reported_net_income = excluded.reported_net_income,
            source_row_ref = excluded.source_row_ref,
            load_batch_id = excluded.load_batch_id
        """,
        (facility_id, period_date, reported_net_income, source_file, source_row_ref, load_batch_id),
    )


def new_batch_id() -> str:
    return uuid.uuid4().hex


def excel_date_to_iso(value) -> str:
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, str):
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(value.strip(), fmt).date().isoformat()
            except ValueError:
                continue
    raise ValueError(f"Cannot parse date: {value!r}")


@dataclass
class LoadResult:
    source_file: str
    facility_periods_loaded: int = 0
    facility_periods_failed: int = 0
    exceptions: list[str] = field(default_factory=list)
