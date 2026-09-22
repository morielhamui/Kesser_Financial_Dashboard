import json, pathlib

SCRATCH = pathlib.Path(__file__).parent
data = json.loads((SCRATCH / "t12_data.json").read_text())

# Sort facilities and derive filter option lists
managers = sorted(set(f["manager"] for f in data["facilities"]))
landlords = sorted(set(f["landlord"] for f in data["facilities"]))

data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

HTML = r"""<title>T12 P&L Waterfall</title>
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
.sub{color:var(--muted); font-size:14px; max-width:70ch; line-height:1.5;}

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

.drill-backdrop{
  position:fixed; inset:0; background:rgba(20,28,26,.45); display:flex;
  align-items:center; justify-content:center; padding:20px; z-index:50;
}
.drill-card{
  background:var(--surface); border:1px solid var(--border); border-radius:14px;
  box-shadow:var(--shadow); max-width:480px; width:100%; max-height:80vh;
  display:flex; flex-direction:column; overflow:hidden;
}
.drill-head{display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:16px 18px 12px; border-bottom:1px solid var(--border);}
.drill-title{font-family:"Fraunces",serif; font-size:16px; font-weight:600; color:var(--ink);}
.drill-sub{font-size:12px; color:var(--muted); margin-top:2px;}
.drill-close{background:none; border:none; font-size:18px; line-height:1; color:var(--muted); cursor:pointer; padding:2px 4px;}
.drill-close:hover{color:var(--ink);}
.drill-body{overflow-y:auto; padding:6px 0;}
.drill-row{display:flex; justify-content:space-between; gap:10px; padding:8px 18px; font-size:13px; border-bottom:1px solid var(--border);}
.drill-row:last-child{border-bottom:none;}
.drill-row .name{color:var(--ink); font-weight:500;}
.drill-row .meta{color:var(--muted); font-size:11.5px; font-weight:400;}
.drill-row .amt{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; color:var(--ink-soft); white-space:nowrap;}
.drill-row .amt.neg{color:var(--bad);}
.drill-row.total{background:var(--surface-2); font-weight:700;}
.drill-row.total .amt{color:var(--ink); font-weight:700;}

tbody td.clickable{cursor:pointer;}
tbody td.clickable:hover{box-shadow:inset 0 0 0 1px var(--accent);}

.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px;}
.stat-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px;}
.stat-label{font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);}
.stat-value{font-family:"IBM Plex Mono",monospace; font-size:26px; font-weight:600; font-variant-numeric:tabular-nums;}
.stat-value.good{color:var(--good);} .stat-value.bad{color:var(--bad);}
.stat-foot{font-size:12px; color:var(--muted);}
.spark{width:100%; height:40px; display:block;}

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

tr.subtotal td{background:var(--surface-2); font-weight:600; color:var(--ink);}
tr.subtotal td.linecell{background:var(--surface-2);}
tr.hero td{background:var(--accent-soft); font-weight:700; font-size:13.5px; border-top:1px solid var(--border-strong); border-bottom:1px solid var(--border-strong);}
tr.hero td.linecell{background:var(--accent-soft); color:var(--ink);}
tr.dept td.linecell{padding-left:32px; color:var(--muted); font-size:12.5px;}
tr.dept td{color:var(--muted); font-size:12.5px;}
tr.dept{display:none;}
tr.dept.show{display:table-row;}

.neg{color:var(--bad);}
.pos-hero{color:var(--good);}
.neg-hero{color:var(--bad);}

.expand-btn{
  background:none; border:none; cursor:pointer; padding:0; margin-right:6px;
  color:var(--muted); font-size:11px; display:inline-flex; align-items:center; justify-content:center;
  width:14px; transition:transform .15s;
}
.expand-btn.open{transform:rotate(90deg);}

.footnote{font-size:11.5px; color:var(--muted); line-height:1.5; padding:2px 4px;}
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="wrap">
  <div class="masthead">
    <span class="eyebrow">Kesser Financial Dashboard</span>
    <h1>T12 P&amp;L Waterfall</h1>
    <p class="sub">Operating revenue through NOI, by month, for the selected managers and landlords. Recomputed from each operator's own reported statements and validated to their reported Net Income within $50.</p>
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
    <p class="filter-hint">Click a chip to select it on its own. Ctrl/Cmd-click to add it to the current selection. Picking a manager, landlord, or facility narrows the other two lists to what actually applies. Click any number in the table to see which facilities make it up.</p>
  </div>

  <div class="stats">
    <div class="stat-card">
      <span class="stat-label">Facilities selected</span>
      <span class="stat-value" id="statFacilities">--</span>
      <span class="stat-foot" id="statFacilitiesFoot">&nbsp;</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Operating Revenue &middot; latest month</span>
      <span class="stat-value" id="statRevenue">--</span>
      <span class="stat-foot" id="statRevenueFoot">&nbsp;</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">NOI &middot; latest month</span>
      <span class="stat-value" id="statNoi">--</span>
      <span class="stat-foot" id="statNoiFoot">&nbsp;</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">NOI trend</span>
      <svg class="spark" id="statSpark" viewBox="0 0 240 40" preserveAspectRatio="none"></svg>
      <span class="stat-foot" id="statSparkFoot">&nbsp;</span>
    </div>
  </div>

  <div class="table-card">
    <div class="table-scroll">
      <table id="waterfallTable">
        <thead><tr id="headRow"></tr></thead>
        <tbody id="bodyRows"></tbody>
      </table>
    </div>
  </div>
  <p class="footnote">Amounts in thousands ($K). Negative values shown in red with parentheses. Click "Operating Expense" to expand department-level detail, and click any number in the table to see the breakdown behind it &mdash; by facility when everything selected shares one manager, or by manager when more than one is in view. GL-account-level detail (the individual line items behind each department) is coming on the Expense/Revenue PPD page. "Management Fees" here is the operator's own reported management fee line and is separate from Kesser's landlord-collected fee revenue, which is tracked at the landlord level.</p>
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

const DEPT_ORDER = ["Ancillary","Nursing","Activities","Social Service","Dietary","Housekeeping","Laundry and Linen","Employee Welfare","Plant","Marketing"];

const ROWS = [
  {key:"operating_revenue", label:"Operating Revenue", type:"line"},
  {key:"operating_expense", label:"Operating Expense", type:"expandable"},
  {key:"operating_income", label:"Operating Income", type:"subtotal"},
  {key:"ga", label:"G&A Expense", type:"line"},
  {key:"ebitdarm", label:"EBITDARM", type:"subtotal"},
  {key:"real_estate_tax", label:"Real Estate Tax", type:"line"},
  {key:"ebidarm", label:"EBIDARM", type:"subtotal"},
  {key:"capital_expenses", label:"Capital Expenses", type:"line"},
  {key:"earnings_before_mgmt_fees", label:"Earnings before Mgmt Fees", type:"subtotal"},
  {key:"management_fees", label:"Management Fees", type:"line"},
  {key:"earnings", label:"Earnings", type:"subtotal"},
  {key:"other_income_expense", label:"Other Income / Expense", type:"line"},
  {key:"noi", label:"NOI", type:"hero"},
];

let selManagers = new Set();   // empty = All
let selLandlords = new Set();  // empty = All
let selFacilities = new Set(); // empty = All, holds facility_id
let expanded = false;

const facilityById = {};
DATA.facilities.forEach(f => { facilityById[f.facility_id] = f; });

const PERIODS_ALL = Array.from(new Set(DATA.waterfall.map(r => r.period))).sort();
let rangeFrom = PERIODS_ALL[0];
let rangeTo = PERIODS_ALL[PERIODS_ALL.length - 1];

function fmtMonth(period){
  const [y,m] = period.split("-");
  const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return names[parseInt(m,10)-1] + " '" + y.slice(2);
}

function fmtK(v){
  if (v === undefined || v === null) return "--";
  const k = v/1000;
  const abs = Math.abs(k);
  const str = abs.toLocaleString(undefined,{maximumFractionDigits:1, minimumFractionDigits:1});
  return v < 0 ? "(" + str + ")" : str;
}

// Click semantics: plain click replaces the group's whole selection with
// just this value (radio-like); re-clicking the sole selected value clears
// back to "All". Ctrl/Cmd-click toggles this value into/out of the existing
// selection so multiple values can be picked at once.
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

// Facilities matching a set of filters, optionally ignoring one dimension
// (so we can compute "what's still pickable" for that dimension's own list).
function filteredFacilities({ignore} = {}){
  return DATA.facilities.filter(f =>
    (ignore === "manager" || selManagers.size === 0 || selManagers.has(f.manager)) &&
    (ignore === "landlord" || selLandlords.size === 0 || selLandlords.has(f.landlord)) &&
    (ignore === "facility" || selFacilities.size === 0 || selFacilities.has(f.facility_id))
  );
}

function matchingFacilityIds(){
  return new Set(filteredFacilities().map(f => f.facility_id));
}

function aggregate(){
  const ids = matchingFacilityIds();
  const rows = DATA.waterfall.filter(r => ids.has(r.facility_id) && r.period >= rangeFrom && r.period <= rangeTo);
  const periods = Array.from(new Set(rows.map(r => r.period))).sort();
  const byPeriod = {};
  periods.forEach(p => {
    byPeriod[p] = {};
    ROWS.forEach(r => byPeriod[p][r.key] = 0);
    byPeriod[p].departments = {};
  });
  rows.forEach(r => {
    const bucket = byPeriod[r.period];
    ROWS.forEach(row => { bucket[row.key] += (r[row.key] || 0); });
    Object.entries(r.departments || {}).forEach(([dept, amt]) => {
      bucket.departments[dept] = (bucket.departments[dept] || 0) + amt;
    });
  });
  return {ids, periods, byPeriod};
}

function deptList(byPeriod, periods){
  const all = new Set();
  periods.forEach(p => Object.keys(byPeriod[p].departments).forEach(d => all.add(d)));
  const ordered = DEPT_ORDER.filter(d => all.has(d));
  const rest = Array.from(all).filter(d => !DEPT_ORDER.includes(d)).sort();
  return ordered.concat(rest);
}

function render(){
  const {periods, byPeriod} = aggregate();
  const head = document.getElementById("headRow");
  const body = document.getElementById("bodyRows");
  head.innerHTML = "";
  body.innerHTML = "";

  const lineTh = document.createElement("th");
  lineTh.className = "linecol";
  lineTh.textContent = "Line Item";
  head.appendChild(lineTh);
  periods.forEach(p => {
    const th = document.createElement("th");
    th.textContent = fmtMonth(p);
    head.appendChild(th);
  });
  const totalTh = document.createElement("th");
  totalTh.textContent = "Total";
  head.appendChild(totalTh);

  const depts = deptList(byPeriod, periods);

  ROWS.forEach(row => {
    const tr = document.createElement("tr");
    if (row.type === "subtotal") tr.className = "subtotal";
    if (row.type === "hero") tr.className = "hero";

    const labelTd = document.createElement("td");
    labelTd.className = "linecell";
    if (row.type === "expandable"){
      const btn = document.createElement("button");
      btn.className = "expand-btn" + (expanded ? " open" : "");
      btn.textContent = "▸";
      btn.onclick = () => { expanded = !expanded; render(); };
      labelTd.appendChild(btn);
      labelTd.appendChild(document.createTextNode(row.label));
    } else {
      labelTd.textContent = row.label;
    }
    tr.appendChild(labelTd);

    let total = 0;
    periods.forEach(p => {
      const v = byPeriod[p][row.key] || 0;
      total += v;
      const td = document.createElement("td");
      td.textContent = fmtK(v);
      td.classList.add("clickable");
      td.onclick = () => openDrill(row.key, row.label, p, null);
      if (row.type === "hero") td.classList.add(v >= 0 ? "pos-hero" : "neg-hero");
      else if (v < 0) td.classList.add("neg");
      tr.appendChild(td);
    });
    const totalTd = document.createElement("td");
    totalTd.textContent = fmtK(total);
    totalTd.classList.add("clickable");
    totalTd.onclick = () => openDrill(row.key, row.label, "TOTAL", null, periods);
    if (row.type === "hero") totalTd.classList.add(total >= 0 ? "pos-hero" : "neg-hero");
    else if (total < 0) totalTd.classList.add("neg");
    tr.appendChild(totalTd);

    body.appendChild(tr);

    if (row.type === "expandable"){
      depts.forEach(dept => {
        const dtr = document.createElement("tr");
        dtr.className = "dept" + (expanded ? " show" : "");
        const dtd = document.createElement("td");
        dtd.className = "linecell";
        dtd.textContent = dept;
        dtr.appendChild(dtd);
        let dtotal = 0;
        periods.forEach(p => {
          const v = (byPeriod[p].departments[dept]) || 0;
          dtotal += v;
          const td = document.createElement("td");
          td.textContent = fmtK(v);
          td.classList.add("clickable");
          td.onclick = () => openDrill(null, dept, p, dept);
          if (v < 0) td.classList.add("neg");
          dtr.appendChild(td);
        });
        const dTotalTd = document.createElement("td");
        dTotalTd.textContent = fmtK(dtotal);
        dTotalTd.classList.add("clickable");
        dTotalTd.onclick = () => openDrill(null, dept, "TOTAL", dept, periods);
        if (dtotal < 0) dTotalTd.classList.add("neg");
        dtr.appendChild(dTotalTd);
        body.appendChild(dtr);
      });
    }
  });

  renderStats(periods, byPeriod);
}

function renderStats(periods, byPeriod){
  const ids = matchingFacilityIds();
  document.getElementById("statFacilities").textContent = ids.size;
  const anyFilter = selManagers.size || selLandlords.size || selFacilities.size;
  document.getElementById("statFacilitiesFoot").textContent = anyFilter
    ? "of " + DATA.facilities.length + " in portfolio"
    : "entire portfolio";

  if (periods.length === 0){
    document.getElementById("statRevenue").textContent = "--";
    document.getElementById("statNoi").textContent = "--";
    document.getElementById("statSpark").innerHTML = "";
    return;
  }
  const latest = periods[periods.length-1];
  const rev = byPeriod[latest].operating_revenue;
  const noi = byPeriod[latest].noi;

  const revEl = document.getElementById("statRevenue");
  revEl.textContent = "$" + fmtK(rev) + "K";
  revEl.className = "stat-value";
  document.getElementById("statRevenueFoot").textContent = fmtMonth(latest);

  const noiEl = document.getElementById("statNoi");
  noiEl.textContent = "$" + fmtK(noi) + "K";
  noiEl.className = "stat-value " + (noi >= 0 ? "good" : "bad");
  document.getElementById("statNoiFoot").textContent = fmtMonth(latest);

  const svg = document.getElementById("statSpark");
  const vals = periods.map(p => byPeriod[p].noi);
  const min = Math.min(...vals, 0), max = Math.max(...vals, 0);
  const range = (max - min) || 1;
  const w = 240, h = 40, pad = 3;
  const stepX = vals.length > 1 ? (w - pad*2) / (vals.length - 1) : 0;
  const pts = vals.map((v,i) => {
    const x = pad + i*stepX;
    const y = h - pad - ((v - min) / range) * (h - pad*2);
    return [x,y];
  });
  const zeroY = h - pad - ((0 - min) / range) * (h - pad*2);
  const path = pts.map((pt,i) => (i===0?"M":"L") + pt[0].toFixed(1) + "," + pt[1].toFixed(1)).join(" ");
  const lastPositive = vals[vals.length-1] >= 0;
  svg.innerHTML =
    '<line x1="' + pad + '" y1="' + zeroY.toFixed(1) + '" x2="' + (w-pad) + '" y2="' + zeroY.toFixed(1) + '" stroke="var(--border)" stroke-width="1" stroke-dasharray="2,2"/>' +
    '<path d="' + path + '" fill="none" stroke="' + (lastPositive ? "var(--good)" : "var(--bad)") + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' +
    '<circle cx="' + pts[pts.length-1][0].toFixed(1) + '" cy="' + pts[pts.length-1][1].toFixed(1) + '" r="2.5" fill="' + (lastPositive ? "var(--good)" : "var(--bad)") + '"/>';
  document.getElementById("statSparkFoot").textContent = fmtMonth(periods[0]) + " – " + fmtMonth(latest);
}

const FACILITY_OPTIONS = DATA.facilities
  .slice()
  .sort((a,b) => a.name.localeCompare(b.name))
  .map(f => ({value: f.facility_id, label: f.name}));
const MANAGER_OPTIONS = MANAGERS.map(m => ({value: m, label: m}));
const LANDLORD_OPTIONS = LANDLORDS.map(l => ({value: l, label: l}));

function populateMonthPickers(){
  const fromSel = document.getElementById("fromMonth");
  const toSel = document.getElementById("toMonth");
  fromSel.innerHTML = "";
  toSel.innerHTML = "";
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
  fromSel.onchange = () => {
    rangeFrom = fromSel.value;
    if (rangeFrom > rangeTo) { rangeTo = rangeFrom; toSel.value = rangeTo; }
    render();
  };
  toSel.onchange = () => {
    rangeTo = toSel.value;
    if (rangeTo < rangeFrom) { rangeFrom = rangeTo; fromSel.value = rangeFrom; }
    render();
  };

  document.getElementById("t3Btn").onclick = () => setTrailingRange(3);
  document.getElementById("t12Btn").onclick = () => setTrailingRange(12);
}

// T3/T12 anchor on the latest month actually reported by the CURRENTLY
// SELECTED facilities, not the portfolio overall -- a facility whose most
// recent data is May shouldn't get a July-anchored range just because some
// other facility elsewhere in the portfolio has already reported July.
function availablePeriodsForSelection(){
  const ids = matchingFacilityIds();
  return Array.from(new Set(DATA.waterfall.filter(r => ids.has(r.facility_id)).map(r => r.period))).sort();
}

function setTrailingRange(n){
  const avail = availablePeriodsForSelection();
  if (avail.length === 0) return;
  const anchor = avail[avail.length - 1];
  const startIdx = Math.max(0, avail.length - n);
  rangeFrom = avail[startIdx];
  rangeTo = anchor;
  document.getElementById("fromMonth").value = rangeFrom;
  document.getElementById("toMonth").value = rangeTo;
  render();
}

// Comparing every individual facility side by side stops being readable once
// more than one manager is in view (could span dozens of unrelated
// facilities), so the drill groups at manager level in that case and only
// breaks out to facility level once the selection is within a single manager.
function drillGroupLevel(facilities){
  const managers = new Set(facilities.map(f => f.manager));
  return managers.size > 1 ? "manager" : "facility";
}

function openDrill(rowKey, rowLabel, period, deptName, totalPeriods){
  const facilities = filteredFacilities();
  const ids = new Set(facilities.map(f => f.facility_id));
  const level = drillGroupLevel(facilities);
  const relevantPeriods = period === "TOTAL" ? totalPeriods : [period];

  const amounts = {};   // groupKey -> amount
  const meta = {};      // groupKey -> {label, sub}
  facilities.forEach(f => {
    const key = level === "manager" ? f.manager : String(f.facility_id);
    if (!(key in amounts)) amounts[key] = 0;
    meta[key] = level === "manager"
      ? {label: f.manager, sub: new Set()}
      : {label: f.name, sub: f.manager + " · " + f.landlord};
    if (level === "manager") meta[key].sub.add(f.landlord);
  });

  DATA.waterfall.forEach(r => {
    if (!ids.has(r.facility_id)) return;
    if (!relevantPeriods.includes(r.period)) return;
    const f = facilityById[r.facility_id];
    const key = level === "manager" ? f.manager : String(r.facility_id);
    const v = deptName ? ((r.departments || {})[deptName] || 0) : (r[rowKey] || 0);
    amounts[key] += v;
  });

  const list = Object.keys(amounts)
    .map(key => ({
      label: meta[key].label,
      sub: level === "manager" ? Array.from(meta[key].sub).join(", ") : meta[key].sub,
      amount: amounts[key],
    }))
    .sort((a,b) => b.amount - a.amount);
  const total = list.reduce((s,x) => s + x.amount, 0);

  document.getElementById("drillTitle").textContent = rowLabel;
  document.getElementById("drillSub").textContent =
    (period === "TOTAL" ? "Total, " + fmtMonth(relevantPeriods[0]) + " – " + fmtMonth(relevantPeriods[relevantPeriods.length-1]) : fmtMonth(period))
    + " · by " + level + " · " + list.length + (list.length === 1 ? "" : "s");

  const bodyEl = document.getElementById("drillBody");
  bodyEl.innerHTML = "";
  list.forEach(x => {
    const row = document.createElement("div");
    row.className = "drill-row";
    const left = document.createElement("div");
    left.innerHTML = '<div class="name">' + x.label + '</div><div class="meta">' + x.sub + '</div>';
    const amt = document.createElement("div");
    amt.className = "amt" + (x.amount < 0 ? " neg" : "");
    amt.textContent = "$" + fmtK(x.amount) + "K";
    row.appendChild(left);
    row.appendChild(amt);
    bodyEl.appendChild(row);
  });
  const totalRow = document.createElement("div");
  totalRow.className = "drill-row total";
  const totalAmt = document.createElement("div");
  totalAmt.className = "amt" + (total < 0 ? " neg" : "");
  totalAmt.textContent = "$" + fmtK(total) + "K";
  totalRow.innerHTML = '<div>Total</div>';
  totalRow.appendChild(totalAmt);
  bodyEl.appendChild(totalRow);

  document.getElementById("drillBackdrop").hidden = false;
}

function closeDrill(){ document.getElementById("drillBackdrop").hidden = true; }
document.getElementById("drillClose").onclick = closeDrill;
document.getElementById("drillBackdrop").onclick = (e) => { if (e.target.id === "drillBackdrop") closeDrill(); };
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrill(); });

function refreshAll(){
  const availManagers = new Set(filteredFacilities({ignore:"manager"}).map(f => f.manager));
  const availLandlords = new Set(filteredFacilities({ignore:"landlord"}).map(f => f.landlord));
  const availFacilityIds = new Set(filteredFacilities({ignore:"facility"}).map(f => f.facility_id));

  Array.from(selManagers).forEach(m => { if (!availManagers.has(m)) selManagers.delete(m); });
  Array.from(selLandlords).forEach(l => { if (!availLandlords.has(l)) selLandlords.delete(l); });
  Array.from(selFacilities).forEach(id => { if (!availFacilityIds.has(id)) selFacilities.delete(id); });

  buildChips(document.getElementById("managerChips"), MANAGER_OPTIONS, selManagers,
    new Set(MANAGERS.filter(m => !availManagers.has(m))));
  buildChips(document.getElementById("landlordChips"), LANDLORD_OPTIONS, selLandlords,
    new Set(LANDLORDS.filter(l => !availLandlords.has(l))));
  buildChips(document.getElementById("facilityChips"), FACILITY_OPTIONS, selFacilities,
    new Set(FACILITY_OPTIONS.map(o => o.value).filter(id => !availFacilityIds.has(id))));

  render();
}

populateMonthPickers();
refreshAll();
</script>
"""

HTML = HTML.replace("__DATA_JSON__", data_json)
HTML = HTML.replace("__MANAGERS_JSON__", json.dumps(managers))
HTML = HTML.replace("__LANDLORDS_JSON__", json.dumps(landlords))

out_path = SCRATCH / "t12_waterfall.html"
out_path.write_text(HTML)
print("wrote", out_path, len(HTML), "bytes")
