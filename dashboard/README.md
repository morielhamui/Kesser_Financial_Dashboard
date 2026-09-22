# Dashboard pages

Each dashboard page is a self-contained HTML artifact: all data is
exported from the database into a JSON file, then embedded inline into a
single HTML file (no server, no external data fetches -- required by how
these get published as Claude Artifacts). Two scripts per page:

- `export_<page>.py` -- queries `db/kesser_financials.sqlite3`, writes
  `<page>_data.json` in this directory.
- `build_<page>.py` -- reads that JSON, embeds it into `<page>.html`
  alongside the page's CSS/JS.

Neither the generated `.json` nor `.html` files are committed (see
`.gitignore`) -- they're derived from the database and regenerated on
demand. To update a page after a database or script change:

```bash
python3 dashboard/export_t12.py && python3 dashboard/build_t12.py
python3 dashboard/export_ppd.py && python3 dashboard/build_ppd.py
python3 dashboard/export_census.py && python3 dashboard/build_census.py
python3 dashboard/export_covenant.py && python3 dashboard/build_covenant.py
python3 dashboard/export_t12_facility.py && python3 dashboard/build_t12_facility.py
```

Then publish the resulting `.html` file with the Artifact tool. If the
page was published before, pass its existing artifact `url` to update it
in place rather than creating a new one.

## Pages

- **T12 P&L Waterfall** (`export_t12.py` / `build_t12.py`) -- Operating
  Revenue through NOI, by month, with manager/landlord/facility
  cross-filters, T3/T12 quick ranges, and click-to-drill facility/manager
  detail. See PROJECT_RULES.md §7 for the waterfall formulas.
- **Revenue & Expense PPD** (`export_ppd.py` / `build_ppd.py`) -- $ per
  resident day by operator, department (Expense) and payor (Revenue)
  breakdowns, GL-account-level drill-down. A "Per Resident Day / Total $"
  toggle switches every card, row, and drill-down between the two --
  Total $ needs no census day count at all, so it's the one baseline
  that still works for an operator with no census file loaded (Aliya),
  putting it on equal footing with the rest of the portfolio. The
  payor-matched census methodology (dividing each payor's revenue by
  that SAME payor's own census days, not the facility total) is
  documented in PROJECT_RULES.md §5 and independently validated against
  Illinois HFS's published Medicaid rates (see
  §8/`scripts/compare_hfs_medicaid_rates.py`) -- 98.2% of comparable
  facility-quarters land within +/-10%.
- **Census & Occupancy** (`export_census.py` / `build_census.py`) --
  resident mix by payor (donut snapshot + 100%-stacked trend, using the
  dataviz skill's validated 8-hue categorical palette), occupancy %
  (resident days &divide; licensed beds &times; days in month, weighted,
  never an average of per-facility %s), and a live Medicaid-rate-vs-HFS
  comparison table (the same methodology as the PPD page's HFS validation,
  now surfaced per facility/quarter instead of only as an offline script).
  Licensed bed counts come from `dim_facility.total_beds` (migration 006),
  sourced the same way `hfs_building_id` was (migration 005): a column
  that was already in `facility_listing.xlsx` but never persisted.
- **Covenant & EBIDAR** (`export_covenant.py` / `build_covenant.py`) --
  EBIDAR coverage against purchase price, by landlord/manager package
  (`fact_purchase_price`, migration 007) -- currently the Petersen SNF
  master lease's 8 manager-brand packages plus one individually-owned
  property. An adjustable target-cap-rate slider (default 13%) drives
  the headline Required EBIDAR / surplus-shortfall figures, alongside a
  fixed 10-13% sensitivity table. Package groups with no purchase price
  on file are listed, not hidden, so a gap in coverage stays visible.
- **T12 by Facility** (`export_t12_facility.py` / `build_t12_facility.py`)
  -- a benchmarking view: pick a landlord to scope the field, choose
  whether to compare by manager or by individual facility, then select
  which ones to line up side by side as columns (e.g. every manager
  under one landlord, or a hand-picked set of facilities across the
  whole portfolio). Waterfall line items are rows, summed over the
  selected month range (T3/T12 quick ranges, anchored on the current
  selection's own latest reported month); the best/worst performer per
  row is tinted so relative performance reads at a glance. Every line
  -- Operating Revenue, each Operating Expense department, G&amp;A, Real
  Estate Tax, Capital Expenses, Management Fees, Other Income/Expense
  -- opens a click-to-drill modal down to its individual GL accounts,
  scanning the full ~69,000-row portfolio-wide GL export on demand
  rather than pre-indexing it, since a drill only opens on click, not
  on every cell render.

Design system (palette, type pairing, filter/drill-down interaction
patterns) is shared across pages for visual consistency; see the inline
`<style>` block at the top of either `build_*.py` for the token set.
