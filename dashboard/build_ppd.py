import json, pathlib

SCRATCH = pathlib.Path(__file__).parent
data = json.loads((SCRATCH / "ppd_data.json").read_text())

managers = sorted(set(f["manager"] for f in data["facilities"]))
landlords = sorted(set(f["landlord"] for f in data["facilities"]))

data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

HTML = r"""<title>Revenue &amp; Expense PPD</title>
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

.section{display:flex; flex-direction:column; gap:14px;}
.section-head{display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap;}
.section-head h2{font-size:19px; font-weight:600;}
.section-head .section-note{font-size:12px; color:var(--muted);}

.card-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(168px,1fr)); gap:12px;}
.op-card{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:13px 14px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px;}
.op-card .op-name{font-size:12.5px; font-weight:600; color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.op-card .op-value{font-family:"IBM Plex Mono",monospace; font-size:20px; font-weight:600; font-variant-numeric:tabular-nums;}
.op-card .op-value.no-data{font-family:"IBM Plex Sans",sans-serif; font-size:12.5px; font-weight:500; color:var(--muted); font-style:italic;}
.no-census-badge{font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--warn); background:var(--warn-soft); border-radius:5px; padding:1px 6px; margin-left:7px; vertical-align:1px;}
.op-card .op-delta{font-size:11px; display:flex; align-items:center; gap:3px;}
.op-card .op-delta.up{color:var(--bad);} .op-card .op-delta.down{color:var(--good);} .op-card .op-delta.flat{color:var(--muted);}
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

tr.manager-row td{font-weight:600; color:var(--ink);}
tr.manager-row td.linecell{background:var(--surface);}
tr.sub td.linecell{padding-left:32px; color:var(--muted); font-size:12.5px;}
tr.sub td{color:var(--muted); font-size:12.5px;}
tr.sub{display:none;}
tr.sub.show{display:table-row;}

.expand-btn{
  background:none; border:none; cursor:pointer; padding:0; margin-right:6px;
  color:var(--muted); font-size:11px; display:inline-flex; align-items:center; justify-content:center;
  width:14px; transition:transform .15s;
}
.expand-btn.open{transform:rotate(90deg);}

.toggle-group{display:inline-flex; border:1px solid var(--border); border-radius:8px; overflow:hidden;}
.toggle-btn{
  font-family:inherit; font-size:12.5px; font-weight:600; color:var(--ink-soft);
  background:var(--surface-2); border:none; padding:6px 13px; cursor:pointer;
}
.toggle-btn + .toggle-btn{border-left:1px solid var(--border);}
.toggle-btn.active{background:var(--accent); color:var(--surface);}

tbody td.clickable{cursor:pointer;}
tbody td.clickable:hover{box-shadow:inset 0 0 0 1px var(--accent);}

.footnote{font-size:11.5px; color:var(--muted); line-height:1.5; padding:2px 4px;}

.drill-backdrop{
  position:fixed; inset:0; background:rgba(20,28,26,.45); display:flex;
  align-items:center; justify-content:center; padding:20px; z-index:50;
}
.drill-card{
  background:var(--surface); border:1px solid var(--border); border-radius:14px;
  box-shadow:var(--shadow); max-width:560px; width:100%; max-height:82vh;
  display:flex; flex-direction:column; overflow:hidden;
}
.drill-head{display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:16px 18px 12px; border-bottom:1px solid var(--border);}
.drill-title{font-family:"Fraunces",serif; font-size:16px; font-weight:600; color:var(--ink);}
.drill-sub{font-size:12px; color:var(--muted); margin-top:2px;}
.drill-close{background:none; border:none; font-size:18px; line-height:1; color:var(--muted); cursor:pointer; padding:2px 4px;}
.drill-close:hover{color:var(--ink);}
.drill-body{overflow-y:auto; padding:6px 0;}
.drill-row{display:flex; justify-content:space-between; align-items:center; gap:10px; padding:8px 18px; font-size:13px; border-bottom:1px solid var(--border); cursor:pointer;}
.drill-row:hover{background:var(--surface-2);}
.drill-row:last-child{border-bottom:none;}
.drill-row .name{color:var(--ink); font-weight:500; display:flex; align-items:center; gap:6px;}
.drill-row .meta{color:var(--muted); font-size:11.5px; font-weight:400;}
.drill-row .amt{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; color:var(--ink-soft); white-space:nowrap;}
.drill-row .amt .ppd{color:var(--muted); font-size:11px; margin-left:6px;}
.drill-row .amt.neg{color:var(--bad);}
.drill-row.total{background:var(--surface-2); font-weight:700; cursor:default;}
.drill-row.total .amt{color:var(--ink); font-weight:700;}
.drill-row.total:hover{background:var(--surface-2);}
.gl-panel{padding:2px 18px 10px 40px; border-bottom:1px solid var(--border); display:none; background:var(--surface-2);}
.gl-panel.show{display:block;}
.gl-line{display:flex; justify-content:space-between; gap:10px; font-size:12px; padding:4px 0; color:var(--ink-soft);}
.gl-line .amt{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums;}
.gl-line .amt.neg{color:var(--bad);}
.gl-more{font-size:11.5px; color:var(--muted); padding:4px 0 2px;}
.gl-empty{font-size:12px; color:var(--muted); padding:6px 0;}
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="wrap">
  <div class="masthead">
    <span class="eyebrow">Kesser Financial Dashboard</span>
    <h1>Revenue &amp; Expense PPD</h1>
    <p class="sub">Dollars per resident day, by operator. Both views share the same filters and month range below &mdash; click any number to see which facilities make it up, then click a facility to see the GL accounts behind it.</p>
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
    <div class="filter-row">
      <span class="filter-label">View</span>
      <span class="toggle-group" role="group" aria-label="View mode">
        <button class="toggle-btn active" id="viewPpdBtn" type="button">Per Resident Day</button>
        <button class="toggle-btn" id="viewTotalBtn" type="button">Total $</button>
      </span>
    </div>
    <p class="filter-hint">Click a chip to select it on its own. Ctrl/Cmd-click to add it to the current selection. Click any number below to see the facilities behind it, then click a facility to drill into its GL accounts. "Total $" doesn't need a census day count, so it's the baseline to compare an operator like Aliya (no census file loaded yet) against the rest on equal footing.</p>
  </div>

  <div class="section">
    <div class="section-head">
      <h2>Expense PPD by Operator</h2>
      <span class="section-note" id="expenseNote">Operating expense (excludes G&amp;A and Management Fees) &divide; total resident days</span>
    </div>
    <div class="card-grid" id="expenseCards"></div>
    <div class="table-card">
      <div class="table-scroll">
        <table id="expenseTable">
          <thead><tr id="expenseHead"></tr></thead>
          <tbody id="expenseBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-head">
      <h2>Revenue PPD by Operator</h2>
      <span class="section-note" id="revenueNote">Resident income &divide; total resident days, by payor</span>
    </div>
    <div class="card-grid" id="revenueCards"></div>
    <div class="table-card">
      <div class="table-scroll">
        <table id="revenueTable">
          <thead><tr id="revenueHead"></tr></thead>
          <tbody id="revenueBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <p class="footnote">PPD figures are $ per resident day, computed as total dollars &divide; total resident days for the group shown (never an average of monthly PPDs), so multi-month columns stay mathematically consistent. The rightmost "Avg" column is weighted the same way across the selected months. Expense department rows divide by the facility's total census, since departments serve every resident regardless of payor &mdash; but each Revenue payor row (Medicaid, Medicare, etc.) divides by that SAME payor's own census days, not total census, so a Medicare rate isn't diluted by the facility's Medicaid/Private residents. "Other" (Revenue) covers the few payor lines with no matching census breakdown to divide against and falls back to total census days. GL amounts in the drill-down panel are the underlying dollars for that line, not PPD. Aliya shows "no census data" &mdash; no census file has been loaded for its facilities yet (a known gap, tracked in PROJECT_RULES.md), so no PPD can be computed for it until one is provided. Allure of Walnut's own source file had its per-payor "Patient Days" corrupted (copy-pasted from its Revenue $ rows); the corrupted payor rows are dropped and folded into "Other" using the correct total instead &mdash; see PROJECT_RULES.md section 8.</p>
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

const PERIODS_ALL = DATA.periods.slice();
const PERIOD_IDX = {}; PERIODS_ALL.forEach((p,i) => PERIOD_IDX[p] = i);

const EXPENSE_DEPT_ORDER = ["Nursing","Ancillary","Activities","Social Service","Dietary","Housekeeping","Laundry and Linen","Employee Welfare","Plant","Marketing"];
const REVENUE_PAYOR_ORDER = ["Medicaid","Managed Medicaid","Medicare","Managed Medicare","Medicare B","Private","Insurance/Commercial","Veterans","Hospice","Assisted Living","Independent Living","Other"];

let selManagers = new Set();
let selLandlords = new Set();
let selFacilities = new Set();
let rangeFrom = PERIODS_ALL[0];
let rangeTo = PERIODS_ALL[PERIODS_ALL.length - 1];
let expandedExpense = new Set();  // manager names currently expanded
let expandedRevenue = new Set();
let viewMode = "ppd";  // "ppd" | "total" -- see metricValue/fmtMetric

function fmtMonth(period){
  const [y,m] = period.split("-");
  const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return names[parseInt(m,10)-1] + " '" + y.slice(2);
}
function fmtPPD(v){
  if (v === null || v === undefined) return "–";
  const abs = Math.abs(v);
  const str = "$" + abs.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2});
  return v < 0 ? "(" + str + ")" : str;
}
function fmtDollarK(v){
  if (v === null || v === undefined) return "–";
  const k = v/1000;
  const abs = Math.abs(k);
  const str = abs.toLocaleString(undefined,{maximumFractionDigits:1, minimumFractionDigits:1});
  return v < 0 ? "(" + str + "K)" : "$" + str + "K";
}

// Total $ needs no census day count at all, so it's the one baseline that
// still works for an operator like Aliya (no census file loaded yet) --
// PPD falls back to "–" for it, Total $ shows the real dollars.
function metricValue(facIds, periods, picker, daysPicker){
  const {dollars, ppd} = sumForFacilities(facIds, periods, picker, daysPicker);
  if (viewMode === "total"){
    const anyRow = facIds.some(fid => periods.some(p => !!ROW_BY_KEY[fid + "|" + p]));
    return anyRow ? dollars : null;
  }
  return ppd;
}
function fmtMetric(v){
  return viewMode === "total" ? fmtDollarK(v) : fmtPPD(v);
}
function setViewMode(mode){
  if (mode === viewMode) return;
  viewMode = mode;
  document.getElementById("viewPpdBtn").classList.toggle("active", mode === "ppd");
  document.getElementById("viewTotalBtn").classList.toggle("active", mode === "total");
  updateSectionNotes();
  renderAll();
}
function updateSectionNotes(){
  document.getElementById("expenseNote").textContent = viewMode === "total"
    ? "Total operating expense (excludes G&A and Management Fees), summed for the selected months"
    : "Operating expense (excludes G&A and Management Fees) ÷ total resident days";
  document.getElementById("revenueNote").textContent = viewMode === "total"
    ? "Total resident income, summed for the selected months, by payor"
    : "Resident income ÷ total resident days, by payor";
}
document.getElementById("viewPpdBtn").onclick = () => setViewMode("ppd");
document.getElementById("viewTotalBtn").onclick = () => setViewMode("total");

function handleChipClick(selectedSet, value, evt){
  const multi = evt.ctrlKey || evt.metaKey;
  if (multi){
    if (selectedSet.has(value)) selectedSet.delete(value); else selectedSet.add(value);
  } else {
    if (selectedSet.size === 1 && selectedSet.has(value)) selectedSet.clear();
    else { selectedSet.clear(); selectedSet.add(value); }
  }
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

function populateMonthPickers(){
  const fromSel = document.getElementById("fromMonth");
  const toSel = document.getElementById("toMonth");
  fromSel.innerHTML = ""; toSel.innerHTML = "";
  PERIODS_ALL.forEach(p => {
    const o1 = document.createElement("option");
    o1.value = p; o1.textContent = fmtMonth(p);
    if (p === rangeFrom) o1.selected = true;
    fromSel.appendChild(o1);
    const o2 = document.createElement("option");
    o2.value = p; o2.textContent = fmtMonth(p);
    if (p === rangeTo) o2.selected = true;
    toSel.appendChild(o2);
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

// --- aggregation helpers -------------------------------------------------
// PPD is always sum(dollars)/sum(days), never an average of per-period PPDs.
// daysPicker defaults to the facility's TOTAL census days (right for expense
// departments and the revenue total, since expenses and blended revenue
// both relate to the whole census) -- but a revenue PAYOR row must divide by
// that SAME payor's own census days, or a Medicare row ends up massively
// diluted by every non-Medicare resident-day too. See daysPickerFor.
function sumForFacilities(facIds, periods, picker, daysPicker){
  daysPicker = daysPicker || (row => row.resident_days || 0);
  let dollars = 0, days = 0;
  facIds.forEach(fid => {
    periods.forEach(p => {
      const row = ROW_BY_KEY[fid + "|" + p];
      if (!row) return;
      dollars += picker(row);
      days += daysPicker(row);
    });
  });
  return {dollars, days, ppd: days > 0 ? dollars / days : null};
}

function daysPickerFor(section, sub){
  if (section === "revenue" && sub){
    return row => (row.resident_days_by_payor[sub] || 0);
  }
  return row => row.resident_days || 0;
}

function periodsInRange(){
  return availablePeriodsForSelection().filter(p => p >= rangeFrom && p <= rangeTo);
}

function managersInScope(){
  const facs = filteredFacilities();
  return Array.from(new Set(facs.map(f => f.manager))).sort();
}

function facilitiesForManager(managerName){
  return filteredFacilities().filter(f => f.manager === managerName).map(f => f.facility_id);
}

function subgroupsFor(section){
  return section === "expense" ? EXPENSE_DEPT_ORDER : REVENUE_PAYOR_ORDER;
}
function pickerFor(section, sub){
  if (section === "expense"){
    return sub ? (row => (row.expense_by_dept[sub] || 0)) : (row => row.expense_total || 0);
  }
  return sub ? (row => (row.revenue_by_payor[sub] || 0)) : (row => row.revenue_total || 0);
}

// --- rendering ------------------------------------------------------------
function renderCards(section, containerId){
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  const managers = managersInScope();
  const periods = periodsInRange();
  const picker = pickerFor(section, null);
  managers.forEach(mgr => {
    const facIds = facilitiesForManager(mgr);
    const series = periods.map(p => metricValue(facIds, [p], picker));
    const hasAnyData = series.some(v => v !== null);
    // Each card shows ITS OWN latest reported month, not just the last
    // column in the shared grid -- under "All", the grid's last column is
    // whichever operator has reported furthest, and a different operator
    // that hasn't reported that far yet would otherwise show a blank
    // "latest" value despite having perfectly good, slightly older data.
    let latestIdx = -1;
    for (let i = series.length - 1; i >= 0; i--){ if (series[i] !== null){ latestIdx = i; break; } }
    const latest = latestIdx === -1 ? null : series[latestIdx];
    const prev = latestIdx > 0 ? series[latestIdx - 1] : null;

    const card = document.createElement("div");
    card.className = "op-card";
    const name = document.createElement("div");
    name.className = "op-name"; name.title = mgr;
    name.textContent = mgr;
    const value = document.createElement("div");
    if (!hasAnyData){
      value.className = "op-value no-data";
      value.textContent = viewMode === "total" ? "No data" : "No census data";
      card.appendChild(name);
      card.appendChild(value);
      container.appendChild(card);
      return;
    }
    value.className = "op-value";
    value.textContent = latest === null ? "–" : fmtMetric(latest);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "op-spark"); svg.setAttribute("viewBox", "0 0 160 28"); svg.setAttribute("preserveAspectRatio", "none");
    drawSpark(svg, series);
    const delta = document.createElement("div");
    if (latest !== null && prev !== null && prev !== 0){
      const pct = ((latest - prev) / Math.abs(prev)) * 100;
      const worse = section === "expense" ? pct > 0.5 : pct < -0.5;
      const better = section === "expense" ? pct < -0.5 : pct > 0.5;
      delta.className = "op-delta " + (worse ? "up" : better ? "down" : "flat");
      delta.textContent = (pct >= 0 ? "▲ " : "▼ ") + Math.abs(pct).toFixed(1) + "% vs prior mo.";
    } else {
      delta.className = "op-delta flat";
      delta.textContent = "—";
    }
    card.appendChild(name);
    card.appendChild(value);
    card.appendChild(svg);
    card.appendChild(delta);
    container.appendChild(card);
  });
  if (managers.length === 0){
    container.innerHTML = '<div class="gl-empty">No operators match the current filters.</div>';
  }
}

function drawSpark(svg, vals){
  const clean = vals.filter(v => v !== null);
  if (clean.length < 2){ svg.innerHTML = ""; return; }
  const w = 160, h = 28, pad = 2;
  const min = Math.min(...clean), max = Math.max(...clean);
  const range = (max - min) || 1;
  const stepX = (w - pad*2) / (vals.length - 1);
  let path = ""; let started = false;
  vals.forEach((v,i) => {
    if (v === null) return;
    const x = pad + i*stepX;
    const y = h - pad - ((v - min) / range) * (h - pad*2);
    path += (started ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1) + " ";
    started = true;
  });
  svg.innerHTML = '<path d="' + path.trim() + '" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
}

function renderTable(section, headId, bodyId, expandedSet){
  const head = document.getElementById(headId);
  const body = document.getElementById(bodyId);
  head.innerHTML = ""; body.innerHTML = "";
  const managers = managersInScope();
  const periods = periodsInRange();
  const subs = subgroupsFor(section);

  const lineTh = document.createElement("th");
  lineTh.className = "linecol"; lineTh.textContent = "Operator";
  head.appendChild(lineTh);
  periods.forEach(p => { const th = document.createElement("th"); th.textContent = fmtMonth(p); head.appendChild(th); });
  const avgTh = document.createElement("th"); avgTh.textContent = "Avg"; head.appendChild(avgTh);

  if (managers.length === 0){
    const tr = document.createElement("tr");
    const td = document.createElement("td"); td.className = "linecell"; td.textContent = "No operators match the current filters.";
    tr.appendChild(td); body.appendChild(tr);
    return;
  }

  managers.forEach(mgr => {
    const facIds = facilitiesForManager(mgr);
    const picker0 = pickerFor(section, null);
    // Total $ needs no census at all, so the "no census data" badge only
    // applies in PPD mode -- Total $ is exactly the view that still works
    // for an operator with no census file loaded.
    const hasCensus = viewMode === "total" ? true : periods.some(p => sumForFacilities(facIds, [p], picker0).days > 0);

    const tr = document.createElement("tr"); tr.className = "manager-row";
    const labelTd = document.createElement("td"); labelTd.className = "linecell";
    const btn = document.createElement("button");
    btn.className = "expand-btn" + (expandedSet.has(mgr) ? " open" : "");
    btn.textContent = "▸";
    btn.onclick = () => { if (expandedSet.has(mgr)) expandedSet.delete(mgr); else expandedSet.add(mgr); renderTable(section, headId, bodyId, expandedSet); };
    labelTd.appendChild(btn); labelTd.appendChild(document.createTextNode(mgr));
    if (!hasCensus){
      const badge = document.createElement("span");
      badge.className = "no-census-badge"; badge.textContent = "no census data";
      labelTd.appendChild(badge);
    }
    tr.appendChild(labelTd);

    const picker = pickerFor(section, null);
    periods.forEach(p => {
      const v = metricValue(facIds, [p], picker);
      const td = document.createElement("td"); td.textContent = fmtMetric(v); td.classList.add("clickable");
      td.onclick = () => openDrill(section, mgr, null, p);
      tr.appendChild(td);
    });
    const avgV = metricValue(facIds, periods, picker);
    const avgTd = document.createElement("td"); avgTd.textContent = fmtMetric(avgV); avgTd.classList.add("clickable");
    avgTd.onclick = () => openDrill(section, mgr, null, "TOTAL", periods);
    tr.appendChild(avgTd);
    body.appendChild(tr);

    subs.forEach(sub => {
      const subPicker = pickerFor(section, sub);
      const subDays = daysPickerFor(section, sub);
      const hasAny = periods.some(p => sumForFacilities(facIds, [p], subPicker, subDays).dollars !== 0);
      if (!hasAny) return;
      const str = document.createElement("tr");
      str.className = "sub" + (expandedSet.has(mgr) ? " show" : "");
      const stl = document.createElement("td"); stl.className = "linecell"; stl.textContent = sub;
      str.appendChild(stl);
      periods.forEach(p => {
        const v = metricValue(facIds, [p], subPicker, subDays);
        const td = document.createElement("td"); td.textContent = fmtMetric(v); td.classList.add("clickable");
        td.onclick = () => openDrill(section, mgr, sub, p);
        str.appendChild(td);
      });
      const avgSubV = metricValue(facIds, periods, subPicker, subDays);
      const avgTd2 = document.createElement("td"); avgTd2.textContent = fmtMetric(avgSubV); avgTd2.classList.add("clickable");
      avgTd2.onclick = () => openDrill(section, mgr, sub, "TOTAL", periods);
      str.appendChild(avgTd2);
      body.appendChild(str);
    });
  });
}

// --- drill-down: Tier 1 = facilities under the manager, Tier 2 (click a
// facility) = the GL account lines behind that facility's number.
function openDrill(section, managerName, sub, period, totalPeriods){
  const facIds = facilitiesForManager(managerName);
  const periods = period === "TOTAL" ? totalPeriods : [period];
  const picker = pickerFor(section, sub);
  const daysPicker = daysPickerFor(section, sub);
  const groupPrefix = section === "expense" ? "E:" : "R:";
  const groupKey = sub ? groupPrefix + sub : null;

  const list = facIds.map(fid => {
    const {dollars, days, ppd} = sumForFacilities([fid], periods, picker, daysPicker);
    return {facility: facilityById[fid], dollars, days, ppd};
  }).filter(x => x.days > 0 || x.dollars !== 0).sort((a,b) => (b.ppd||0) - (a.ppd||0));

  const totalAgg = sumForFacilities(facIds, periods, picker, daysPicker);

  document.getElementById("drillTitle").textContent = managerName + (sub ? " – " + sub : "");
  document.getElementById("drillSub").textContent =
    (period === "TOTAL" ? "Avg, " + fmtMonth(periods[0]) + " – " + fmtMonth(periods[periods.length-1]) : fmtMonth(period))
    + " · by facility · click a facility for GL detail";

  const bodyEl = document.getElementById("drillBody");
  bodyEl.innerHTML = "";
  list.forEach(x => {
    const row = document.createElement("div");
    row.className = "drill-row";
    const left = document.createElement("div");
    left.innerHTML = '<span class="expand-btn" style="width:10px;">▸</span><div><div class="name">' + x.facility.name + '</div><div class="meta">' + x.facility.landlord + '</div></div>';
    const amt = document.createElement("div");
    amt.className = "amt";
    amt.innerHTML = fmtPPD(x.ppd) + '<span class="ppd">' + fmtDollarK(x.dollars) + '</span>';
    row.appendChild(left); row.appendChild(amt);

    const glPanel = document.createElement("div");
    glPanel.className = "gl-panel";
    let glLoaded = false;
    row.onclick = () => {
      const chev = left.querySelector(".expand-btn");
      const willShow = !glPanel.classList.contains("show");
      glPanel.classList.toggle("show", willShow);
      chev.classList.toggle("open", willShow);
      if (willShow && !glLoaded){ renderGlDetail(glPanel, x.facility.facility_id, periods, groupPrefix, groupKey); glLoaded = true; }
    };
    bodyEl.appendChild(row);
    bodyEl.appendChild(glPanel);
  });

  const totalRow = document.createElement("div");
  totalRow.className = "drill-row total";
  totalRow.innerHTML = '<div>Total</div>';
  const totalAmt = document.createElement("div");
  totalAmt.className = "amt";
  totalAmt.innerHTML = fmtPPD(totalAgg.ppd) + '<span class="ppd">' + fmtDollarK(totalAgg.dollars) + '</span>';
  totalRow.appendChild(totalAmt);
  bodyEl.appendChild(totalRow);

  document.getElementById("drillBackdrop").hidden = false;
}

function renderGlDetail(panel, facilityId, periods, groupPrefix, groupKey){
  const periodIdxSet = new Set(periods.map(p => PERIOD_IDX[p]));
  const lines = {};
  DATA.gl.forEach(([fid, pIdx, gIdx, lIdx, amt]) => {
    if (fid !== facilityId || !periodIdxSet.has(pIdx)) return;
    const group = DATA.groups[gIdx];
    if (!group.startsWith(groupPrefix)) return;
    if (groupKey && group !== groupKey) return;
    const label = DATA.labels[lIdx];
    lines[label] = (lines[label] || 0) + amt;
  });
  const sorted = Object.entries(lines).sort((a,b) => Math.abs(b[1]) - Math.abs(a[1]));
  if (sorted.length === 0){
    panel.innerHTML = '<div class="gl-empty">No GL detail found for this selection.</div>';
    return;
  }
  const shown = sorted.slice(0, 12);
  panel.innerHTML = shown.map(([label, amt]) =>
    '<div class="gl-line"><span>' + label + '</span><span class="amt' + (amt < 0 ? ' neg' : '') + '">' + fmtDollarK(amt) + '</span></div>'
  ).join("");
  if (sorted.length > shown.length){
    const rest = sorted.length - shown.length;
    panel.innerHTML += '<div class="gl-more">+ ' + rest + ' more line' + (rest === 1 ? "" : "s") + '</div>';
  }
}

function closeDrill(){ document.getElementById("drillBackdrop").hidden = true; }
document.getElementById("drillClose").onclick = closeDrill;
document.getElementById("drillBackdrop").onclick = (e) => { if (e.target.id === "drillBackdrop") closeDrill(); };
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrill(); });

// --- filters orchestration -------------------------------------------------
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
  renderCards("expense", "expenseCards");
  renderTable("expense", "expenseHead", "expenseBody", expandedExpense);
  renderCards("revenue", "revenueCards");
  renderTable("revenue", "revenueHead", "revenueBody", expandedRevenue);
}

populateMonthPickers();
refreshAll();
</script>
"""

HTML = HTML.replace("__DATA_JSON__", data_json)
HTML = HTML.replace("__MANAGERS_JSON__", json.dumps(managers))
HTML = HTML.replace("__LANDLORDS_JSON__", json.dumps(landlords))

out_path = SCRATCH / "ppd.html"
out_path.write_text(HTML)
print("wrote", out_path, len(HTML), "bytes")
