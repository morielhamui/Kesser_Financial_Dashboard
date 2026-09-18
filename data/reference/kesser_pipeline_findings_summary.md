# Kesser Financial Pipeline — Findings Summary
*Session date: September 2026*

Purpose: a clean record of what was diagnosed, verified, and fixed in this session, so nothing has to be re-derived when this work moves to Claude Code.

---

## 1. Evercare — Hospice/Medicaid PPD: NOT a bug, verified correct

**The report**: Hospice and Medicaid PPD looked off for Evercare when compared against Power BI.

**What was checked**: Raw source file `Peterson___Breese_April26_P_L.xlsx`, "Collinsville" tab (facility 1030), April 2026.

**What the source actually shows**:
| Line | Revenue | Per-diem rate (in the source itself) |
|---|---|---|
| Room & Board Medicaid | $47,900.40 | $214.80/day |
| Room & Board Hospice | $17,613.60 | $214.80/day |

Evercare itself reports the identical $214.80/day rate for both payors in this facility-period. This is not something our pipeline computed or distorted — it's copied straight from the source. Also cross-verified Managed Medicaid: source Room & Board ($393,943.20) + Adjustments ($1,200.40) = $395,143.60, exactly matching our system.

**Conclusion**: Our numbers are correct. If Power BI shows different Hospice/Medicaid rates for this facility, the discrepancy is on the Power BI side — most likely the same Power Query census-load bug identified earlier in this project (previously found causing a Medicare/Medicaid PPD swap on a different facility). Not something to fix in our pipeline.

**Status**: Closed. No action needed.

---

## 2. Curis (Arcadia and all Curis facilities) — Hospice Medicaid census/revenue mismatch: REAL BUG, FIX VERIFIED BUT NOT YET DEPLOYED

**The report**: Arcadia's revenue totals matched Power BI but PPD didn't, suggesting a census/revenue mapping issue.

**What was checked**: Raw source file `04_30_26_Petersen_Financial_Statements_-_MTD_Only_NO_ADDBACKS.xls`, Arcadia Aledo column (facility 1008), April 2026.

**The mechanism**:
- **Census side** tracks a separate "Hospice Medicaid" bucket: Medicaid 372 / Hospice Medicaid 90 / Medicaid Pending 117 (Aledo, April 2026)
- **Revenue side** has no Hospice line at all — Resident Income Medicaid ($146,115) is the only Medicaid-family revenue line
- Our system was folding "Medicaid Pending" into "Medicaid" for PPD (from an earlier fix) but **not** folding "Hospice Medicaid" or "Hospice Medicaid Pending"
- Result: Medicaid revenue included hospice residents' dollars, but the day-count denominator excluded their days

**Impact, concretely (Aledo, April 2026)**:
- What we were computing: $146,115 ÷ 489 days = **$298.80/day**
- What it should be: $146,115 ÷ 579 days (372+117+90) = **$252.36/day**
- ~18% overstatement

**Scope**: Checked all 831 documents. This pattern — "Hospice Medicaid" / "Hospice Medicaid Pending" census categories with no matching revenue line — appears in **all 22 Curis facilities** (Axiom, Arcadia, Goldwater, Avenues, Villas, Gardens brands), 371 affected document-periods. No other operator (Evercare, Extendicare, Lincoln, Lineage, Aliya) has this pattern.

**Precedent**: This is the same situation already resolved for Lincoln — no separate hospice revenue line exists, so hospice census folds into Medicaid as an interim decision. Same fix applied here for consistency.

**Fix applied**: Fold "Hospice Medicaid" → "Medicaid" and "Hospice Medicaid Pending" → "Medicaid" in `census.by_payor`, for all 22 Curis facilities. Verified locally: Aledo April 2026 now shows Medicaid: 579 days, matching the source exactly (372+117+90+0).

**Status**: ⚠️ **Fix is correct and verified locally, but NOT deployed to the live site.** The tool interface used earlier in this session to write to the site's database stopped working mid-session (an "Invalid action" error on a call that had worked repeatedly just before). This needs to be applied once a working path to the live data exists — likely as part of the Claude Code rebuild.

---

## 3. Payor alias consolidation (applied earlier this session, confirmed live)

Applied and verified live across all 831 facility-months:
- "Insurance/Commerical" (typo) / "Insurance" / "Insurance - Commercial" → **Insurance/Commercial**
- "Medicare Advantage" → **Managed Medicare**
- "Medicare MMAI" → **Managed Medicare**
- "Medicaid MMAI" → **Managed Medicaid**
- "Medicaid Pending" → **Medicaid**

Rationale for MMAI aliases (dual-eligible plans): when a dual-eligible resident is in a Medicare-covered stay, Medicare rates apply, so MMAI census/revenue routes to the Medicare-family payor bucket matching that logic.

---

## 4. Open item carried forward

- **The Curis Hospice-Medicaid fix (Section 2) still needs to be pushed live.** All source files and the corrected local data exist; only the deployment step remains.
- This should be one of the first things done in the Claude Code rebuild, alongside re-implementing the Curis parser with this fix built in from the start (rather than patched on after the fact).

---

## 5. Infrastructure notes for the Claude Code rebuild

- All 6 operator parsers (Curis, Extendicare, Lincoln, Lineage, Evercare, Aliya) need to be rebuilt from scratch — the working code from earlier in this project no longer exists in this environment, though the raw source files and master account mapping file are intact and were used to re-verify everything in this summary.
- The account-mapping and payor-alias rules above should be written into a spec file the Claude Code project reads automatically, so this knowledge doesn't live only in chat history.
- A real database (not a hand-patched JSON store) removes the need for the kind of manual batch-pushing this session required.
