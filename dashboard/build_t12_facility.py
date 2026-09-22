import json, pathlib

SCRATCH = pathlib.Path(__file__).resolve().parent
data = json.loads((SCRATCH / "t12_facility_data.json").read_text())

data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

HTML = r"""<title>T12 by Facility</title>
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
.wrap{max-width:1400px; margin-inline:auto; display:flex; flex-direction:column; gap:22px;}
.masthead{display:flex; flex-direction:column; gap:4px;}
.eyebrow{font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--accent); font-weight:600;}
h1{font-size:clamp(24px,3.4vw,32px); font-weight:600; color:var(--ink);}
.sub{color:var(--muted); font-size:14px; max-width:76ch; line-height:1.5;}

.picker-bar{display:flex; flex-direction:column; gap:12px; background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow);}
.picker-row{display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.toggle-group{display:inline-flex; border:1px solid var(--border); border-radius:8px; overflow:hidden;}
.toggle-btn{
  font-family:inherit; font-size:13px; font-weight:600; color:var(--ink-soft);
  background:var(--surface-2); border:none; padding:7px 14px; cursor:pointer;
}
.toggle-btn + .toggle-btn{border-left:1px solid var(--border);}
.toggle-btn.active{background:var(--accent); color:var(--surface);}
.facility-select{
  font-family:"IBM Plex Sans",sans-serif; font-size:14px; font-weight:600; color:var(--ink);
  background:var(--surface-2); border:1px solid var(--border); border-radius:8px;
  padding:7px 12px; min-width:180px;
}
.range-picker{display:flex; align-items:center; gap:8px; margin-left:auto;}
.range-picker select{
  font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--ink);
  background:var(--surface-2); border:1px solid var(--border); border-radius:8px;
  padding:5px 10px;
}
.range-sep{color:var(--muted);}
.chip{
  font-family:inherit; font-size:12.5px; font-weight:500; color:var(--ink-soft);
  background:var(--surface-2); border:1px solid var(--border); border-radius:999px;
  padding:5px 12px; cursor:pointer;
}
.chip:hover{border-color:var(--border-strong);}
.chip.active{background:var(--accent); border-color:var(--accent); color:var(--surface);}
.chip.ghost{background:none;}
.entity-row{align-items:flex-start;}
.entity-row-label{font-size:12px; font-weight:600; color:var(--muted); padding-top:6px; white-space:nowrap;}
.entity-chips{display:flex; flex-wrap:wrap; gap:6px; flex:1;}
.filter-hint{font-size:11.5px; color:var(--muted); margin:0;}
.summary-line{font-size:12.5px; color:var(--ink-soft); margin:0; padding-top:2px; border-top:1px solid var(--border);}

.entity-cards{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px;}
.entity-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:14px 16px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px;}
.entity-card-label{font-family:"Fraunces",serif; font-size:14.5px; font-weight:600; color:var(--ink);}
.entity-card-meta{font-size:11px; color:var(--muted); margin-top:-4px;}
.entity-card-row{display:flex; justify-content:space-between; font-size:12px; color:var(--muted);}
.entity-card-row .ecv{font-family:"IBM Plex Mono",monospace; font-weight:600; color:var(--ink);}
.entity-card-row .ecv.good{color:var(--good);} .entity-card-row .ecv.bad{color:var(--bad);}
.entity-spark{width:100%; height:28px; display:block; margin-top:2px;}

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
.col-meta{display:block; font-weight:400; font-size:9.5px; color:var(--muted); text-transform:none; letter-spacing:0; margin-top:2px; font-family:"IBM Plex Sans",sans-serif;}
tbody td{padding:7px 14px; text-align:right; border-bottom:1px solid var(--border); font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--ink-soft);}
tbody td.linecell{text-align:left; font-family:"IBM Plex Sans",sans-serif; color:var(--ink); white-space:nowrap;}
th.linecol, td.linecell{position:sticky; left:0; background:var(--surface); z-index:2; box-shadow:1px 0 0 var(--border);}
thead th.linecol{background:var(--surface-2); z-index:3;}

tr.subtotal td{background:var(--surface-2); font-weight:600; color:var(--ink);}
tr.subtotal td.linecell{background:var(--surface-2);}
tr.hero td{background:var(--accent-soft); font-weight:700; font-size:13.5px; border-top:1px solid var(--border-strong); border-bottom:1px solid var(--border-strong);}
tr.hero td.linecell{background:var(--accent-soft); color:var(--ink);}
tr.dept td.linecell{padding-left:32px; color:var(--muted); font-size:12.5px;}
tr.dept td{color:var(--muted); font-size:12.5px;}

.expand-btn{
  background:none; border:none; cursor:pointer; padding:0; margin-right:6px;
  color:var(--muted); font-size:11px; display:inline-flex; align-items:center; justify-content:center;
  width:14px; transition:transform .15s;
}
.expand-btn.open{transform:rotate(90deg);}
.neg{color:var(--bad);}
.pos-hero{color:var(--good);} .neg-hero{color:var(--bad);}
.best{background:var(--good-soft);}
.worst{background:var(--bad-soft);}
td.linecell.best, td.linecell.worst{background:var(--surface);}

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
.drill-row .amt.neg{color:var(--bad);}
.drill-row.total{background:var(--surface-2); font-weight:700; cursor:default;}
.drill-row.total .amt{color:var(--ink); font-weight:700;}
.drill-row.total:hover{background:var(--surface-2);}
.gl-panel{padding:2px 18px 10px 40px; border-bottom:1px solid var(--border); display:none; background:var(--surface-2);}
.gl-panel.show{display:block;}
.gl-flat{padding:6px 18px 10px;}
.gl-line{display:flex; justify-content:space-between; gap:10px; font-size:12px; padding:4px 0; color:var(--ink-soft);}
.gl-line .amt{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums;}
.gl-line .amt.neg{color:var(--bad);}
.gl-empty{font-size:12px; color:var(--muted); padding:6px 0;}
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="wrap">
  <div class="masthead">
    <span class="eyebrow">Kesser Financial Dashboard</span>
    <h1>T12 by Facility</h1>
    <p class="sub">Compare managers or facilities against each other to benchmark performance. Pick a landlord to scope the field, choose whether to compare by manager or by individual facility, then select which ones to line up side by side &mdash; every line item, including each Operating Expense department, drills down to its GL accounts.</p>
  </div>

  <div class="picker-bar">
    <div class="picker-row">
      <span class="toggle-group" role="group" aria-label="Compare by">
        <button class="toggle-btn active" id="byManagerBtn" type="button">Managers</button>
        <button class="toggle-btn" id="byFacilityBtn" type="button">Facilities</button>
      </span>
      <select class="facility-select" id="landlordSelect"></select>
      <div class="range-picker">
        <select id="fromMonth"></select>
        <span class="range-sep">&ndash;</span>
        <select id="toMonth"></select>
        <button class="chip" id="t3Btn" type="button">T3</button>
        <button class="chip" id="t12Btn" type="button">T12</button>
      </div>
    </div>
    <div class="picker-row entity-row">
      <span class="entity-row-label">Compare</span>
      <div class="entity-chips" id="entityChips"></div>
      <button class="chip ghost" id="selectAllBtn" type="button">Select all</button>
      <button class="chip ghost" id="clearBtn" type="button">Clear</button>
    </div>
    <p class="filter-hint">Click an entity to add or remove it from the comparison &mdash; no limit, but the table scrolls sideways past a handful.</p>
    <p class="summary-line" id="summaryLine">&nbsp;</p>
  </div>

  <div class="entity-cards" id="entityCards"></div>

  <div class="table-card">
    <div class="table-scroll">
      <table id="waterfallTable">
        <thead><tr id="headRow"></tr></thead>
        <tbody id="bodyRows"></tbody>
      </table>
    </div>
  </div>
  <p class="footnote">Amounts in thousands ($K), summed over the selected month range for each entity. Negative values shown in red with parentheses. The green/red tint on a row marks the best and worst performer among the entities shown &mdash; higher is better for revenue and profit lines, lower is better for expense lines; the "Other Income / Expense" line isn't tinted since its sign has no consistent direction. Click any Operating Revenue, department, G&amp;A, Real Estate Tax, Capital Expenses, Management Fees, or Other Income/Expense cell &mdash; or the Operating Expense total &mdash; to drill into GL-account detail. "Management Fees" here is the operator's own reported management fee line, separate from Kesser's landlord-collected fee revenue.</p>
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
const facilityById = {};
DATA.facilities.forEach(f => { facilityById[f.facility_id] = f; });
const LANDLORDS = Array.from(new Set(DATA.facilities.map(f => f.landlord))).sort();

const WATERFALL_BY_KEY = {};
DATA.waterfall.forEach(r => { WATERFALL_BY_KEY[r.facility_id + "|" + r.period] = r; });
const PERIOD_IDX = {}; DATA.periods.forEach((p,i) => PERIOD_IDX[p] = i);
const PERIODS_ALL = DATA.periods;

const EXPENSE_DEPT_ORDER = ["Nursing","Ancillary","Activities","Social Service","Dietary","Housekeeping","Laundry and Linen","Employee Welfare","Plant","Marketing"];

// better: "high" = larger is stronger performance (tinted green), "low" = smaller
// is stronger (an expense -- less of it is better), null = no consistent
// direction (Other Income/Expense mixes unrelated one-off items).
const ROWS = [
  {key:"operating_revenue", label:"Operating Revenue", type:"line", glKey:"operating_revenue", better:"high"},
  {key:"operating_expense", label:"Operating Expense", type:"expandable", better:"low"},
  {key:"operating_income", label:"Operating Income", type:"subtotal", better:"high"},
  {key:"ga", label:"G&A Expense", type:"line", glKey:"ga", better:"low"},
  {key:"ebitdarm", label:"EBITDARM", type:"subtotal", better:"high"},
  {key:"real_estate_tax", label:"Real Estate Tax", type:"line", glKey:"real_estate_tax", better:"low"},
  {key:"ebidarm", label:"EBIDARM", type:"subtotal", better:"high"},
  {key:"capital_expenses", label:"Capital Expenses", type:"line", glKey:"capital_expenses", better:"low"},
  {key:"earnings_before_mgmt_fees", label:"Earnings before Mgmt Fees", type:"subtotal", better:"high"},
  {key:"management_fees", label:"Management Fees", type:"line", glKey:"management_fees", better:"low"},
  {key:"earnings", label:"Earnings", type:"subtotal", better:"high"},
  {key:"other_income_expense", label:"Other Income / Expense", type:"line", glKey:"other_income_expense", better:null},
  {key:"noi", label:"NOI", type:"hero", better:"high"},
];

let compareBy = "manager";   // "manager" | "facility"
let selLandlord = "";        // "" = all landlords
let selEntities = new Set(); // manager names or facility_ids (as strings)
let expandedOpex = false;
let rangeFrom = PERIODS_ALL[0], rangeTo = PERIODS_ALL[PERIODS_ALL.length - 1];

function fmtMonth(period){
  const [y,m] = period.split("-");
  const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return names[parseInt(m,10)-1] + " '" + y.slice(2);
}
function fmtK(v){
  if (v === undefined || v === null) return "–";
  const k = v/1000;
  const abs = Math.abs(k);
  const str = abs.toLocaleString(undefined,{maximumFractionDigits:1, minimumFractionDigits:1});
  return v < 0 ? "(" + str + ")" : str;
}
function fmtRangeLabel(periods){
  if (periods.length === 0) return "no data";
  return periods.length === 1 ? fmtMonth(periods[0]) : fmtMonth(periods[0]) + " – " + fmtMonth(periods[periods.length-1]);
}

// --- entity universe: managers or facilities, scoped by the landlord filter --
function entitiesInScope(){
  const facs = DATA.facilities.filter(f => !selLandlord || f.landlord === selLandlord);
  if (compareBy === "manager"){
    const byMgr = {};
    facs.forEach(f => { (byMgr[f.manager] = byMgr[f.manager] || []).push(f.facility_id); });
    return Object.keys(byMgr).map(mgr => {
      const ids = byMgr[mgr];
      const landlords = Array.from(new Set(ids.map(id => facilityById[id].landlord)));
      const meta = ids.length + " facilit" + (ids.length === 1 ? "y" : "ies") + " · " + (landlords.length === 1 ? landlords[0] : landlords.length + " landlords");
      return {key: mgr, label: mgr, facilityIds: ids, meta};
    }).sort((a,b) => a.label.localeCompare(b.label));
  }
  return facs.map(f => ({key: f.facility_id, label: f.name, facilityIds: [f.facility_id], meta: f.manager + " · " + f.landlord}))
    .sort((a,b) => a.label.localeCompare(b.label));
}

function defaultSelection(scope){
  if (scope.length <= 6) return scope.map(e => String(e.key));
  return scope.slice().sort((a,b) => b.facilityIds.length - a.facilityIds.length || a.label.localeCompare(b.label))
    .slice(0, 6).map(e => String(e.key));
}

function refreshEntities(){
  const scope = entitiesInScope();
  const scopeKeys = new Set(scope.map(e => String(e.key)));
  Array.from(selEntities).forEach(k => { if (!scopeKeys.has(k)) selEntities.delete(k); });
  if (selEntities.size === 0) defaultSelection(scope).forEach(k => selEntities.add(k));
  return scope;
}

function sumRaw(facilityIds, periods, key){
  let total = 0;
  facilityIds.forEach(fid => periods.forEach(p => {
    const row = WATERFALL_BY_KEY[fid + "|" + p];
    if (row) total += (row[key] || 0);
  }));
  return total;
}
function sumDept(facilityIds, periods, dept){
  let total = 0;
  facilityIds.forEach(fid => periods.forEach(p => {
    const row = WATERFALL_BY_KEY[fid + "|" + p];
    if (row) total += (row.departments[dept] || 0);
  }));
  return total;
}

// --- filter wiring ---------------------------------------------------------
function setCompareBy(mode){
  if (mode === compareBy) return;
  const prevScope = entitiesInScope();
  const prevSelected = prevScope.filter(e => selEntities.has(String(e.key)));
  compareBy = mode;
  const newScope = entitiesInScope();
  const newKeys = new Set();
  if (mode === "facility"){
    prevSelected.forEach(e => e.facilityIds.forEach(id => newKeys.add(String(id))));
  } else {
    prevSelected.forEach(e => newKeys.add(facilityById[e.facilityIds[0]].manager));
  }
  const validKeys = new Set(newScope.map(e => String(e.key)));
  let expanded = Array.from(newKeys).filter(k => validKeys.has(k));
  // Expanding a handful of managers into their facilities can blow up to
  // dozens of columns -- cap to the largest-revenue facilities so switching
  // modes still lands on a readable comparison rather than the whole roster.
  const MAX_AUTO_EXPAND = 12;
  if (mode === "facility" && expanded.length > MAX_AUTO_EXPAND){
    expanded = expanded
      .map(k => ({k, rev: sumRaw([parseInt(k, 10)], PERIODS_ALL, "operating_revenue")}))
      .sort((a,b) => b.rev - a.rev)
      .slice(0, MAX_AUTO_EXPAND)
      .map(x => x.k);
  }
  selEntities = new Set(expanded);
  document.getElementById("byManagerBtn").classList.toggle("active", mode === "manager");
  document.getElementById("byFacilityBtn").classList.toggle("active", mode === "facility");
  refreshAndRender();
}
document.getElementById("byManagerBtn").onclick = () => setCompareBy("manager");
document.getElementById("byFacilityBtn").onclick = () => setCompareBy("facility");

function populateLandlordSelect(){
  const sel = document.getElementById("landlordSelect");
  sel.innerHTML = "";
  const optAll = document.createElement("option"); optAll.value = ""; optAll.textContent = "All Landlords";
  sel.appendChild(optAll);
  LANDLORDS.forEach(l => { const o = document.createElement("option"); o.value = l; o.textContent = l; sel.appendChild(o); });
  sel.value = selLandlord;
  sel.onchange = () => { selLandlord = sel.value; refreshAndRender(); };
}

function buildEntityChips(scope){
  const container = document.getElementById("entityChips");
  container.innerHTML = "";
  scope.forEach(e => {
    const k = String(e.key);
    const btn = document.createElement("button");
    btn.className = "chip" + (selEntities.has(k) ? " active" : "");
    btn.textContent = e.label;
    btn.onclick = () => { if (selEntities.has(k)) selEntities.delete(k); else selEntities.add(k); buildEntityChips(scope); render(); };
    container.appendChild(btn);
  });
}
document.getElementById("selectAllBtn").onclick = () => {
  const scope = entitiesInScope();
  scope.forEach(e => selEntities.add(String(e.key)));
  buildEntityChips(scope); render();
};
document.getElementById("clearBtn").onclick = () => {
  selEntities.clear();
  buildEntityChips(entitiesInScope()); render();
};

function refreshAndRender(){
  const scope = refreshEntities();
  buildEntityChips(scope);
  render();
}

// --- month range, anchored on the CURRENTLY SELECTED entities (not the whole
// portfolio) -- a comparison whose entities' latest reported month is May
// shouldn't get a July-anchored T3/T12 just because some other manager
// elsewhere has already reported July.
function availablePeriodsForSelection(){
  const ids = new Set();
  entitiesInScope().forEach(e => { if (selEntities.has(String(e.key))) e.facilityIds.forEach(id => ids.add(id)); });
  const set = new Set();
  DATA.waterfall.forEach(r => { if (ids.has(r.facility_id)) set.add(r.period); });
  return Array.from(set).sort();
}
function setTrailingRange(n){
  const avail = availablePeriodsForSelection();
  if (avail.length === 0) return;
  const anchor = avail[avail.length - 1];
  const startIdx = Math.max(0, avail.length - n);
  rangeFrom = avail[startIdx]; rangeTo = anchor;
  document.getElementById("fromMonth").value = rangeFrom;
  document.getElementById("toMonth").value = rangeTo;
  render();
}
function populateMonthPickers(){
  const fromSel = document.getElementById("fromMonth");
  const toSel = document.getElementById("toMonth");
  fromSel.innerHTML = ""; toSel.innerHTML = "";
  PERIODS_ALL.forEach(p => {
    const o1 = document.createElement("option"); o1.value = p; o1.textContent = fmtMonth(p);
    if (p === rangeFrom) o1.selected = true; fromSel.appendChild(o1);
    const o2 = document.createElement("option"); o2.value = p; o2.textContent = fmtMonth(p);
    if (p === rangeTo) o2.selected = true; toSel.appendChild(o2);
  });
  fromSel.onchange = () => { rangeFrom = fromSel.value; if (rangeFrom > rangeTo){ rangeTo = rangeFrom; toSel.value = rangeTo; } render(); };
  toSel.onchange = () => { rangeTo = toSel.value; if (rangeTo < rangeFrom){ rangeFrom = rangeTo; fromSel.value = rangeFrom; } render(); };
  document.getElementById("t3Btn").onclick = () => setTrailingRange(3);
  document.getElementById("t12Btn").onclick = () => setTrailingRange(12);
}

// --- GL-account detail, scanned on demand from the full ~69,000-row portfolio
// export -- only touched when a drill modal opens (an occasional click), so
// no per-facility index needs to be pre-built the way the old single-facility
// page needed one for its always-visible nested rows.
function glLinesFor(groupKey, facilityIds, periods){
  const idSet = new Set(facilityIds);
  const periodIdxSet = new Set(periods.map(p => PERIOD_IDX[p]));
  const lines = {};
  DATA.gl.forEach(([fid, pIdx, gIdx, lIdx, amt]) => {
    if (!idSet.has(fid) || !periodIdxSet.has(pIdx)) return;
    if (DATA.groups[gIdx] !== groupKey) return;
    const label = DATA.labels[lIdx];
    lines[label] = (lines[label] || 0) + amt;
  });
  return Object.entries(lines).sort((a,b) => Math.abs(b[1]) - Math.abs(a[1]));
}
function renderGlLinesInto(container, groupKey, facilityIds, periods){
  const lines = glLinesFor(groupKey, facilityIds, periods);
  if (lines.length === 0){ container.innerHTML = '<div class="gl-empty">No GL detail available for this selection.</div>'; return; }
  container.innerHTML = lines.map(([label, amt]) =>
    '<div class="gl-line"><span>' + label + '</span><span class="amt' + (amt < 0 ? ' neg' : '') + '">$' + fmtK(amt) + 'K</span></div>'
  ).join("");
}

// --- drill modal ------------------------------------------------------------
function openDrillList(title, subtitle, rows){
  document.getElementById("drillTitle").textContent = title;
  document.getElementById("drillSub").textContent = subtitle;
  const bodyEl = document.getElementById("drillBody");
  bodyEl.innerHTML = "";
  let total = 0;
  rows.forEach(r => {
    total += r.amount;
    const row = document.createElement("div");
    row.className = "drill-row";
    const left = document.createElement("div");
    left.innerHTML = '<span class="expand-btn" style="width:10px;">▸</span><div><div class="name">' + r.label + '</div>' + (r.sub ? '<div class="meta">' + r.sub + '</div>' : '') + '</div>';
    const amt = document.createElement("div");
    amt.className = "amt" + (r.amount < 0 ? " neg" : "");
    amt.textContent = "$" + fmtK(r.amount) + "K";
    row.appendChild(left); row.appendChild(amt);
    const panel = document.createElement("div");
    panel.className = "gl-panel";
    let loaded = false;
    row.onclick = () => {
      const chev = left.querySelector(".expand-btn");
      const show = !panel.classList.contains("show");
      panel.classList.toggle("show", show);
      chev.classList.toggle("open", show);
      if (show && !loaded){ renderGlLinesInto(panel, r.glKey, r.facilityIds, r.periods); loaded = true; }
    };
    bodyEl.appendChild(row);
    bodyEl.appendChild(panel);
  });
  const totalRow = document.createElement("div");
  totalRow.className = "drill-row total";
  totalRow.innerHTML = '<div>Total</div>';
  const totalAmt = document.createElement("div");
  totalAmt.className = "amt" + (total < 0 ? " neg" : "");
  totalAmt.textContent = "$" + fmtK(total) + "K";
  totalRow.appendChild(totalAmt);
  bodyEl.appendChild(totalRow);
  document.getElementById("drillBackdrop").hidden = false;
}
function openDrillGlFlat(title, subtitle, groupKey, facilityIds, periods){
  document.getElementById("drillTitle").textContent = title;
  document.getElementById("drillSub").textContent = subtitle;
  const bodyEl = document.getElementById("drillBody");
  bodyEl.innerHTML = '<div class="gl-flat"></div>';
  renderGlLinesInto(bodyEl.querySelector(".gl-flat"), groupKey, facilityIds, periods);
  document.getElementById("drillBackdrop").hidden = false;
}

function drillLine(entity, row, periods){
  const subtitle = entity.label + " · " + fmtRangeLabel(periods);
  if (entity.facilityIds.length > 1){
    const rows = entity.facilityIds.map(fid => {
      const f = facilityById[fid];
      return {label: f.name, sub: f.manager + " · " + f.landlord, amount: sumRaw([fid], periods, row.key), glKey: row.glKey, facilityIds: [fid], periods};
    }).filter(x => x.amount !== 0).sort((a,b) => Math.abs(b.amount) - Math.abs(a.amount));
    openDrillList(row.label, subtitle + " · by facility", rows);
  } else {
    openDrillGlFlat(row.label, subtitle, row.glKey, entity.facilityIds, periods);
  }
}
function drillOpex(entity, periods){
  const subtitle = entity.label + " · " + fmtRangeLabel(periods);
  const depts = deptsFor([entity], periods);
  const rows = depts.map(dept => ({
    label: dept, amount: sumDept(entity.facilityIds, periods, dept), glKey: "opex:" + dept, facilityIds: entity.facilityIds, periods,
  })).filter(x => x.amount !== 0).sort((a,b) => Math.abs(b.amount) - Math.abs(a.amount));
  openDrillList("Operating Expense", subtitle + " · by department", rows);
}
function drillDept(entity, dept, periods){
  openDrillGlFlat(dept, entity.label + " · " + fmtRangeLabel(periods), "opex:" + dept, entity.facilityIds, periods);
}

function closeDrill(){ document.getElementById("drillBackdrop").hidden = true; }
document.getElementById("drillClose").onclick = closeDrill;
document.getElementById("drillBackdrop").onclick = (e) => { if (e.target.id === "drillBackdrop") closeDrill(); };
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrill(); });

// --- table rendering ---------------------------------------------------------
function deptsFor(entities, periods){
  const all = new Set();
  entities.forEach(e => e.facilityIds.forEach(fid => periods.forEach(p => {
    const row = WATERFALL_BY_KEY[fid + "|" + p];
    if (row) Object.keys(row.departments).forEach(d => all.add(d));
  })));
  const ordered = EXPENSE_DEPT_ORDER.filter(d => all.has(d));
  const rest = Array.from(all).filter(d => !EXPENSE_DEPT_ORDER.includes(d)).sort();
  return ordered.concat(rest);
}

function appendRow(body, opts){
  const tr = document.createElement("tr");
  if (opts.cssClass) tr.className = opts.cssClass;

  const labelTd = document.createElement("td");
  labelTd.className = "linecell";
  if (opts.expandable){
    const btn = document.createElement("button");
    btn.className = "expand-btn" + (opts.isOpen ? " open" : "");
    btn.textContent = "▸";
    btn.onclick = (e) => { e.stopPropagation(); opts.onToggle(); };
    labelTd.appendChild(btn);
  }
  labelTd.appendChild(document.createTextNode(opts.label));
  tr.appendChild(labelTd);

  const finite = opts.values.filter(v => v !== null && v !== undefined);
  const max = finite.length > 1 ? Math.max(...finite) : null;
  const min = finite.length > 1 ? Math.min(...finite) : null;

  opts.values.forEach((v, i) => {
    const td = document.createElement("td");
    td.textContent = fmtK(v);
    if (v < 0) td.classList.add("neg");
    if (opts.better && max !== null && max !== min){
      if (opts.better === "high" && v === max) td.classList.add("best");
      else if (opts.better === "high" && v === min) td.classList.add("worst");
      else if (opts.better === "low" && v === min) td.classList.add("best");
      else if (opts.better === "low" && v === max) td.classList.add("worst");
    }
    if (opts.rowType === "hero") td.classList.add(v >= 0 ? "pos-hero" : "neg-hero");
    if (opts.onClick){ td.classList.add("clickable"); td.onclick = () => opts.onClick(i); }
    tr.appendChild(td);
  });
  body.appendChild(tr);
  return tr;
}

function render(){
  const scope = entitiesInScope();
  const selected = scope.filter(e => selEntities.has(String(e.key))).sort((a,b) => a.label.localeCompare(b.label));
  const periods = PERIODS_ALL.filter(p => p >= rangeFrom && p <= rangeTo);

  updateSummaryLine(selected, periods);
  renderEntityCards(selected, periods);

  const head = document.getElementById("headRow");
  const body = document.getElementById("bodyRows");
  head.innerHTML = ""; body.innerHTML = "";

  const lineTh = document.createElement("th");
  lineTh.className = "linecol"; lineTh.textContent = "Line Item";
  head.appendChild(lineTh);

  if (selected.length === 0){
    const tr = document.createElement("tr");
    const td = document.createElement("td"); td.className = "linecell"; td.textContent = "No entities selected — choose managers or facilities above to compare.";
    tr.appendChild(td); body.appendChild(tr);
    return;
  }

  selected.forEach(e => {
    const th = document.createElement("th");
    th.innerHTML = e.label + '<span class="col-meta">' + e.meta + '</span>';
    head.appendChild(th);
  });

  const depts = deptsFor(selected, periods);

  ROWS.forEach(row => {
    const values = selected.map(e => sumRaw(e.facilityIds, periods, row.key));
    appendRow(body, {
      label: row.label, values, better: row.better, rowType: row.type,
      cssClass: row.type === "subtotal" ? "subtotal" : row.type === "hero" ? "hero" : "",
      expandable: row.type === "expandable", isOpen: expandedOpex,
      onToggle: row.type === "expandable" ? (() => { expandedOpex = !expandedOpex; render(); }) : null,
      onClick: row.glKey ? ((i) => drillLine(selected[i], row, periods)) : (row.type === "expandable" ? ((i) => drillOpex(selected[i], periods)) : null),
    });

    if (row.type === "expandable" && expandedOpex){
      depts.forEach(dept => {
        const dvalues = selected.map(e => sumDept(e.facilityIds, periods, dept));
        appendRow(body, {
          label: dept, values: dvalues, better: "low", cssClass: "dept",
          onClick: (i) => drillDept(selected[i], dept, periods),
        });
      });
    }
  });
}

function updateSummaryLine(selected, periods){
  const el = document.getElementById("summaryLine");
  if (selected.length === 0){ el.textContent = "No entities selected."; return; }
  const noun = compareBy === "manager" ? ("manager" + (selected.length === 1 ? "" : "s")) : ("facilit" + (selected.length === 1 ? "y" : "ies"));
  const scopeTxt = selLandlord ? selLandlord : "all landlords";
  el.textContent = "Comparing " + selected.length + " " + noun + " · " + scopeTxt + " · " + fmtRangeLabel(periods);
}

function renderEntityCards(selected, periods){
  const container = document.getElementById("entityCards");
  container.innerHTML = "";
  selected.forEach((e, idx) => {
    const noi = sumRaw(e.facilityIds, periods, "noi");
    const rev = sumRaw(e.facilityIds, periods, "operating_revenue");
    const card = document.createElement("div");
    card.className = "entity-card";
    const svgId = "spark" + idx;
    card.innerHTML =
      '<div class="entity-card-label">' + e.label + '</div>' +
      '<div class="entity-card-meta">' + e.meta + '</div>' +
      '<div class="entity-card-row"><span>Revenue</span><span class="ecv">$' + fmtK(rev) + 'K</span></div>' +
      '<div class="entity-card-row"><span>NOI</span><span class="ecv ' + (noi >= 0 ? "good" : "bad") + '">$' + fmtK(noi) + 'K</span></div>' +
      '<svg class="entity-spark" viewBox="0 0 200 32" preserveAspectRatio="none" data-spark="' + svgId + '"></svg>';
    container.appendChild(card);
    drawSparkline(card.querySelector('[data-spark="' + svgId + '"]'), e.facilityIds, periods);
  });
}
function drawSparkline(svg, facilityIds, periods){
  if (periods.length < 2){ svg.innerHTML = ""; return; }
  const vals = periods.map(p => sumRaw(facilityIds, [p], "noi"));
  const min = Math.min(...vals, 0), max = Math.max(...vals, 0);
  const range = (max - min) || 1;
  const w = 200, h = 32, pad = 3;
  const stepX = (w - pad*2) / (vals.length - 1);
  const pts = vals.map((v,i) => [pad + i*stepX, h - pad - ((v - min) / range) * (h - pad*2)]);
  const zeroY = h - pad - ((0 - min) / range) * (h - pad*2);
  const path = pts.map((pt,i) => (i===0?"M":"L") + pt[0].toFixed(1) + "," + pt[1].toFixed(1)).join(" ");
  const lastPositive = vals[vals.length-1] >= 0;
  svg.innerHTML =
    '<line x1="' + pad + '" y1="' + zeroY.toFixed(1) + '" x2="' + (w-pad) + '" y2="' + zeroY.toFixed(1) + '" stroke="var(--border)" stroke-width="1" stroke-dasharray="2,2"/>' +
    '<path d="' + path + '" fill="none" stroke="' + (lastPositive ? "var(--good)" : "var(--bad)") + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' +
    '<circle cx="' + pts[pts.length-1][0].toFixed(1) + '" cy="' + pts[pts.length-1][1].toFixed(1) + '" r="2.5" fill="' + (lastPositive ? "var(--good)" : "var(--bad)") + '"/>';
}

populateLandlordSelect();
populateMonthPickers();
refreshAndRender();
</script>
"""

HTML = HTML.replace("__DATA_JSON__", data_json)

out_path = SCRATCH / "t12_facility.html"
out_path.write_text(HTML)
print("wrote", out_path, len(HTML), "bytes")
