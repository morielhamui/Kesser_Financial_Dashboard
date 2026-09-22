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
.sub{color:var(--muted); font-size:14px; max-width:72ch; line-height:1.5;}

.picker-bar{display:flex; flex-direction:column; gap:12px; background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow);}
.picker-row{display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.nav-btn{
  font-family:"IBM Plex Mono",monospace; font-size:15px; font-weight:600; color:var(--ink-soft);
  background:var(--surface-2); border:1px solid var(--border); border-radius:8px;
  padding:6px 12px; cursor:pointer;
}
.nav-btn:hover{border-color:var(--border-strong);}
.nav-btn:disabled{opacity:.35; cursor:not-allowed;}
.facility-select{
  font-family:"IBM Plex Sans",sans-serif; font-size:15px; font-weight:600; color:var(--ink);
  background:var(--surface-2); border:1px solid var(--border); border-radius:8px;
  padding:7px 12px; flex:1; min-width:220px; max-width:420px;
}
.badge{font-size:11.5px; font-weight:500; color:var(--ink-soft); background:var(--surface-2); border:1px solid var(--border); border-radius:999px; padding:4px 11px; white-space:nowrap;}
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

.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px;}
.stat-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px;}
.stat-label{font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);}
.stat-value{font-family:"IBM Plex Mono",monospace; font-size:24px; font-weight:600; font-variant-numeric:tabular-nums;}
.stat-value.good{color:var(--good);} .stat-value.bad{color:var(--bad);}
.stat-foot{font-size:12px; color:var(--muted);}
.spark{width:100%; height:34px; display:block;}

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
tr.gl td.linecell{padding-left:52px; color:var(--muted); font-size:11.5px; font-weight:400;}
tr.gl-dept td.linecell{padding-left:52px; color:var(--muted); font-size:11.5px; font-weight:400;}
tr.gl td, tr.gl-dept td{color:var(--muted); font-size:11.5px;}
tr.hidden-row{display:none;}

.expand-btn{
  background:none; border:none; cursor:pointer; padding:0; margin-right:6px;
  color:var(--muted); font-size:11px; display:inline-flex; align-items:center; justify-content:center;
  width:14px; transition:transform .15s;
}
.expand-btn.open{transform:rotate(90deg);}
.no-gl{color:var(--muted); font-style:italic;}
.neg{color:var(--bad);}
.pos-hero{color:var(--good);} .neg-hero{color:var(--bad);}

.footnote{font-size:11.5px; color:var(--muted); line-height:1.5; padding:2px 4px;}
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="wrap">
  <div class="masthead">
    <span class="eyebrow">Kesser Financial Dashboard</span>
    <h1>T12 by Facility</h1>
    <p class="sub">Full P&amp;L waterfall for one facility at a time, with every line &mdash; not just Operating Expense &mdash; expandable all the way down to its GL accounts.</p>
  </div>

  <div class="picker-bar">
    <div class="picker-row">
      <button class="nav-btn" id="prevBtn" title="Previous facility">&larr;</button>
      <select class="facility-select" id="facilitySelect"></select>
      <button class="nav-btn" id="nextBtn" title="Next facility">&rarr;</button>
      <span class="badge" id="managerBadge">&nbsp;</span>
      <span class="badge" id="landlordBadge">&nbsp;</span>
      <div class="range-picker">
        <select id="fromMonth"></select>
        <span class="range-sep">&ndash;</span>
        <select id="toMonth"></select>
        <button class="chip" id="t3Btn" type="button">T3</button>
        <button class="chip" id="t12Btn" type="button">T12</button>
      </div>
    </div>
  </div>

  <div class="stats">
    <div class="stat-card">
      <span class="stat-label">Operating Revenue &middot; latest month</span>
      <span class="stat-value" id="statRevenue">&ndash;</span>
      <span class="stat-foot" id="statRevenueFoot">&nbsp;</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">NOI &middot; latest month</span>
      <span class="stat-value" id="statNoi">&ndash;</span>
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
  <p class="footnote">Amounts in thousands ($K). Negative values shown in red with parentheses. Click the arrow next to any line &mdash; Operating Revenue, each Operating Expense department, G&amp;A, Real Estate Tax, Capital Expenses, Management Fees, and Other Income/Expense &mdash; to reveal the individual GL accounts summed into it, sorted largest to smallest. "Management Fees" here is the operator's own reported management fee line, separate from Kesser's landlord-collected fee revenue.</p>
</div>

<script>
const DATA = __DATA_JSON__;
const facilityById = {};
DATA.facilities.forEach(f => { facilityById[f.facility_id] = f; });
const SORTED_FACILITIES = DATA.facilities.slice().sort((a,b) => a.name.localeCompare(b.name));

const WATERFALL_BY_KEY = {};
DATA.waterfall.forEach(r => { WATERFALL_BY_KEY[r.facility_id + "|" + r.period] = r; });

const PERIOD_IDX = {}; DATA.periods.forEach((p,i) => PERIOD_IDX[p] = i);

const EXPENSE_DEPT_ORDER = ["Nursing","Ancillary","Activities","Social Service","Dietary","Housekeeping","Laundry and Linen","Employee Welfare","Plant","Marketing"];

const ROWS = [
  {key:"operating_revenue", label:"Operating Revenue", type:"line", glKey:"operating_revenue"},
  {key:"operating_expense", label:"Operating Expense", type:"expandable"},
  {key:"operating_income", label:"Operating Income", type:"subtotal"},
  {key:"ga", label:"G&A Expense", type:"line", glKey:"ga"},
  {key:"ebitdarm", label:"EBITDARM", type:"subtotal"},
  {key:"real_estate_tax", label:"Real Estate Tax", type:"line", glKey:"real_estate_tax"},
  {key:"ebidarm", label:"EBIDARM", type:"subtotal"},
  {key:"capital_expenses", label:"Capital Expenses", type:"line", glKey:"capital_expenses"},
  {key:"earnings_before_mgmt_fees", label:"Earnings before Mgmt Fees", type:"subtotal"},
  {key:"management_fees", label:"Management Fees", type:"line", glKey:"management_fees"},
  {key:"earnings", label:"Earnings", type:"subtotal"},
  {key:"other_income_expense", label:"Other Income / Expense", type:"line", glKey:"other_income_expense"},
  {key:"noi", label:"NOI", type:"hero"},
];

let currentFacilityId = SORTED_FACILITIES[0].facility_id;
let rangeFrom, rangeTo;
let expandedOpex = false;
let expandedDept = new Set();      // department names expanded to GL
let expandedTopLine = new Set();   // row keys (glKey) expanded to GL

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

function facilityPeriods(facilityId){
  return Object.keys(WATERFALL_BY_KEY).filter(k => k.startsWith(facilityId + "|")).map(k => k.split("|")[1]).sort();
}

function populateFacilitySelect(){
  const sel = document.getElementById("facilitySelect");
  sel.innerHTML = "";
  SORTED_FACILITIES.forEach(f => {
    const o = document.createElement("option");
    o.value = f.facility_id; o.textContent = f.name;
    if (f.facility_id === currentFacilityId) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => { currentFacilityId = parseInt(sel.value, 10); onFacilityChange(); };
}
function currentIndex(){ return SORTED_FACILITIES.findIndex(f => f.facility_id === currentFacilityId); }
document.getElementById("prevBtn").onclick = () => {
  const i = currentIndex();
  if (i > 0){ currentFacilityId = SORTED_FACILITIES[i-1].facility_id; onFacilityChange(); }
};
document.getElementById("nextBtn").onclick = () => {
  const i = currentIndex();
  if (i < SORTED_FACILITIES.length - 1){ currentFacilityId = SORTED_FACILITIES[i+1].facility_id; onFacilityChange(); }
};

// currentGlIndex[groupKey][label][period] = amount -- built once per
// facility change (not per render/cell) since DATA.gl has ~69,000 rows
// across the whole portfolio; re-scanning it for every GL cell on every
// expand click would be needlessly slow.
let currentGlIndex = {};
function buildGlIndex(facilityId){
  const idx = {};
  DATA.gl.forEach(([fid, pIdx, gIdx, lIdx, amt]) => {
    if (fid !== facilityId) return;
    const groupKey = DATA.groups[gIdx];
    const label = DATA.labels[lIdx];
    const period = DATA.periods[pIdx];
    (((idx[groupKey] ??= {})[label] ??= {})[period] = ((idx[groupKey][label][period]) || 0) + amt);
  });
  return idx;
}

function onFacilityChange(){
  populateFacilitySelect();
  document.getElementById("prevBtn").disabled = currentIndex() === 0;
  document.getElementById("nextBtn").disabled = currentIndex() === SORTED_FACILITIES.length - 1;
  const f = facilityById[currentFacilityId];
  document.getElementById("managerBadge").textContent = f.manager;
  document.getElementById("landlordBadge").textContent = f.landlord;
  expandedOpex = false; expandedDept = new Set(); expandedTopLine = new Set();
  currentGlIndex = buildGlIndex(currentFacilityId);
  const periods = facilityPeriods(currentFacilityId);
  rangeFrom = periods[0]; rangeTo = periods[periods.length - 1];
  populateMonthPickers();
  render();
}

function populateMonthPickers(){
  const periods = facilityPeriods(currentFacilityId);
  const fromSel = document.getElementById("fromMonth");
  const toSel = document.getElementById("toMonth");
  fromSel.innerHTML = ""; toSel.innerHTML = "";
  periods.forEach(p => {
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
function setTrailingRange(n){
  const periods = facilityPeriods(currentFacilityId);
  if (periods.length === 0) return;
  const anchor = periods[periods.length - 1];
  const startIdx = Math.max(0, periods.length - n);
  rangeFrom = periods[startIdx]; rangeTo = anchor;
  document.getElementById("fromMonth").value = rangeFrom;
  document.getElementById("toMonth").value = rangeTo;
  render();
}

function glLinesFor(groupKey, periods){
  const byLabel = currentGlIndex[groupKey];
  if (!byLabel) return [];
  const totals = {};
  Object.entries(byLabel).forEach(([label, byPeriod]) => {
    let sum = 0;
    periods.forEach(p => { sum += byPeriod[p] || 0; });
    if (sum !== 0) totals[label] = sum;
  });
  return Object.entries(totals).sort((a,b) => Math.abs(b[1]) - Math.abs(a[1]));
}

function render(){
  const periods = facilityPeriods(currentFacilityId).filter(p => p >= rangeFrom && p <= rangeTo);
  const head = document.getElementById("headRow");
  const body = document.getElementById("bodyRows");
  head.innerHTML = ""; body.innerHTML = "";

  const lineTh = document.createElement("th");
  lineTh.className = "linecol"; lineTh.textContent = "Line Item";
  head.appendChild(lineTh);
  periods.forEach(p => { const th = document.createElement("th"); th.textContent = fmtMonth(p); head.appendChild(th); });
  const totalTh = document.createElement("th"); totalTh.textContent = "Total"; head.appendChild(totalTh);

  const depts = (() => {
    const all = new Set();
    periods.forEach(p => {
      const row = WATERFALL_BY_KEY[currentFacilityId + "|" + p];
      if (row) Object.keys(row.departments).forEach(d => all.add(d));
    });
    const ordered = EXPENSE_DEPT_ORDER.filter(d => all.has(d));
    const rest = Array.from(all).filter(d => !EXPENSE_DEPT_ORDER.includes(d)).sort();
    return ordered.concat(rest);
  })();

  function appendGlRows(groupKey, periods, indentClass){
    const lines = glLinesFor(groupKey, periods);
    if (lines.length === 0){
      const tr = document.createElement("tr"); tr.className = indentClass + " show";
      const td = document.createElement("td"); td.className = "linecell no-gl"; td.textContent = "No GL detail available"; td.colSpan = periods.length + 2;
      tr.appendChild(td); body.appendChild(tr);
      return;
    }
    const byLabel = currentGlIndex[groupKey] || {};
    lines.forEach(([label]) => {
      const tr = document.createElement("tr"); tr.className = indentClass + " show";
      const labelTd = document.createElement("td"); labelTd.className = "linecell"; labelTd.textContent = label;
      tr.appendChild(labelTd);
      let total = 0;
      const byPeriod = byLabel[label] || {};
      periods.forEach(p => {
        const v = byPeriod[p] || 0;
        total += v;
        const td = document.createElement("td"); td.textContent = fmtK(v);
        if (v < 0) td.classList.add("neg");
        tr.appendChild(td);
      });
      const totalTd = document.createElement("td"); totalTd.textContent = fmtK(total);
      if (total < 0) totalTd.classList.add("neg");
      tr.appendChild(totalTd);
      body.appendChild(tr);
    });
  }

  ROWS.forEach(row => {
    const tr = document.createElement("tr");
    if (row.type === "subtotal") tr.className = "subtotal";
    if (row.type === "hero") tr.className = "hero";

    const labelTd = document.createElement("td");
    labelTd.className = "linecell";
    const canExpand = row.type === "expandable" || !!row.glKey;
    if (canExpand){
      const isOpen = row.type === "expandable" ? expandedOpex : expandedTopLine.has(row.key);
      const btn = document.createElement("button");
      btn.className = "expand-btn" + (isOpen ? " open" : "");
      btn.textContent = "▸";
      btn.onclick = () => {
        if (row.type === "expandable") expandedOpex = !expandedOpex;
        else { if (expandedTopLine.has(row.key)) expandedTopLine.delete(row.key); else expandedTopLine.add(row.key); }
        render();
      };
      labelTd.appendChild(btn);
      labelTd.appendChild(document.createTextNode(row.label));
    } else {
      labelTd.textContent = row.label;
    }
    tr.appendChild(labelTd);

    let total = 0;
    periods.forEach(p => {
      const wRow = WATERFALL_BY_KEY[currentFacilityId + "|" + p];
      const v = wRow ? (wRow[row.key] || 0) : 0;
      total += v;
      const td = document.createElement("td");
      td.textContent = fmtK(v);
      if (row.type === "hero") td.classList.add(v >= 0 ? "pos-hero" : "neg-hero");
      else if (v < 0) td.classList.add("neg");
      tr.appendChild(td);
    });
    const totalTd = document.createElement("td");
    totalTd.textContent = fmtK(total);
    if (row.type === "hero") totalTd.classList.add(total >= 0 ? "pos-hero" : "neg-hero");
    else if (total < 0) totalTd.classList.add("neg");
    tr.appendChild(totalTd);
    body.appendChild(tr);

    if (row.glKey && expandedTopLine.has(row.key)){
      appendGlRows(row.glKey, periods, "gl");
    }

    if (row.type === "expandable"){
      depts.forEach(dept => {
        const dtr = document.createElement("tr");
        dtr.className = "dept" + (expandedOpex ? " show" : "");
        const deptOpen = expandedDept.has(dept);
        const dtd = document.createElement("td"); dtd.className = "linecell";
        const dbtn = document.createElement("button");
        dbtn.className = "expand-btn" + (deptOpen ? " open" : "");
        dbtn.textContent = "▸";
        dbtn.onclick = (e) => { e.stopPropagation(); if (expandedDept.has(dept)) expandedDept.delete(dept); else expandedDept.add(dept); render(); };
        dtd.appendChild(dbtn);
        dtd.appendChild(document.createTextNode(dept));
        dtr.appendChild(dtd);
        let dtotal = 0;
        periods.forEach(p => {
          const wRow = WATERFALL_BY_KEY[currentFacilityId + "|" + p];
          const v = wRow ? (wRow.departments[dept] || 0) : 0;
          dtotal += v;
          const td = document.createElement("td"); td.textContent = fmtK(v);
          if (v < 0) td.classList.add("neg");
          dtr.appendChild(td);
        });
        const dTotalTd = document.createElement("td"); dTotalTd.textContent = fmtK(dtotal);
        if (dtotal < 0) dTotalTd.classList.add("neg");
        dtr.appendChild(dTotalTd);
        body.appendChild(dtr);

        if (expandedOpex && deptOpen){
          appendGlRows("opex:" + dept, periods, "gl-dept");
        }
      });
    }
  });

  renderStats(periods);
}

function renderStats(periods){
  if (periods.length === 0){
    document.getElementById("statRevenue").textContent = "–";
    document.getElementById("statNoi").textContent = "–";
    document.getElementById("statSpark").innerHTML = "";
    return;
  }
  const latest = periods[periods.length-1];
  const latestRow = WATERFALL_BY_KEY[currentFacilityId + "|" + latest] || {};
  const rev = latestRow.operating_revenue || 0;
  const noi = latestRow.noi || 0;

  const revEl = document.getElementById("statRevenue");
  revEl.textContent = "$" + fmtK(rev) + "K";
  document.getElementById("statRevenueFoot").textContent = fmtMonth(latest);

  const noiEl = document.getElementById("statNoi");
  noiEl.textContent = "$" + fmtK(noi) + "K";
  noiEl.className = "stat-value " + (noi >= 0 ? "good" : "bad");
  document.getElementById("statNoiFoot").textContent = fmtMonth(latest);

  const svg = document.getElementById("statSpark");
  const vals = periods.map(p => (WATERFALL_BY_KEY[currentFacilityId + "|" + p] || {}).noi ?? null);
  const clean = vals.filter(v => v !== null);
  if (clean.length < 2){ svg.innerHTML = ""; return; }
  const min = Math.min(...clean, 0), max = Math.max(...clean, 0);
  const range = (max - min) || 1;
  const w = 240, h = 40, pad = 3;
  const stepX = vals.length > 1 ? (w - pad*2) / (vals.length - 1) : 0;
  const pts = vals.map((v,i) => [pad + i*stepX, h - pad - ((v - min) / range) * (h - pad*2)]);
  const zeroY = h - pad - ((0 - min) / range) * (h - pad*2);
  const path = pts.map((pt,i) => (i===0?"M":"L") + pt[0].toFixed(1) + "," + pt[1].toFixed(1)).join(" ");
  const lastPositive = vals[vals.length-1] >= 0;
  svg.innerHTML =
    '<line x1="' + pad + '" y1="' + zeroY.toFixed(1) + '" x2="' + (w-pad) + '" y2="' + zeroY.toFixed(1) + '" stroke="var(--border)" stroke-width="1" stroke-dasharray="2,2"/>' +
    '<path d="' + path + '" fill="none" stroke="' + (lastPositive ? "var(--good)" : "var(--bad)") + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' +
    '<circle cx="' + pts[pts.length-1][0].toFixed(1) + '" cy="' + pts[pts.length-1][1].toFixed(1) + '" r="2.5" fill="' + (lastPositive ? "var(--good)" : "var(--bad)") + '"/>';
  document.getElementById("statSparkFoot").textContent = fmtMonth(periods[0]) + " – " + fmtMonth(periods[periods.length-1]);
}

onFacilityChange();
</script>
"""

HTML = HTML.replace("__DATA_JSON__", data_json)

out_path = SCRATCH / "t12_facility.html"
out_path.write_text(HTML)
print("wrote", out_path, len(HTML), "bytes")
