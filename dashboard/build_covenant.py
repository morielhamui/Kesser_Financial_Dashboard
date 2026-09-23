import json, pathlib

SCRATCH = pathlib.Path(__file__).resolve().parent
data = json.loads((SCRATCH / "covenant_data.json").read_text())

managers = sorted(set(f["manager"] for f in data["facilities"]))
landlords = sorted(set(f["landlord"] for f in data["facilities"]))

data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

HTML = r"""<title>Covenant &amp; EBIDAR</title>
<style>
:root{
  --bg:#FAF7F0; --surface:#FFFFFF; --surface-2:#F3EEE3;
  --ink:#1C2B27; --ink-soft:#3E4C47; --muted:#7A7062;
  --border:#E4DCC9; --border-strong:#D3C7AC;
  --accent:#A8781F; --accent-soft:#F1E3C4;
  --good:#2E7D63; --good-soft:#E1F0E7;
  --warn:#C0752A; --warn-soft:#FBEBD8;
  --bad:#B14A3C; --bad-soft:#F8E2DE;
  --shadow: 0 1px 2px rgba(28,43,39,.06), 0 6px 20px -8px rgba(28,43,39,.18);
  color-scheme: light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#141C1A; --surface:#1B2522; --surface-2:#212C28;
    --ink:#EDE7D8; --ink-soft:#C9CFC7; --muted:#8B9490;
    --border:#324039; --border-strong:#425149;
    --accent:#DCAA55; --accent-soft:#3A3221;
    --good:#57B092; --good-soft:#1E332B;
    --warn:#E0954E; --warn-soft:#3A2B1A;
    --bad:#E1897A; --bad-soft:#3A2521;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px -10px rgba(0,0,0,.5);
  }
}
:root[data-theme="dark"]{
  --bg:#141C1A; --surface:#1B2522; --surface-2:#212C28;
  --ink:#EDE7D8; --ink-soft:#C9CFC7; --muted:#8B9490;
  --border:#324039; --border-strong:#425149;
  --accent:#DCAA55; --accent-soft:#3A3221;
  --good:#57B092; --good-soft:#1E332B;
  --warn:#E0954E; --warn-soft:#3A2B1A;
  --bad:#E1897A; --bad-soft:#3A2521;
  --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px -10px rgba(0,0,0,.5);
}
*{box-sizing:border-box;}
body{
  background:var(--bg); color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,Segoe UI,sans-serif;
  padding-inline:20px; padding-block:24px 48px;
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3{font-family:"Fraunces","Iowan Old Style",Georgia,serif; text-wrap:balance; margin:0;}
.wrap{max-width:1400px; margin-inline:auto; display:flex; flex-direction:column; gap:26px;}
.masthead{display:flex; flex-direction:column; gap:4px;}
.eyebrow{font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--accent); font-weight:600;}
h1{font-size:clamp(24px,3.4vw,32px); font-weight:600; color:var(--ink);}
.sub{color:var(--muted); font-size:14px; max-width:72ch; line-height:1.5;}

.filters{display:flex; flex-direction:column; gap:10px; background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow);}
.filter-row{display:flex; align-items:flex-start; gap:12px; flex-wrap:wrap;}
.filter-label{font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); width:80px; flex:0 0 80px; padding-top:6px;}
.chips{display:flex; flex-wrap:wrap; gap:6px; flex:1;}
.chip{
  font-family:inherit; font-size:12.5px; font-weight:500; color:var(--ink-soft);
  background:var(--surface-2); border:1px solid var(--border); border-radius:999px;
  padding:5px 12px; cursor:pointer; transition:background .12s, color .12s, border-color .12s;
  white-space:nowrap;
}
.chip:hover{border-color:var(--border-strong);}
.chip.active{background:var(--accent); border-color:var(--accent); color:var(--surface);}
.chip.disabled{opacity:.35; cursor:not-allowed; text-decoration:line-through;}
.chips-scroll{max-height:118px; overflow-y:auto; padding-right:4px;}
.filter-hint{font-size:11.5px; color:var(--muted); margin:0; padding-left:92px;}
.range-picker{display:flex; align-items:center; gap:8px;}
.range-picker select{
  font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--ink);
  background:var(--surface-2); border:1px solid var(--border); border-radius:8px;
  padding:5px 10px;
}
.range-sep{color:var(--muted);}

.rate-panel{display:flex; align-items:center; gap:16px; background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow); flex-wrap:wrap;}
.rate-label{font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); white-space:nowrap;}
.rate-slider{flex:1; min-width:200px; accent-color:var(--accent); height:6px;}
.rate-value{font-family:"IBM Plex Mono",monospace; font-size:22px; font-weight:600; color:var(--accent); min-width:70px; text-align:right;}

.section{display:flex; flex-direction:column; gap:14px;}
.section-head{display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap;}
.section-head h2{font-size:19px; font-weight:600;}
.section-head .section-note{font-size:12px; color:var(--muted);}

.stat-strip{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px;}
.stat-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px;}
.stat-label{font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);}
.stat-value{font-family:"IBM Plex Mono",monospace; font-size:24px; font-weight:600; font-variant-numeric:tabular-nums;}
.stat-value.good{color:var(--good);} .stat-value.bad{color:var(--bad);}
.stat-foot{font-size:12px; color:var(--muted);}

.card-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:12px;}
.op-card{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:13px 14px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px;}
.op-card .op-name{font-size:12.5px; font-weight:600; color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.op-card .op-sub{font-size:11px; color:var(--muted); margin-top:-4px;}
.op-card .op-value{font-family:"IBM Plex Mono",monospace; font-size:20px; font-weight:600; font-variant-numeric:tabular-nums;}
.op-card .op-value.no-data{font-family:"IBM Plex Sans",sans-serif; font-size:12.5px; font-weight:500; color:var(--muted); font-style:italic;}
.op-card .op-spark{width:100%; height:28px; display:block;}

.table-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); overflow:hidden;}
.table-scroll{overflow-x:auto; overflow-y:hidden;}
table{border-collapse:collapse; width:100%; font-size:13px;}
thead th{
  position:sticky; top:0; background:var(--surface-2); color:var(--muted);
  font-weight:600; font-size:10.5px; letter-spacing:.04em; text-transform:uppercase;
  text-align:right; padding:10px 14px; border-bottom:1px solid var(--border); white-space:nowrap;
  font-family:"IBM Plex Mono",monospace;
}
thead th.linecol{text-align:left; font-family:"IBM Plex Sans",sans-serif;}
tbody td{padding:8px 14px; text-align:right; border-bottom:1px solid var(--border); font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--ink-soft);}
tbody td.linecell{text-align:left; font-family:"IBM Plex Sans",sans-serif; color:var(--ink); white-space:nowrap;}
th.linecol, td.linecell{position:sticky; left:0; background:var(--surface); z-index:2; box-shadow:1px 0 0 var(--border);}
thead th.linecol{background:var(--surface-2); z-index:3;}
tbody td.linecell .pkg-sub{display:block; font-size:11px; color:var(--muted); font-weight:400;}
.pos{color:var(--good);} .neg{color:var(--bad);}
.no-price-row td{color:var(--muted); font-style:italic;}
.penalty-note{background:var(--warn-soft); border:1px solid var(--warn); border-radius:10px; padding:10px 14px; font-size:12.5px; color:var(--ink-soft); display:flex; gap:8px; align-items:flex-start;}

.footnote{font-size:11.5px; color:var(--muted); line-height:1.5; padding:2px 4px;}

.stat-value.clickable{cursor:pointer; text-decoration:underline dotted; text-underline-offset:5px; text-decoration-color:var(--border-strong);}
.stat-value.clickable:hover{text-decoration-color:var(--accent);}

.drill-backdrop{
  position:fixed; inset:0; background:rgba(20,28,26,.45); display:flex;
  align-items:center; justify-content:center; padding:20px; z-index:50;
}
.drill-card{
  background:var(--surface); border:1px solid var(--border); border-radius:14px;
  box-shadow:var(--shadow); max-width:480px; width:100%; max-height:82vh;
  display:flex; flex-direction:column; overflow:hidden;
}
.drill-head{display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:16px 18px 12px; border-bottom:1px solid var(--border);}
.drill-title{font-family:"Fraunces",serif; font-size:16px; font-weight:600; color:var(--ink);}
.drill-sub{font-size:12px; color:var(--muted); margin-top:2px;}
.drill-close{background:none; border:none; font-size:18px; line-height:1; color:var(--muted); cursor:pointer; padding:2px 4px;}
.drill-close:hover{color:var(--ink);}
.drill-body{overflow-y:auto; padding:4px 0 6px;}
.drill-section-head{font-size:10.5px; font-weight:600; letter-spacing:.05em; text-transform:uppercase; color:var(--muted); padding:12px 18px 6px;}
.drill-row{display:flex; justify-content:space-between; align-items:center; gap:10px; padding:6px 18px; font-size:13px; border-bottom:1px solid var(--border);}
.drill-row:last-child{border-bottom:none;}
.drill-row .name{color:var(--ink); font-weight:500;}
.drill-row .amt{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; color:var(--ink-soft); white-space:nowrap;}
.drill-row .amt.neg{color:var(--bad);}
.drill-row.total{background:var(--surface-2); font-weight:700;}
.drill-row.total .amt{color:var(--ink); font-weight:700;}
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="wrap">
  <div class="masthead">
    <span class="eyebrow">Kesser Financial Dashboard</span>
    <h1>Covenant &amp; EBIDAR</h1>
    <p class="sub">Two separate tests, tracked independently: the <strong>Lease Covenant</strong> (a collective test &mdash; rolling T12 Covenant Income across every Petersen SNF facility vs. 1.2&times; the rent Petersen SNF itself pays CareTrust, its upstream owner &mdash; a financial penalty applies if it's not met) and <strong>Cap Rate Supportable</strong> (EBIDAR by package vs. the purchase option price). Both use the same EBIDAR &mdash; EBIDARM less a normalized 5% of Operating Revenue management-fee add-back, not the operator's actual reported management fee &mdash; but compare it against two different benchmarks. This is fundamentally an operator-side metric; we track it here because Curis is a related operator.</p>
  </div>

  <div class="filters">
    <div class="filter-row">
      <span class="filter-label">Manager</span>
      <div class="chips" id="managerChips"></div>
    </div>
    <div class="filter-row">
      <span class="filter-label">Landlord</span>
      <div class="chips" id="landlordChips"></div>
    </div>
    <div class="filter-row">
      <span class="filter-label">Facility</span>
      <div class="chips chips-scroll" id="facilityChips"></div>
    </div>
    <div class="filter-row">
      <span class="filter-label">Months</span>
      <div class="range-picker">
        <select id="fromMonth"></select>
        <span class="range-sep">&ndash;</span>
        <select id="toMonth"></select>
        <button class="chip" id="t3Btn" type="button">T3</button>
        <button class="chip" id="t12Btn" type="button">T12</button>
      </div>
    </div>
    <p class="filter-hint">Manager/Landlord/Facility filters and the month range only affect the Cap Rate Supportable section below &mdash; the Lease Covenant test is a fixed, collective measure (always every facility, always trailing 12 months) and doesn't change with what's selected here.</p>
  </div>

  <div id="covenantSections"></div>

  <div class="section-head" style="margin-top:6px;">
    <h2>Cap Rate Supportable (Purchase Option)</h2>
    <span class="section-note">EBIDAR for the selected months, annualized, vs. the purchase option price above</span>
  </div>

  <div class="rate-panel">
    <span class="rate-label">Target Cap Rate</span>
    <input type="range" class="rate-slider" id="rateSlider" min="10" max="13" step="0.25" value="13">
    <span class="rate-value" id="rateValue">13.00%</span>
  </div>

  <div class="stat-strip">
    <div class="stat-card">
      <span class="stat-label">Purchase price</span>
      <span class="stat-value" id="statPrice">&ndash;</span>
      <span class="stat-foot">in current filter</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Annualized EBIDAR</span>
      <span class="stat-value" id="statEbidar">&ndash;</span>
      <span class="stat-foot" id="statEbidarFoot">&nbsp;</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Cap rate supportable</span>
      <span class="stat-value" id="statSupportable">&ndash;</span>
      <span class="stat-foot">actual EBIDAR &divide; price</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Surplus / (shortfall)</span>
      <span class="stat-value" id="statSurplus">&ndash;</span>
      <span class="stat-foot" id="statSurplusFoot">at target rate</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Cap Rate Supportable</span>
      <span class="stat-value" id="statSupportedLabel">&ndash;</span>
      <span class="stat-foot">EBIDAR vs. required, at target rate</span>
    </div>
  </div>

  <div class="card-grid" id="pkgCards"></div>

  <div class="section">
    <div class="section-head">
      <h2>Coverage by Package</h2>
      <span class="section-note">Required EBIDAR and surplus/shortfall use the target cap rate above</span>
    </div>
    <div class="table-card">
      <div class="table-scroll">
        <table id="pkgTable">
          <thead><tr>
            <th class="linecol">Package</th>
            <th>Purchase Price</th>
            <th>Annualized EBIDAR</th>
            <th>Cap Rate Supportable</th>
            <th id="requiredHeadCell">Required EBIDAR</th>
            <th>Surplus / (Shortfall)</th>
            <th>Covenant Status</th>
          </tr></thead>
          <tbody id="pkgBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-head">
      <h2>Sensitivity: Surplus / (Shortfall) by Cap Rate</h2>
      <span class="section-note">Same annualized EBIDAR, held constant across a 10&ndash;13% cap rate range</span>
    </div>
    <div class="table-card">
      <div class="table-scroll">
        <table id="sensTable">
          <thead><tr id="sensHead"></tr></thead>
          <tbody id="sensBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <p class="footnote">EBIDAR = EBIDARM &minus; 5% of Operating Revenue (a normalized management-fee add-back standing in for the operator's actual reported management fee) &mdash; the same EBIDAR feeds both tests, compared against two different benchmarks. <strong>Lease Covenant</strong>: a collective measure, not a per-manager or per-package one &mdash; rolling T12 Covenant Income summed across every facility a landlord operates, vs. 1.2&times; the Annual Rent that landlord itself pays its own upstream owner (`fact_lease_rent`, migration 009, currently just Petersen SNF's rent to CareTrust, $810,333.28/mo &mdash; NOT the larger figure Petersen SNF collects from its own operators, a different number entirely). Always the trailing 12 months per the lease, regardless of the filters or month-range above; a shortfall ("Breach") triggers a financial penalty under the lease. Click the T12 covenant income figure to see the month-by-month and by-manager detail behind it. <strong>Cap Rate Supportable</strong>: EBIDAR by package for the selected months, annualized (&times; 12 &divide; number of months with data), vs. Purchase Price &times; the target cap rate slider &mdash; a purchase-option affordability test, unrelated to the lease covenant. Purchase prices are package-level, not per-facility &mdash; e.g. all 7 Arcadia facilities under the Petersen SNF master lease were bought as one package with one price, so EBIDAR for every facility in a package is summed before comparing to that package's price. Only the Petersen SNF packages (all 8 manager brands) and 1155 N First St/Evercare have a purchase price on file; the ~11 other individually-owned properties show "no purchase price data" rather than a guessed figure. See PROJECT_RULES.md section 9a for the landlord/master-lease structure this reflects.</p>
</div>

<div class="drill-backdrop" id="drillBackdrop" hidden>
  <div class="drill-card" role="dialog" aria-modal="true">
    <div class="drill-head">
      <div>
        <div class="drill-title" id="drillTitle">&nbsp;</div>
        <div class="drill-sub" id="drillSub">&nbsp;</div>
      </div>
      <button class="drill-close" id="drillClose" aria-label="Close">&times;</button>
    </div>
    <div class="drill-body" id="drillBody"></div>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;
const MANAGERS = __MANAGERS_JSON__;
const LANDLORDS = __LANDLORDS_JSON__;

const facilityById = {};
DATA.facilities.forEach(f => { facilityById[f.facility_id] = f; });
const ROW_BY_KEY = {};
DATA.rows.forEach(r => { ROW_BY_KEY[r.facility_id + "|" + r.period] = r; });
const PERIODS_ALL = Array.from(new Set(DATA.rows.map(r => r.period))).sort();

let selManagers = new Set(), selLandlords = new Set(), selFacilities = new Set();
let rangeFrom = PERIODS_ALL[0], rangeTo = PERIODS_ALL[PERIODS_ALL.length - 1];
let targetRate = 13.0;

const SENS_RATES = [10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0];

function fmtMoney(v){
  const abs = Math.abs(v);
  const str = "$" + abs.toLocaleString(undefined, {maximumFractionDigits:0});
  return v < 0 ? "(" + str + ")" : str;
}
function fmtPct(v){ return v === null || v === undefined ? "–" : v.toFixed(2) + "%"; }

function handleChipClick(selectedSet, value, evt){
  const multi = evt.ctrlKey || evt.metaKey;
  if (multi){ if (selectedSet.has(value)) selectedSet.delete(value); else selectedSet.add(value); }
  else { if (selectedSet.size === 1 && selectedSet.has(value)) selectedSet.clear(); else { selectedSet.clear(); selectedSet.add(value); } }
  refreshAll();
}
function buildChips(container, options, selectedSet, disabledSet){
  container.innerHTML = "";
  const allBtn = document.createElement("button");
  allBtn.className = "chip" + (selectedSet.size === 0 ? " active" : "");
  allBtn.textContent = "All";
  allBtn.onclick = () => { selectedSet.clear(); refreshAll(); };
  container.appendChild(allBtn);
  options.forEach(opt => {
    const btn = document.createElement("button");
    const isDisabled = disabledSet && disabledSet.has(opt.value) && !selectedSet.has(opt.value);
    btn.className = "chip" + (selectedSet.has(opt.value) ? " active" : "") + (isDisabled ? " disabled" : "");
    btn.textContent = opt.label;
    btn.onclick = (evt) => { if (!isDisabled) handleChipClick(selectedSet, opt.value, evt); };
    container.appendChild(btn);
  });
}
function filteredFacilities({ignore} = {}){
  return DATA.facilities.filter(f =>
    (ignore === "manager" || selManagers.size === 0 || selManagers.has(f.manager)) &&
    (ignore === "landlord" || selLandlords.size === 0 || selLandlords.has(f.landlord)) &&
    (ignore === "facility" || selFacilities.size === 0 || selFacilities.has(f.facility_id))
  );
}
function matchingFacilityIds(){ return new Set(filteredFacilities().map(f => f.facility_id)); }
function availablePeriodsForSelection(){
  const ids = matchingFacilityIds();
  const set = new Set();
  DATA.rows.forEach(r => { if (ids.has(r.facility_id)) set.add(r.period); });
  return Array.from(set).sort();
}
function periodsInRange(){ return availablePeriodsForSelection().filter(p => p >= rangeFrom && p <= rangeTo); }

function populateMonthPickers(){
  const fromSel = document.getElementById("fromMonth");
  const toSel = document.getElementById("toMonth");
  fromSel.innerHTML = ""; toSel.innerHTML = "";
  function fmtMonth(period){
    const [y,m] = period.split("-");
    const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return names[parseInt(m,10)-1] + " '" + y.slice(2);
  }
  window.fmtMonth = fmtMonth;
  PERIODS_ALL.forEach(p => {
    const o1 = document.createElement("option"); o1.value = p; o1.textContent = fmtMonth(p);
    if (p === rangeFrom) o1.selected = true; fromSel.appendChild(o1);
    const o2 = document.createElement("option"); o2.value = p; o2.textContent = fmtMonth(p);
    if (p === rangeTo) o2.selected = true; toSel.appendChild(o2);
  });
  fromSel.onchange = () => { rangeFrom = fromSel.value; if (rangeFrom > rangeTo){ rangeTo = rangeFrom; toSel.value = rangeTo; } renderAll(); };
  toSel.onchange = () => { rangeTo = toSel.value; if (rangeTo < rangeFrom){ rangeFrom = rangeTo; fromSel.value = rangeFrom; } renderAll(); };
  document.getElementById("t3Btn").onclick = () => setTrailingRange(3);
  document.getElementById("t12Btn").onclick = () => setTrailingRange(12);
}
function setTrailingRange(n){
  const avail = availablePeriodsForSelection();
  if (avail.length === 0) return;
  const anchor = avail[avail.length - 1];
  const startIdx = Math.max(0, avail.length - n);
  rangeFrom = avail[startIdx]; rangeTo = anchor;
  document.getElementById("fromMonth").value = rangeFrom;
  document.getElementById("toMonth").value = rangeTo;
  renderAll();
}

// --- package math ----------------------------------------------------------
// The covenant metric is EBIDAR, not EBIDARM -- EBIDAR = EBIDARM minus a
// normalized management-fee add-back of 5% of Operating Revenue (NOT the
// operator's actual reported management fee line). Confirmed against the
// real underwriting model's own measures:
//   Covenant Earnings ([EBIDAR]) = [EBIDARM] - 0.05 * [Total Operating Revenue]
//   Cap Rate Supportable %       = DIVIDE([EBIDAR], [Purchase Price (PO)])
// See PROJECT_RULES.md section 9a.
const MGMT_FEE_ADDBACK_PCT = 0.05;

// Annualized EBIDAR = sum(EBIDAR for months with data) x 12/(months with
// data) -- never a straight-line guess for missing months, just scaling
// what's actually reported so an interim period compares fairly against
// the one-time purchase price. The add-back is linear in revenue, so
// summing per-period EBIDAR across months is equivalent to summing
// EBIDARM and revenue separately and combining once -- done that way here.
function packagesInScope(){
  const ids = matchingFacilityIds();
  return DATA.packages
    .map(pkg => ({...pkg, facility_ids: pkg.facility_ids.filter(fid => ids.has(fid))}))
    .filter(pkg => pkg.facility_ids.length > 0 && pkg.purchase_price !== null && pkg.purchase_price !== undefined);
}
function ebidarFor(row){ return row.ebidarm - MGMT_FEE_ADDBACK_PCT * row.operating_revenue; }

// The lease covenant is a COLLECTIVE, landlord-level test -- Covenant
// Income summed across EVERY facility under that landlord (all manager
// brands together), compared to the ONE rent that landlord itself pays
// its own upstream owner (e.g. Petersen SNF -> CareTrust) -- never a
// per-manager or per-package number, and never the Manager/Landlord/
// Facility filter chips above (those scope the Cap Rate Supportable
// section only). Rolling T12, always, per the lease -- independent of
// the shared month-range picker too.
const MIN_COVERAGE_RATIO = 1.2;
function landlordCovenantTest(landlordRent){
  const facIds = landlordRent.facility_ids;
  const avail = Array.from(new Set(DATA.rows.filter(r => facIds.includes(r.facility_id)).map(r => r.period))).sort();
  const t12 = avail.slice(-12);
  let sum = 0;
  t12.forEach(p => {
    facIds.forEach(fid => {
      const row = ROW_BY_KEY[fid + "|" + p];
      if (row) sum += ebidarFor(row);
    });
  });
  const annualRent = landlordRent.monthly_rent * 12;
  const required = annualRent * MIN_COVERAGE_RATIO;
  return {sum, months: t12.length, annualRent, required, surplus: sum - required};
}
function annualizedEbidar(facIds, periods){
  let sum = 0, monthsWithData = 0;
  const perPeriod = {};
  periods.forEach(p => {
    let v = 0, any = false;
    facIds.forEach(fid => {
      const row = ROW_BY_KEY[fid + "|" + p];
      if (row){ v += ebidarFor(row); any = true; }
    });
    if (any){ perPeriod[p] = v; sum += v; monthsWithData++; }
  });
  const factor = monthsWithData > 0 ? 12 / monthsWithData : null;
  return {sum, monthsWithData, annualized: factor !== null ? sum * factor : null, perPeriod};
}
function supportedLabel(annualized, required){
  if (annualized === null) return null;
  return annualized >= required ? "✓ Supported" : "✗ Shortfall";
}
function drawSpark(svg, vals){
  const clean = vals.filter(v => v !== null && v !== undefined);
  if (clean.length < 2){ svg.innerHTML = ""; return; }
  const w = 160, h = 28, pad = 2;
  const min = Math.min(...clean), max = Math.max(...clean);
  const range = (max - min) || 1;
  const stepX = (w - pad*2) / (vals.length - 1);
  let path = ""; let started = false;
  vals.forEach((v,i) => {
    if (v === null || v === undefined) return;
    const x = pad + i*stepX;
    const y = h - pad - ((v - min) / range) * (h - pad*2);
    path += (started ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1) + " ";
    started = true;
  });
  svg.innerHTML = '<path d="' + path.trim() + '" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
}

function renderCards(pkgs, periods){
  const container = document.getElementById("pkgCards");
  container.innerHTML = "";
  pkgs.forEach(pkg => {
    const {annualized} = annualizedEbidar(pkg.facility_ids, periods);
    const supportable = annualized !== null ? (annualized / pkg.purchase_price) * 100 : null;
    const card = document.createElement("div"); card.className = "op-card";
    const name = document.createElement("div"); name.className = "op-name"; name.textContent = pkg.brand; name.title = pkg.landlord + " — " + pkg.brand;
    const sub = document.createElement("div"); sub.className = "op-sub"; sub.textContent = pkg.landlord;
    card.appendChild(name); card.appendChild(sub);
    if (supportable === null){
      const val = document.createElement("div"); val.className = "op-value no-data"; val.textContent = "No EBIDAR data";
      card.appendChild(val); container.appendChild(card); return;
    }
    const value = document.createElement("div"); value.className = "op-value"; value.textContent = fmtPct(supportable);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class","op-spark"); svg.setAttribute("viewBox","0 0 160 28"); svg.setAttribute("preserveAspectRatio","none");
    const monthlySeries = periods.map(p => {
      let v = 0, any = false;
      pkg.facility_ids.forEach(fid => { const row = ROW_BY_KEY[fid + "|" + p]; if (row){ v += ebidarFor(row); any = true; } });
      return any ? (v * 12 / pkg.purchase_price) * 100 : null;
    });
    drawSpark(svg, monthlySeries);
    card.appendChild(value); card.appendChild(svg);
    container.appendChild(card);
  });
  if (pkgs.length === 0){
    container.innerHTML = '<div style="color:var(--muted);font-size:12px;">No packages with a purchase price match the current filters.</div>';
  }
}

function renderStats(pkgs, periods){
  let totalPrice = 0, totalAnnualized = 0, anyData = false;
  pkgs.forEach(pkg => {
    totalPrice += pkg.purchase_price;
    const {annualized} = annualizedEbidar(pkg.facility_ids, periods);
    if (annualized !== null){ totalAnnualized += annualized; anyData = true; }
  });
  document.getElementById("statPrice").textContent = fmtMoney(totalPrice);
  if (!anyData || pkgs.length === 0){
    document.getElementById("statEbidar").textContent = "–";
    document.getElementById("statSupportable").textContent = "–";
    document.getElementById("statSurplus").textContent = "–";
    document.getElementById("statSupportedLabel").textContent = "–";
    return;
  }
  document.getElementById("statEbidar").textContent = fmtMoney(totalAnnualized);
  document.getElementById("statEbidarFoot").textContent = periods.length + " month" + (periods.length===1?"":"s") + " annualized";
  const supportable = (totalAnnualized / totalPrice) * 100;
  document.getElementById("statSupportable").textContent = fmtPct(supportable);
  const required = totalPrice * (targetRate/100);
  const surplus = totalAnnualized - required;
  const surplusEl = document.getElementById("statSurplus");
  surplusEl.textContent = fmtMoney(surplus);
  surplusEl.className = "stat-value " + (surplus >= 0 ? "good" : "bad");
  const labelEl = document.getElementById("statSupportedLabel");
  labelEl.textContent = supportedLabel(totalAnnualized, required);
  labelEl.className = "stat-value " + (surplus >= 0 ? "good" : "bad");
}

function renderTable(pkgs, periods){
  document.getElementById("requiredHeadCell").textContent = "Required EBIDAR @ " + targetRate.toFixed(2) + "%";
  const body = document.getElementById("pkgBody");
  body.innerHTML = "";
  const allPkgs = DATA.packages; // show every known package the filter would include, even with 0 matching facilities left out already by caller
  pkgs.forEach(pkg => {
    const {annualized} = annualizedEbidar(pkg.facility_ids, periods);
    const tr = document.createElement("tr");
    const labelTd = document.createElement("td"); labelTd.className = "linecell";
    labelTd.innerHTML = pkg.brand + '<span class="pkg-sub">' + pkg.landlord + ' · ' + pkg.facility_ids.length + ' facilit' + (pkg.facility_ids.length===1?'y':'ies') + '</span>';
    tr.appendChild(labelTd);
    const priceTd = document.createElement("td"); priceTd.textContent = fmtMoney(pkg.purchase_price); tr.appendChild(priceTd);
    if (annualized === null){
      const td = document.createElement("td"); td.textContent = "–"; td.colSpan = 5; tr.appendChild(td);
      body.appendChild(tr); return;
    }
    const ebidarTd = document.createElement("td"); ebidarTd.textContent = fmtMoney(annualized); tr.appendChild(ebidarTd);
    const supportable = (annualized / pkg.purchase_price) * 100;
    const suppTd = document.createElement("td"); suppTd.textContent = fmtPct(supportable); tr.appendChild(suppTd);
    const required = pkg.purchase_price * (targetRate/100);
    const reqTd = document.createElement("td"); reqTd.textContent = fmtMoney(required); tr.appendChild(reqTd);
    const surplus = annualized - required;
    const surplusTd = document.createElement("td"); surplusTd.textContent = fmtMoney(surplus); surplusTd.classList.add(surplus >= 0 ? "pos" : "neg");
    tr.appendChild(surplusTd);
    const statusTd = document.createElement("td"); statusTd.textContent = supportedLabel(annualized, required); statusTd.classList.add(surplus >= 0 ? "pos" : "neg");
    tr.appendChild(statusTd);
    body.appendChild(tr);
  });

  // Facilities in scope whose landlord/brand has no purchase price at all.
  const covered = new Set();
  pkgs.forEach(pkg => pkg.facility_ids.forEach(fid => covered.add(fid)));
  const uncoveredByGroup = {};
  filteredFacilities().forEach(f => {
    if (covered.has(f.facility_id)) return;
    const key = f.landlord + " · " + f.manager;
    uncoveredByGroup[key] = (uncoveredByGroup[key] || 0) + 1;
  });
  Object.entries(uncoveredByGroup).forEach(([key, n]) => {
    const tr = document.createElement("tr"); tr.className = "no-price-row";
    const td = document.createElement("td"); td.className = "linecell"; td.colSpan = 7;
    td.textContent = key + " — no purchase price data (" + n + " facilit" + (n===1?"y":"ies") + ")";
    tr.appendChild(td); body.appendChild(tr);
  });

  if (pkgs.length === 0 && Object.keys(uncoveredByGroup).length === 0){
    const tr = document.createElement("tr");
    const td = document.createElement("td"); td.className = "linecell"; td.textContent = "No facilities match the current filters."; tr.appendChild(td);
    body.appendChild(tr);
  }
}

function renderSensitivity(pkgs, periods){
  const head = document.getElementById("sensHead"); const body = document.getElementById("sensBody");
  head.innerHTML = ""; body.innerHTML = "";
  const lineTh = document.createElement("th"); lineTh.className = "linecol"; lineTh.textContent = "Package"; head.appendChild(lineTh);
  SENS_RATES.forEach(r => { const th = document.createElement("th"); th.textContent = r.toFixed(2) + "%"; head.appendChild(th); });

  if (pkgs.length === 0){
    const tr = document.createElement("tr"); const td = document.createElement("td"); td.className="linecell"; td.textContent="No packages match the current filters."; tr.appendChild(td); body.appendChild(tr); return;
  }
  pkgs.forEach(pkg => {
    const {annualized} = annualizedEbidar(pkg.facility_ids, periods);
    const tr = document.createElement("tr");
    const labelTd = document.createElement("td"); labelTd.className = "linecell";
    labelTd.innerHTML = pkg.brand + '<span class="pkg-sub">' + pkg.landlord + '</span>';
    tr.appendChild(labelTd);
    SENS_RATES.forEach(rate => {
      const td = document.createElement("td");
      if (annualized === null){ td.textContent = "–"; tr.appendChild(td); return; }
      const required = pkg.purchase_price * (rate/100);
      const surplus = annualized - required;
      td.textContent = fmtMoney(surplus);
      td.classList.add(surplus >= 0 ? "pos" : "neg");
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

// A single collective total vs. target per landlord -- no per-manager or
// per-package breakdown, since the lease covenant isn't evaluated that
// way (an individual operator's own number doesn't matter to CareTrust,
// only the combined total does).
function renderCovenantSections(){
  const container = document.getElementById("covenantSections");
  container.innerHTML = "";
  if (DATA.landlord_rents.length === 0){
    container.innerHTML = '<div class="section"><p class="filter-hint" style="padding-left:0;">No lease rent data on file yet.</p></div>';
    return;
  }
  DATA.landlord_rents.forEach(lr => {
    const {sum, months, annualRent, required, surplus} = landlordCovenantTest(lr);
    const met = surplus >= 0;
    const section = document.createElement("div");
    section.className = "section";
    section.innerHTML =
      '<div class="section-head"><h2>Lease Covenant Test &mdash; ' + lr.landlord + '</h2>' +
      '<span class="section-note">Rolling T12 Covenant Income (EBIDAR), all ' + lr.facility_ids.length + ' facilities combined, vs. ' + MIN_COVERAGE_RATIO.toFixed(1) + '&times; the rent ' + lr.landlord + ' pays CareTrust &mdash; always trailing 12 months</span></div>' +
      '<div class="stat-strip">' +
        '<div class="stat-card"><span class="stat-label">Monthly rent to CareTrust</span><span class="stat-value">' + fmtMoney(lr.monthly_rent) + '</span><span class="stat-foot">on file</span></div>' +
        '<div class="stat-card"><span class="stat-label">Annual rent</span><span class="stat-value">' + fmtMoney(annualRent) + '</span><span class="stat-foot">12 &times; monthly rent</span></div>' +
        '<div class="stat-card"><span class="stat-label">Required covenant income</span><span class="stat-value">' + fmtMoney(required) + '</span><span class="stat-foot">' + MIN_COVERAGE_RATIO.toFixed(1) + '&times; annual rent</span></div>' +
        '<div class="stat-card"><span class="stat-label">T12 covenant income</span><span class="stat-value' + (months > 0 ? ' clickable" onclick="openCovenantDrill(' + lr.landlord_id + ')' : '') + '">' + (months > 0 ? fmtMoney(sum) : "–") + '</span><span class="stat-foot">' + (months < 12 ? "only " + months + " month" + (months===1?"":"s") + " of data" : "actual, rolling T12 — click for detail") + '</span></div>' +
        '<div class="stat-card"><span class="stat-label">Surplus / (shortfall)</span><span class="stat-value ' + (met ? "good" : "bad") + '">' + (months > 0 ? fmtMoney(surplus) : "–") + '</span><span class="stat-foot">vs. required</span></div>' +
        '<div class="stat-card"><span class="stat-label">Covenant Status</span><span class="stat-value ' + (met ? "good" : "bad") + '">' + (months > 0 ? (met ? "✓ Met" : "✗ Breach") : "–") + '</span><span class="stat-foot">a breach triggers a lease penalty</span></div>' +
      '</div>' +
      '<div class="penalty-note">&#9888;&#65039; This is a collective measure across every facility ' + lr.landlord + ' operates &mdash; not any one manager or package. A "Breach" means rolling T12 covenant income fell short of ' + MIN_COVERAGE_RATIO.toFixed(1) + '&times; the annual rent ' + lr.landlord + ' itself pays CareTrust (not what it collects from operators), which triggers a financial penalty under the lease.</div>';
    container.appendChild(section);
  });
}

// Verification detail for the T12 covenant income total ONLY -- by month
// and by manager, both summing to the same headline figure. No per-
// manager pass/fail here (the covenant itself is collective, not
// per-operator); this is purely for tracing the number, not a second
// compliance check.
function openCovenantDrill(landlordId){
  const lr = DATA.landlord_rents.find(x => x.landlord_id === landlordId);
  if (!lr) return;
  const facIds = lr.facility_ids;
  const avail = Array.from(new Set(DATA.rows.filter(r => facIds.includes(r.facility_id)).map(r => r.period))).sort();
  const t12 = avail.slice(-12);

  const byPeriod = t12.map(p => {
    let v = 0;
    facIds.forEach(fid => { const row = ROW_BY_KEY[fid + "|" + p]; if (row) v += ebidarFor(row); });
    return {label: window.fmtMonth ? window.fmtMonth(p) : p, amount: v};
  });

  const managerOf = {};
  DATA.facilities.forEach(f => { managerOf[f.facility_id] = f.manager; });
  const byManagerMap = {};
  facIds.forEach(fid => {
    const mgr = managerOf[fid] || "Unknown";
    t12.forEach(p => {
      const row = ROW_BY_KEY[fid + "|" + p];
      if (row) byManagerMap[mgr] = (byManagerMap[mgr] || 0) + ebidarFor(row);
    });
  });
  const byManager = Object.entries(byManagerMap).sort((a, b) => b[1] - a[1]);

  const total = byPeriod.reduce((s, x) => s + x.amount, 0);

  document.getElementById("drillTitle").textContent = "T12 Covenant Income — " + lr.landlord;
  document.getElementById("drillSub").textContent = (t12.length ? byPeriod[0].label + " – " + byPeriod[byPeriod.length - 1].label : "no data") + " · " + facIds.length + " facilities";

  const bodyEl = document.getElementById("drillBody");
  bodyEl.innerHTML = "";

  const monthHead = document.createElement("div"); monthHead.className = "drill-section-head"; monthHead.textContent = "By Month";
  bodyEl.appendChild(monthHead);
  byPeriod.forEach(({label, amount}) => {
    const row = document.createElement("div"); row.className = "drill-row";
    row.innerHTML = '<div class="name">' + label + '</div><div class="amt' + (amount < 0 ? " neg" : "") + '">' + fmtMoney(amount) + '</div>';
    bodyEl.appendChild(row);
  });
  const monthTotal = document.createElement("div"); monthTotal.className = "drill-row total";
  monthTotal.innerHTML = '<div>Total (T12)</div><div class="amt">' + fmtMoney(total) + '</div>';
  bodyEl.appendChild(monthTotal);

  const mgrHead = document.createElement("div"); mgrHead.className = "drill-section-head"; mgrHead.textContent = "By Manager";
  bodyEl.appendChild(mgrHead);
  byManager.forEach(([mgr, amount]) => {
    const row = document.createElement("div"); row.className = "drill-row";
    row.innerHTML = '<div class="name">' + mgr + '</div><div class="amt' + (amount < 0 ? " neg" : "") + '">' + fmtMoney(amount) + '</div>';
    bodyEl.appendChild(row);
  });
  const mgrTotal = document.createElement("div"); mgrTotal.className = "drill-row total";
  mgrTotal.innerHTML = '<div>Total (T12)</div><div class="amt">' + fmtMoney(total) + '</div>';
  bodyEl.appendChild(mgrTotal);

  document.getElementById("drillBackdrop").hidden = false;
}
function closeDrill(){ document.getElementById("drillBackdrop").hidden = true; }
document.getElementById("drillClose").onclick = closeDrill;
document.getElementById("drillBackdrop").onclick = (e) => { if (e.target.id === "drillBackdrop") closeDrill(); };
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrill(); });

const FACILITY_OPTIONS = DATA.facilities.slice().sort((a,b) => a.name.localeCompare(b.name)).map(f => ({value: f.facility_id, label: f.name}));
const MANAGER_OPTIONS = MANAGERS.map(m => ({value: m, label: m}));
const LANDLORD_OPTIONS = LANDLORDS.map(l => ({value: l, label: l}));

function refreshAll(){
  const availManagers = new Set(filteredFacilities({ignore:"manager"}).map(f => f.manager));
  const availLandlords = new Set(filteredFacilities({ignore:"landlord"}).map(f => f.landlord));
  const availFacilityIds = new Set(filteredFacilities({ignore:"facility"}).map(f => f.facility_id));
  Array.from(selManagers).forEach(m => { if (!availManagers.has(m)) selManagers.delete(m); });
  Array.from(selLandlords).forEach(l => { if (!availLandlords.has(l)) selLandlords.delete(l); });
  Array.from(selFacilities).forEach(id => { if (!availFacilityIds.has(id)) selFacilities.delete(id); });
  buildChips(document.getElementById("managerChips"), MANAGER_OPTIONS, selManagers, new Set(MANAGERS.filter(m => !availManagers.has(m))));
  buildChips(document.getElementById("landlordChips"), LANDLORD_OPTIONS, selLandlords, new Set(LANDLORDS.filter(l => !availLandlords.has(l))));
  buildChips(document.getElementById("facilityChips"), FACILITY_OPTIONS, selFacilities, new Set(FACILITY_OPTIONS.map(o => o.value).filter(id => !availFacilityIds.has(id))));
  renderAll();
}
function renderAll(){
  const pkgs = packagesInScope();
  const periods = periodsInRange();
  renderCards(pkgs, periods);
  renderStats(pkgs, periods);
  renderTable(pkgs, periods);
  renderSensitivity(pkgs, periods);
}

document.getElementById("rateSlider").oninput = (e) => {
  targetRate = parseFloat(e.target.value);
  document.getElementById("rateValue").textContent = targetRate.toFixed(2) + "%";
  renderAll();
};

renderCovenantSections();
populateMonthPickers();
refreshAll();
</script>
"""

HTML = HTML.replace("__DATA_JSON__", data_json)
HTML = HTML.replace("__MANAGERS_JSON__", json.dumps(managers))
HTML = HTML.replace("__LANDLORDS_JSON__", json.dumps(landlords))

out_path = SCRATCH / "covenant.html"
out_path.write_text(HTML)
print("wrote", out_path, len(HTML), "bytes")
