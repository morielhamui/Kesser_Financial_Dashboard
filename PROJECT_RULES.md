# Kesser Tenant Financial Monitoring — Project Rules & Decisions

This file is the persistent source of truth for the business rules, mapping
decisions, and known-bug history behind this system. It exists so this
knowledge survives across sessions instead of living only in chat history.
Any change to a rule below should be made here first, then reflected in code.

## 1. Purpose

Kesser is a real estate company that owns nursing home (SNF) properties and
leases them to third-party operators. This system tracks tenant (operator)
financial health per facility per period so Kesser can monitor continued
ability to pay rent. It replaces a prior Power BI report.

## 2. Operators and Source File Formats

| Operator | Brands covered (facility-listing `Manager` values) | Source format |
|---|---|---|
| **Curis** | Axiom, Arcadia, Arcadia - ALF, Goldwater (financial-name prefixes Avenues/Villas/Gardens fall under Arcadia / Arcadia - ALF) | Consolidated multi-facility statements (one workbook, one column per facility, per facility-group e.g. "Petersen Group") |
| **Extendicare** | Extended Care, Haven | T12 Budget vs. Actual, single-facility files |
| **Lincoln** | Lincoln | Multi-facility income statements + separate census files |
| **Lineage** | Lineage | QuickBooks Desktop T12 exports; also `<Facility>_PL_MMDDYYYY.xlsm` files (North Aurora, Sandwich, Irving Park, South Elgin, Ironwood) |
| **Evercare** | Evercare | Single-facility, trailing-12 tabs |
| **Aliya** | Aliya | YTD detailed hierarchical P&L, up to 5 levels of indentation |
| **Allure** | Allure (facilities: Mendota, Peru, Sterling, Walnut) | "Income Statement Trending Detail - GGM" — wide sheet, one row per account, `<Month>_Actual $` / `<Month>_Actual $/Day` column pairs per month plus a `TOTALS` column, 3-space-indent leaf accounts under department headers, `TOTAL <dept>` subtotal rows, a `Patient Days` section for census, `Net Income - (Loss)` bottom line. Discovered mid-project (not in the original 6); added here per user confirmation. Walnut has an added ILF (independent living) component. |

**Excluded from load**: Stern and COR HC Partners LLC are tenants/managers
with no financials to load — present in the facility master for
traceability (`dim_facility.is_active = 0`), but their absence from a load
batch is not an exception.

Note: "Petersen" is not an operator — it is a Curis **facility group** name
(header: `Curis Services` / `Facility group: Petersen Group`), covering a
set of Axiom-brand facilities (Axiom Gardens Flora, Axiom Flora, Axiom
Gardens Mount Vernon, Axiom West Frankfort, Axiom Mount Vernon, Axiom
Rosiclare, Axiom Harrisburg, etc.). Files named `*Petersen*` and
`*Peterson*` (both spellings appear in source filenames) are Curis-operator
raw files. "Petersen SNF" is also the landlord entity name for most of the
portfolio in the facility master (`Landlord Name` column) — do not confuse
the landlord label with the operator/manager.

Stern is no longer a tenant. COR HC Partners LLC has no financials to load
(do not treat its absence as a load failure).

## 2a. Facility Master Data

`data/reference/facility_listing.xlsx` (sheet `Dim_Facility`, 61 rows) is
the source of truth for `dim_facility`: `FacilityKey`, `Manager` (brand,
grouped into operators per the table above — trim whitespace, e.g. "Allure "
vs "Allure"), `Landlord Name`, `Previous Name` (→ `dim_facility_alias`),
`Financial Name` (→ `dim_facility.facility_name`, matches how the facility
appears in financial statements), `New Name`, address/state/county,
bed counts, `Facility ID`, `Licensee ID`, Medicare certification number.

## 2b. Master Account Mapping (source of truth)

`data/reference/kesser_master_account_mapping.xlsx` is the authoritative
mapping for **Curis, Lineage, Extendicare, Evercare, Lincoln** (999
combined rows across those 5 operators; does not cover Aliya or Allure,
both discovered/added after this file was built — those two use
parser-local heuristics until a master mapping row set exists for them).
Loaded via `db/seed/load_master_mapping.py` into `dim_account_mapping`.

Sheet shape: `Operator, Raw Account, Grouping, Sub-Group, Detail, Payor,
Sign Multiplier, Exclude (subtotal)`, plus a `Sign Adjustments` tab (same
shape minus Payor, for accounts the source stores negative that must flip
sign — e.g. Extendicare's `Bed Tax` / `Rev - Assessment Tax`) and a
`Cross-Operator Concepts` tab (precedent for reused labels across
operators — check it before deciding a new account's mapping).

Column mapping into `dim_account_mapping`:
- `Grouping` → `statement_type` (`revenue` | `opex` | `capital`; see §6 for
  why this is a broad bucket, not the narrower metrics-layer concept)
- `Sub-Group` → `category` (department: Nursing, Ancillary, General and
  Administrative, Management Fees, Marketing, Resident Income, Other
  Income / Expense, Capital Expenses, ...)
- `Detail` → `detail` (Salaries, Supplies, Therapy, Rent, Other, ...)
- `Payor` → `payor` (mainly populated for Ancillary opex rows split by
  payor+service, and Revenue rows split by payor)
- Rows with blank `Grouping` and/or `Exclude=1` are section/department
  subtotals (e.g. the bare label "Nursing Expenses", or the AC sheet's own
  "Gross Resident Income" aggregate) — never loaded as accounts; parsers
  must skip them structurally (by section/indentation), not by consulting
  this exclude flag directly, since a subtotal that slips through would
  double-count.
- `Grouping="Census"` rows are not loaded into `dim_account_mapping` at
  all (census isn't GL-coded). Instead their `Detail` column is the
  authoritative canonical-payor lookup for census parsing — use
  `db/seed/load_master_mapping.get_census_payor_map()` rather than
  hand-maintaining a separate alias table per operator, for any operator
  this mapping covers.

Confirmed by hand-tracing the arithmetic (Curis, Petersen Group, 05/2025):
Revenue = full `Resident Income <Payor>` detail (not the AC sheet's netted
"Total Net Resident Income") + all Other Income/Expense items; Operating
Expense = every department GL account **including** Nursing Home Fee
(reclassified to G&A) and the by-payor-by-service Ancillary Expense detail
(reclassified from what Curis's own sheet calls a revenue deduction into a
real Operating Expense department, `category="Ancillary"`). This reproduces
the source's reported Net Income to the dollar.

## 3. Core Taxonomy Rules

- **Expense accounts** get the specific department category — Nursing,
  Dietary, Ancillary, Plant, Housekeeping, Laundry and Linen, Activities,
  Social Service, Employee Welfare, Marketing, General and Administrative,
  Management Fees. Never bucket into a generic "Other" when a specific
  category applies.
- **Revenue accounts** are categorized only by payor — never further split
  by service type.
- **Net Income is the correctness test, not department-level subtotals.**
  The mapping intentionally reclassifies accounts away from each operator's
  own internal categorization. Only the bottom-line Net Income needs to tie
  out to the source; department subtotals are allowed to differ from the
  operator's own presentation.
- **Sign multiplier**: some source accounts are stored negative when they
  should be treated as positive expense/revenue (or vice versa). Apply
  `dim_account_mapping.sign_multiplier = -1` where needed. This has been a
  repeated source of bugs — always verify against the source's own Net
  Income after mapping, not just visually. Known example: Bed Tax /
  Rev-Assessment Tax.

## 4. Specific Mapping Decisions

- **Regional Allocation** costs stay in their originating department
  (Dietary / Nursing / Plant / Social Service / G&A) — do not move them to
  a corporate/other bucket. Their `Detail` value is `"Other"`, not
  `"Salaries"`.
- **Management Fees** get their own Sub-Group: `"Management Fees"`.
- **Provider Assessment Fees** map to G&A, Detail = `"Licenses and Provider
  Fee"`.
- **"Consulting"** as an account label refers to **Cherry**, a
  software/vendor cost — not a generic consulting expense. Map accordingly,
  not to a generic consulting line.
- **"Prior Year Expenses/Adjustments"** is Revenue / Other, not an expense,
  regardless of which section of the source it appears in.
- **Kesser's own revenue** (`fact_kesser_revenue`, the rent side) is
  **effective-dated, not monthly**. Rent changes only at step-ups. Do not
  require a row for every month — carry the last known effective value
  forward until the next dated entry.

## 5. Payor Alias Consolidation

Apply consistently to **both** census and revenue sides.

| Source label(s) | Canonical payor |
|---|---|
| "Insurance/Commerical" (typo), "Insurance", "Insurance - Commercial" | **Insurance/Commercial** |
| "Medicare Advantage" | **Managed Medicare** |
| "Medicare MMAI" | **Managed Medicare** (dual-eligible; when the stay is Medicare-covered, Medicare rates apply) |
| "Medicaid MMAI" | **Managed Medicaid** |
| "Medicaid Pending" | **Medicaid** |

### Operator-specific hospice folding

- **Curis only**: "Hospice Medicaid" and "Hospice Medicaid Pending" →
  **Medicaid**. Curis has no separate Hospice revenue line — hospice
  residents' room & board revenue sits entirely inside "Resident Income
  Medicaid," while census counts hospice days separately. Without folding,
  Medicaid PPD is overstated ~18%.
  - Verified: Arcadia Aledo, April 2026 — $146,115 ÷ 489 days = $298.80
    (wrong, hospice days excluded) vs. $146,115 ÷ 579 days = $252.36
    (correct, hospice days included).
  - This fix was verified in the prior build but never deployed — it must
    be live from day one here.
- **Lincoln**: hospice census also maps to Medicaid, same reasoning (no
  separate hospice revenue line). Flagged as an interim decision
  previously — treat as correct for now; revisit only if evidence says
  otherwise.
- **Evercare: do NOT fold.** Evercare reports its own proper Hospice
  revenue line, and per-diem rates for Hospice and Medicaid can
  legitimately match (verified: Collinsville, April 2026 — both
  $214.80/day). That is real data, not a mapping artifact.

## 6. Validation Rule (gate before anything is "loaded")

After every load:

```
recomputed Net Income = Revenue − Operating Expense − Capital Expenses
```

This must match the source file's own reported Net Income within **$50**.
If it does not, the load fails and is written to `exceptions_log` — nothing
downstream (metrics, dashboard) reads data that hasn't passed this check.

**Important nuance** (confirmed against the master account mapping's own
README): in this 3-term formula, "Operating Expense" is a **broad**
grouping bucket — it includes G&A, Management Fees, and any
operator-specific reclassified items (e.g. Curis's Nursing Home Fee is
reclassified into G&A/"Licenses and Provider Fee" here), not just
department-level opex. "Revenue" likewise includes the full Other
Income/Expense section (Interest Income, QIP, CNA Incentive, etc.), not
just resident income by payor. `dim_account_mapping.statement_type` takes
exactly these 3 values (`revenue` | `opex` | `capital`) — one per row from
the master mapping's `Grouping` column. The **narrower** "Operating
Expense" used in the metrics waterfall (§7, which excludes G&A and
Management Fees) is a separate, later concept computed from the same rows
by filtering on `category`/`sub_group` — it is not what this validation
gate checks.

## 7. Metrics / Waterfall Formulas

Computed per facility-period:

```
Operating Revenue              = Resident Income + Ancillary + QIP
Operating Expense              = all department sub-groups except G&A and
                                  Management Fees
                                  (includes "Other Income / Expense" as a
                                  sub-group under Operating Expense — this
                                  placement is specific to Evercare)
Operating Income                = Operating Revenue − Operating Expense
EBITDARM                        = Operating Income − G&A
EBIDARM                         = EBITDARM − Real Estate Tax
Earnings before Management Fees = EBIDARM − Capital Expenses
Earnings                        = Earnings before Management Fees
                                   − Management Fees
NOI                              = Earnings + Other Income/Expense
                                   (QIP excluded here — already counted in
                                   Operating Revenue)
```

## 8. Known Past Bugs — Do Not Reintroduce

- **Lineage mapping file**: had two columns both named `Merged.2`
  (duplicate column name) → caused phantom mapping errors. Always
  de-duplicate/validate column headers on load, don't assume uniqueness.
- **Curis addbacks detection**: must use **structural detection** (position/
  indentation/section boundaries), not a keyword whitelist — label variants
  were previously missed. Prefer a blacklist + structural approach.
- **Extendicare payor-subtotal detection**: must be narrow. An earlier,
  overly broad subtotal detector excluded real leaf accounts that happened
  to share a header name with a subtotal row.
- **Lincoln extra metadata row**: some files insert an extra row that
  shifts all fixed positions. Use dynamic header detection (search for
  header markers), never fixed row numbers.
- **Lincoln facility renames**: two facilities were renamed mid-stream.
  Look up by both old and new names, case-insensitively.
- **Aliya indentation hierarchy**: up to 5 levels deep. Must track
  indentation depth with an explicit stack, not keyword matching, to
  correctly attribute child accounts to the right parent category.

## 9. Database Schema (see `db/migrations/` for DDL)

- `dim_facility`
- `dim_operator`
- `dim_account_mapping` (includes `sign_multiplier`)
- `fact_tenant_financials`
- `fact_census`
- `fact_kesser_revenue` (effective-dated, forward-filled — see §4)
- `fact_reported_net_income`
- `exceptions_log`
- External Medicaid/CMS reference data: `fact_hfs_rates`, `fact_qip_payments`,
  `fact_cna_payments`, `fact_cms_ratings`

## 10. Parsers

One parser module per operator (`parsers/<operator>.py`), each responsible
for: locating the header/period, extracting the account hierarchy per its
own structural quirks (see §8), mapping through `dim_account_mapping`,
applying `sign_multiplier`, and producing rows for
`fact_tenant_financials` / `fact_census`. Every parser run must pass
through the validation module (§6) before rows are marked loaded.

## 10a. Known Data Gaps (as of initial load)

Tracked so they aren't mistaken for load failures — every one of these is
an absence of source data, not a parsing bug. All 7 operators otherwise
validate 100% (1,856 facility-periods, 0 failures) as of this writing.

- **Aliya**: no raw files for Glenwood/Palatine's sibling facilities —
  only 2 of Aliya's facilities have any data at all.
- **Lincoln**: no separate census file was ever provided, despite the
  spec calling for one (income statement + separate census files).
  Census is not loaded for Lincoln.
- **Lineage**: Ironwood (a 5th Lineage facility per the facility master)
  has zero raw files.
- **Evercare**: Edwardsville and Evercare University (2 of Evercare's 7
  facilities per the facility master) have zero raw files. Also, the
  Breese tab in one specific file (`fce47447-4_Pack_PL_12.25.xlsx`) is
  entirely blank — skipped, not a failure.
- **Allure**: Sterling has zero raw files.
- **Extendicare**: 4 Balance Sheet files (no P&L/Net Income data) are
  intentionally skipped by the parser, not counted as failures.

## 11. Hosting

Web front end (replacement for the old Power BI report) — pages to be
designed once the data layer is validated end-to-end for at least one
operator.
