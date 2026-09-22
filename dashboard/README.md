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
  breakdowns, GL-account-level drill-down. The payor-matched census
  methodology (dividing each payor's revenue by that SAME payor's own
  census days, not the facility total) is documented in PROJECT_RULES.md
  §5 and independently validated against Illinois HFS's published
  Medicaid rates (see §8/`scripts/compare_hfs_medicaid_rates.py`) --
  98.2% of comparable facility-quarters land within +/-10%.

Design system (palette, type pairing, filter/drill-down interaction
patterns) is shared across pages for visual consistency; see the inline
`<style>` block at the top of either `build_*.py` for the token set.
