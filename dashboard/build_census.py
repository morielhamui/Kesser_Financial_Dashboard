import json, pathlib

SCRATCH = pathlib.Path(__file__).resolve().parent
data = json.loads((SCRATCH / "census_data.json").read_text())

managers = sorted(set(f["manager"] for f in data["facilities"]))
landlords = sorted(set(f["landlord"] for f in data["facilities"]))

data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

HTML = r"""<title>Census &amp; Occupancy</title>
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
  /* Dataviz skill's validated default categorical palette (8 hues, fixed
     order -- the order itself is the CVD-safety mechanism, never
     reordered or cycled). Payor buckets beyond the 7th fold into "Other"
     (slot 8) rather than adding a 9th color. */
  --series-1:#2a78d6; --series-2:#eb6834; --series-3:#1baf7a; --series-4:#eda100;
  --series-5:#e87ba4; --series-6:#008300; --series-7:#4a3aa7; --series-8:#e34948;
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
    --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70; --series-4:#c98500;
    --series-5:#d55181; --series-6:#008300; --series-7:#9085e9; --series-8:#e66767;
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
  --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70; --series-4:#c98500;
  --series-5:#d55181; --series-6:#008300; --series-7:#9085e9; --series-8:#e66767;
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
.op-card .op-delta{font-size:11px; display:flex; align-items:center; gap:3px;}
.op-card .op-delta.up{color:var(--good);} .op-card .op-delta.down{color:var(--bad);} .op-card .op-delta.flat{color:var(--muted);}
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
tbody td.clickable{cursor:pointer;}
tbody td.clickable:hover{box-shadow:inset 0 0 0 1px var(--accent);}
.no-beds-badge{font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--warn); background:var(--warn-soft); border-radius:5px; padding:1px 6px; margin-left:7px; vertical-align:1px;}

/* Payor mix: donut + 100%-stacked month columns */
.mix-layout{display:flex; gap:24px; flex-wrap:wrap; align-items:flex-start;}
.donut-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:18px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:12px; flex:0 0 260px;}
.donut-card h3{font-size:13px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.04em;}
.donut-svg{width:180px; height:180px; align-self:center;}
.legend{display:flex; flex-direction:column; gap:6px; font-size:12.5px;}
.legend-row{display:flex; align-items:center; gap:8px;}
.legend-swatch{width:10px; height:10px; border-radius:3px; flex:0 0 auto;}
.legend-label{flex:1; color:var(--ink-soft);}
.legend-pct{font-family:"IBM Plex Mono",monospace; color:var(--ink); font-variant-numeric:tabular-nums;}

.stack-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:18px; box-shadow:var(--shadow); flex:1 1 480px; min-width:0;}
.stack-card h3{font-size:13px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; margin-bottom:12px;}
.stack-scroll{overflow-x:auto; padding-bottom:6px;}
.stack-cols{display:flex; align-items:flex-end; gap:4px; height:180px; min-width:max-content;}
.stack-col{display:flex; flex-direction:column-reverse; width:22px; height:100%; border-radius:2px; overflow:hidden; flex:0 0 auto;}
.stack-seg{width:100%;}
.stack-labels{display:flex; gap:4px; margin-top:6px; min-width:max-content;}
.stack-label{width:22px; flex:0 0 auto; font-size:9px; color:var(--muted); text-align:center; writing-mode:vertical-rl; transform:rotate(180deg); height:34px;}

.hfs-cell{position:relative;}
.hfs-cell .ours{font-weight:600;}
.hfs-cell .hfs{color:var(--muted); font-size:11px;}
.hfs-good{color:var(--good);} .hfs-bad{color:var(--bad);}
.hfs-flagged{background:var(--bad-soft); box-shadow:inset 0 0 0 1px var(--bad);}
.flag-row{display:flex; justify-content:space-between; align-items:center; gap:10px; padding:9px 18px; font-size:13px; border-bottom:1px solid var(--border);}
.flag-row:last-child{border-bottom:none;}
.flag-row .name{color:var(--ink); font-weight:500;}
.flag-row .meta{color:var(--muted); font-size:11.5px;}
.flag-row .variance{font-family:"IBM Plex Mono",monospace; font-weight:600; color:var(--bad); white-space:nowrap;}

.stat-strip{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px;}
.stat-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px;}
.stat-label{font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);}
.stat-value{font-family:"IBM Plex Mono",monospace; font-size:24px; font-weight:600; font-variant-numeric:tabular-nums;}
.stat-foot{font-size:12px; color:var(--muted);}

.expand-btn{
  background:none; border:none; cursor:pointer; padding:0; margin-right:6px;
  color:var(--muted); font-size:11px; display:inline-flex; align-items:center; justify-content:center;
  width:14px; transition:transform .15s;
}
.expand-btn.open{transform:rotate(90deg);}
tr.sub{display:none;} tr.sub.show{display:table-row;}
tr.sub td.linecell{padding-left:32px; color:var(--muted); font-size:12.5px;}
tr.sub td{color:var(--muted); font-size:12.5px;}

.footnote{font-size:11.5px; color:var(--muted); line-height:1.5; padding:2px 4px;}

.drill-backdrop{position:fixed; inset:0; background:rgba(20,28,26,.45); display:flex; align-items:center; justify-content:center; padding:20px; z-index:50;}
.drill-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); max-width:520px; width:100%; max-height:82vh; display:flex; flex-direction:column; overflow:hidden;}
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
.drill-row.total{background:var(--surface-2); font-weight:700;}
.drill-row.total .amt{color:var(--ink); font-weight:700;}
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="wrap">
  <div class="masthead">
    <span class="eyebrow">Kesser Financial Dashboard</span>
    <h1>Census &amp; Occupancy</h1>
    <p class="sub">Resident mix by payor, occupancy against licensed beds, and calculated Medicaid rates checked against Illinois HFS's own published rate list. Shares the same filters and month range as the other pages.</p>
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
    <p class="filter-hint">Click a chip to select it on its own. Ctrl/Cmd-click to add it to the current selection. Click any occupancy number to see the facilities behind it.</p>
  </div>

  <div class="section">
    <div class="section-head">
      <h2>Census Mix by Payor</h2>
      <span class="section-note">Share of resident days by payor</span>
    </div>
    <div class="mix-layout">
      <div class="donut-card">
        <h3 id="donutTitle">Latest month</h3>
        <svg class="donut-svg" id="donutSvg" viewBox="0 0 100 100"></svg>
        <div class="legend" id="donutLegend"></div>
      </div>
      <div class="stack-card">
        <h3>Trend across selected months</h3>
        <div class="stack-scroll">
          <div class="stack-cols" id="stackCols"></div>
          <div class="stack-labels" id="stackLabels"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-head">
      <h2>Occupancy</h2>
      <span class="section-note">Resident days &divide; (licensed beds &times; days in month)</span>
    </div>
    <div class="card-grid" id="occCards"></div>
    <div class="table-card">
      <div class="table-scroll">
        <table id="occTable">
          <thead><tr id="occHead"></tr></thead>
          <tbody id="occBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-head">
      <h2>Medicaid Rate vs. Illinois HFS</h2>
      <span class="section-note">Calculated Medicaid PPD (fee-for-service only) vs. HFS's published quarterly rate</span>
    </div>
    <div class="stat-strip">
      <div class="stat-card">
        <span class="stat-label">Facility-quarters compared</span>
        <span class="stat-value" id="hfsCompared">&ndash;</span>
        <span class="stat-foot">in current filter</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Within &plusmn;5%</span>
        <span class="stat-value" id="hfsWithinTol">&ndash;</span>
        <span class="stat-foot" id="hfsWithinTolFoot">&nbsp;</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Median variance</span>
        <span class="stat-value" id="hfsMedian">&ndash;</span>
        <span class="stat-foot">ours vs. HFS</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Flagged (&gt;5%)</span>
        <span class="stat-value" id="hfsFlaggedCount">&ndash;</span>
        <span class="stat-foot">facility-quarters to review</span>
      </div>
    </div>
    <div class="table-card" id="flaggedCard" hidden>
      <div style="padding:14px 18px 4px; font-size:12px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.04em;">Flagged facility-quarters</div>
      <div id="flaggedList"></div>
    </div>
    <div class="table-card">
      <div class="table-scroll">
        <table id="hfsTable">
          <thead><tr id="hfsHead"></tr></thead>
          <tbody id="hfsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <p class="footnote">Occupancy excludes the 2 facilities with no recorded bed count (flagged "no beds") from both the numerator and denominator, so the blended % isn't distorted by an unknown capacity. Payor mix folds smaller payors (Veterans, Assisted Living, Independent Living, Medicare B, and any unmatched line) into "Other" to keep the chart's colors distinguishable &mdash; the underlying figures keep full payor detail. HFS comparison uses the traditional fee-for-service Medicaid payor only, never Managed Medicaid, since Medicaid MCOs negotiate their own contracted rates rather than following HFS's published fee schedule; blank cells mean we have no Medicaid census/revenue for that facility that quarter. Facility-quarters where our calculated rate differs from HFS's published rate by more than 5% are flagged (&#9888;&#65039;, red background) for review. See PROJECT_RULES.md section 5 for the full methodology.</p>
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
let selManagers = new Set(), selLandlords = new Set(), selFacilities = new Set();
let rangeFrom = PERIODS_ALL[0], rangeTo = PERIODS_ALL[PERIODS_ALL.length - 1];
let expandedOcc = new Set();

// Chart-only payor grouping: the 7 most material payors get their own
// slot; everything else folds into "Other" to stay within the validated
// 8-hue categorical palette (dataviz skill) -- the table/drill data below
// keeps full payor detail regardless.
const CHART_PAYORS = ["Medicaid","Managed Medicaid","Medicare","Private","Managed Medicare","Insurance/Commercial","Hospice"];
const CHART_COLORS = ["var(--series-1)","var(--series-2)","var(--series-3)","var(--series-4)","var(--series-5)","var(--series-6)","var(--series-7)","var(--series-8)"];

// Facility-quarters where our calculated Medicaid rate differs from HFS's
// published rate by more than this get flagged for review.
const HFS_FLAG_PCT = 5;

function fmtMonth(period){
  const [y,m] = period.split("-");
  const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return names[parseInt(m,10)-1] + " '" + y.slice(2);
}
function fmtPct(v){ return v === null || v === undefined ? "–" : (v*100).toFixed(1) + "%"; }
function fmtDollarK(v){
  const k = v/1000; const abs = Math.abs(k);
  const str = abs.toLocaleString(undefined,{maximumFractionDigits:1, minimumFractionDigits:1});
  return v < 0 ? "(" + str + "K)" : "$" + str + "K";
}
function daysInMonth(period){
  const [y,m] = period.split("-").map(Number);
  return new Date(y, m, 0).getDate();
}

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
function managersInScope(){ return Array.from(new Set(filteredFacilities().map(f => f.manager))).sort(); }
function facilitiesForManager(managerName){ return filteredFacilities().filter(f => f.manager === managerName).map(f => f.facility_id); }

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

// --- Payor mix -------------------------------------------------------------
function mixForPeriod(facIds, period){
  const totals = {};
  facIds.forEach(fid => {
    const row = ROW_BY_KEY[fid + "|" + period];
    if (!row) return;
    Object.entries(row.census_by_payor).forEach(([payor, days]) => {
      totals[payor] = (totals[payor] || 0) + days;
    });
  });
  return totals;
}
function chartBucket(totals){
  const buckets = {}; CHART_PAYORS.forEach(p => buckets[p] = 0); buckets["Other"] = 0;
  Object.entries(totals).forEach(([payor, days]) => {
    buckets[CHART_PAYORS.includes(payor) ? payor : "Other"] += days;
  });
  return buckets;
}
function renderDonut(facIds, periods){
  const latest = periods[periods.length - 1];
  document.getElementById("donutTitle").textContent = latest ? fmtMonth(latest) : "No data";
  const svg = document.getElementById("donutSvg");
  const legend = document.getElementById("donutLegend");
  if (!latest){ svg.innerHTML = ""; legend.innerHTML = '<div style="color:var(--muted);font-size:12px;">No census data.</div>'; return; }
  const buckets = chartBucket(mixForPeriod(facIds, latest));
  const order = [...CHART_PAYORS, "Other"];
  const total = order.reduce((s,p) => s + buckets[p], 0);
  if (total === 0){ svg.innerHTML = ""; legend.innerHTML = '<div style="color:var(--muted);font-size:12px;">No census data.</div>'; return; }

  let cumulative = 0;
  const cx = 50, cy = 50, r = 40, strokeW = 18;
  const circumference = 2 * Math.PI * r;
  let arcs = "";
  order.forEach((payor, i) => {
    const frac = buckets[payor] / total;
    if (frac <= 0) return;
    const dash = frac * circumference;
    const gap = circumference - dash;
    const offset = -cumulative * circumference;
    arcs += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${CHART_COLORS[i]}" stroke-width="${strokeW}" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${offset}" transform="rotate(-90 ${cx} ${cy})"></circle>`;
    cumulative += frac;
  });
  svg.innerHTML = arcs;

  legend.innerHTML = "";
  order.forEach((payor, i) => {
    if (buckets[payor] <= 0) return;
    const pct = buckets[payor] / total;
    const row = document.createElement("div"); row.className = "legend-row";
    row.innerHTML = `<span class="legend-swatch" style="background:${CHART_COLORS[i]}"></span><span class="legend-label">${payor}</span><span class="legend-pct">${(pct*100).toFixed(1)}%</span>`;
    legend.appendChild(row);
  });
}
function renderStack(facIds, periods){
  const cols = document.getElementById("stackCols");
  const labels = document.getElementById("stackLabels");
  cols.innerHTML = ""; labels.innerHTML = "";
  const order = [...CHART_PAYORS, "Other"];
  periods.forEach(p => {
    const buckets = chartBucket(mixForPeriod(facIds, p));
    const total = order.reduce((s,x) => s + buckets[x], 0);
    const col = document.createElement("div"); col.className = "stack-col";
    if (total > 0){
      order.forEach((payor, i) => {
        const frac = buckets[payor] / total;
        if (frac <= 0) return;
        const seg = document.createElement("div");
        seg.className = "stack-seg";
        seg.style.height = (frac*100) + "%";
        seg.style.background = CHART_COLORS[i];
        seg.title = payor + ": " + (frac*100).toFixed(1) + "%";
        col.appendChild(seg);
      });
    }
    cols.appendChild(col);
    const lbl = document.createElement("div"); lbl.className = "stack-label"; lbl.textContent = fmtMonth(p);
    labels.appendChild(lbl);
  });
}

// --- Occupancy ---------------------------------------------------------
function occForFacilities(facIds, periods){
  let days = 0, bedDays = 0;
  facIds.forEach(fid => {
    const fac = facilityById[fid];
    if (!fac.total_beds) return;
    periods.forEach(p => {
      const row = ROW_BY_KEY[fid + "|" + p];
      if (!row) return;
      days += row.resident_days;
      bedDays += fac.total_beds * daysInMonth(p);
    });
  });
  return {days, bedDays, pct: bedDays > 0 ? days / bedDays : null};
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
function renderOccCards(){
  const container = document.getElementById("occCards");
  container.innerHTML = "";
  const managers = managersInScope();
  const periods = periodsInRange();
  managers.forEach(mgr => {
    const facIds = facilitiesForManager(mgr);
    const series = periods.map(p => occForFacilities(facIds, [p]).pct);
    const hasAny = series.some(v => v !== null);
    const card = document.createElement("div"); card.className = "op-card";
    const name = document.createElement("div"); name.className = "op-name"; name.textContent = mgr;
    card.appendChild(name);
    if (!hasAny){
      const hasBeds = facIds.some(fid => facilityById[fid].total_beds);
      const hasCensus = periods.some(p => facIds.some(fid => ROW_BY_KEY[fid + "|" + p]));
      const val = document.createElement("div"); val.className = "op-value no-data";
      val.textContent = !hasCensus ? "No census data" : !hasBeds ? "No bed data" : "No data";
      card.appendChild(val); container.appendChild(card); return;
    }
    let latestIdx = -1;
    for (let i = series.length - 1; i >= 0; i--){ if (series[i] !== null){ latestIdx = i; break; } }
    const latest = latestIdx === -1 ? null : series[latestIdx];
    const prev = latestIdx > 0 ? series[latestIdx - 1] : null;
    const value = document.createElement("div"); value.className = "op-value"; value.textContent = latest === null ? "–" : fmtPct(latest);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class","op-spark"); svg.setAttribute("viewBox","0 0 160 28"); svg.setAttribute("preserveAspectRatio","none");
    drawSpark(svg, series);
    const delta = document.createElement("div");
    if (latest !== null && prev !== null){
      const ptsChange = (latest - prev) * 100;
      delta.className = "op-delta " + (ptsChange > 0.2 ? "up" : ptsChange < -0.2 ? "down" : "flat");
      delta.textContent = (ptsChange >= 0 ? "▲ " : "▼ ") + Math.abs(ptsChange).toFixed(1) + " pts vs prior mo.";
    } else { delta.className = "op-delta flat"; delta.textContent = "—"; }
    card.appendChild(value); card.appendChild(svg); card.appendChild(delta);
    container.appendChild(card);
  });
}
function renderOccTable(){
  const head = document.getElementById("occHead"); const body = document.getElementById("occBody");
  head.innerHTML = ""; body.innerHTML = "";
  const managers = managersInScope(); const periods = periodsInRange();
  const lineTh = document.createElement("th"); lineTh.className = "linecol"; lineTh.textContent = "Operator"; head.appendChild(lineTh);
  periods.forEach(p => { const th = document.createElement("th"); th.textContent = fmtMonth(p); head.appendChild(th); });
  const avgTh = document.createElement("th"); avgTh.textContent = "Avg"; head.appendChild(avgTh);
  if (managers.length === 0){
    const tr = document.createElement("tr"); const td = document.createElement("td"); td.className="linecell"; td.textContent="No operators match the current filters."; tr.appendChild(td); body.appendChild(tr); return;
  }
  managers.forEach(mgr => {
    const facIds = facilitiesForManager(mgr);
    const hasBeds = facIds.some(fid => facilityById[fid].total_beds);
    const hasCensus = periods.some(p => facIds.some(fid => ROW_BY_KEY[fid + "|" + p]));
    const tr = document.createElement("tr"); tr.className = "manager-row";
    const labelTd = document.createElement("td"); labelTd.className = "linecell"; labelTd.textContent = mgr;
    if (!hasCensus){ const badge = document.createElement("span"); badge.className = "no-beds-badge"; badge.textContent = "no census data"; labelTd.appendChild(badge); }
    else if (!hasBeds){ const badge = document.createElement("span"); badge.className = "no-beds-badge"; badge.textContent = "no beds"; labelTd.appendChild(badge); }
    tr.appendChild(labelTd);
    periods.forEach(p => {
      const {pct} = occForFacilities(facIds, [p]);
      const td = document.createElement("td"); td.textContent = fmtPct(pct); td.classList.add("clickable");
      td.onclick = () => openOccDrill(mgr, p);
      tr.appendChild(td);
    });
    const {pct: avgPct} = occForFacilities(facIds, periods);
    const avgTd = document.createElement("td"); avgTd.textContent = fmtPct(avgPct); avgTd.classList.add("clickable");
    avgTd.onclick = () => openOccDrill(mgr, "TOTAL", periods);
    tr.appendChild(avgTd);
    body.appendChild(tr);
  });
}
function drillGroupLevel(facilities){
  const managers = new Set(facilities.map(f => f.manager));
  return managers.size > 1 ? "manager" : "facility";
}
function openOccDrill(managerName, period, totalPeriods){
  const facs = filteredFacilities().filter(f => f.manager === managerName);
  const level = drillGroupLevel(facs);
  const periods = period === "TOTAL" ? totalPeriods : [period];
  const groups = {};
  facs.forEach(f => {
    const key = level === "manager" ? f.manager : String(f.facility_id);
    if (!groups[key]) groups[key] = {label: level === "manager" ? f.manager : f.name, sub: level === "manager" ? "" : (f.manager + " · " + f.landlord), facIds: []};
    groups[key].facIds.push(f.facility_id);
  });
  const list = Object.values(groups).map(g => {
    const {days, bedDays, pct} = occForFacilities(g.facIds, periods);
    return {label: g.label, sub: g.sub, pct, days, bedDays};
  }).sort((a,b) => (b.pct||0) - (a.pct||0));
  const totalAgg = occForFacilities(facs.map(f=>f.facility_id), periods);

  document.getElementById("drillTitle").textContent = managerName;
  document.getElementById("drillSub").textContent = (period === "TOTAL" ? "Avg, " + fmtMonth(periods[0]) + " – " + fmtMonth(periods[periods.length-1]) : fmtMonth(period)) + " · by " + level;
  const bodyEl = document.getElementById("drillBody"); bodyEl.innerHTML = "";
  list.forEach(x => {
    const row = document.createElement("div"); row.className = "drill-row";
    const left = document.createElement("div");
    left.innerHTML = '<div class="name">' + x.label + '</div>' + (x.sub ? '<div class="meta">' + x.sub + '</div>' : '');
    const amt = document.createElement("div"); amt.className = "amt";
    amt.textContent = x.bedDays > 0 ? fmtPct(x.pct) + " (" + Math.round(x.days) + " days)" : "no beds";
    row.appendChild(left); row.appendChild(amt);
    bodyEl.appendChild(row);
  });
  const totalRow = document.createElement("div"); totalRow.className = "drill-row total";
  totalRow.innerHTML = '<div>Total</div>';
  const totalAmt = document.createElement("div"); totalAmt.className = "amt"; totalAmt.textContent = fmtPct(totalAgg.pct);
  totalRow.appendChild(totalAmt); bodyEl.appendChild(totalRow);
  document.getElementById("drillBackdrop").hidden = false;
}

// --- HFS comparison ------------------------------------------------------
function renderHfsTable(){
  const facs = filteredFacilities();
  const facIds = new Set(facs.map(f => f.facility_id));
  const compareRows = DATA.hfs_compare.filter(r => facIds.has(r.facility_id));
  const quarters = DATA.hfs_quarters;

  const head = document.getElementById("hfsHead"); const body = document.getElementById("hfsBody");
  head.innerHTML = ""; body.innerHTML = "";
  const lineTh = document.createElement("th"); lineTh.className = "linecol"; lineTh.textContent = "Facility"; head.appendChild(lineTh);
  quarters.forEach(q => { const th = document.createElement("th"); th.textContent = fmtMonth(q); head.appendChild(th); });

  const byFacility = {};
  compareRows.forEach(r => { (byFacility[r.facility_id] = byFacility[r.facility_id] || {})[r.quarter] = r; });

  const sortedFacs = facs.filter(f => byFacility[f.facility_id]).sort((a,b) => a.name.localeCompare(b.name));
  if (sortedFacs.length === 0){
    const tr = document.createElement("tr"); const td = document.createElement("td"); td.className="linecell"; td.textContent="No HFS-matched facilities in the current filter."; tr.appendChild(td); body.appendChild(tr);
  }
  const flagged = [];
  sortedFacs.forEach(f => {
    const tr = document.createElement("tr");
    const labelTd = document.createElement("td"); labelTd.className = "linecell"; labelTd.textContent = f.name; tr.appendChild(labelTd);
    quarters.forEach(q => {
      const td = document.createElement("td"); td.className = "hfs-cell";
      const r = byFacility[f.facility_id][q];
      if (!r || r.our_rate === null){ td.innerHTML = "–"; tr.appendChild(td); return; }
      const pct = (r.our_rate - r.hfs_rate) / r.hfs_rate * 100;
      const isFlagged = Math.abs(pct) > HFS_FLAG_PCT;
      if (isFlagged){ td.classList.add("hfs-flagged"); flagged.push({facility: f.name, quarter: q, our_rate: r.our_rate, hfs_rate: r.hfs_rate, pct}); }
      const cls = isFlagged ? "hfs-bad" : "hfs-good";
      const flag = isFlagged ? '⚠️ ' : '';
      td.innerHTML = '<div class="ours">$' + r.our_rate.toFixed(2) + '</div><div class="hfs ' + cls + '">' + flag + 'HFS $' + r.hfs_rate.toFixed(2) + ' (' + (pct>=0?'+':'') + pct.toFixed(1) + '%)</div>';
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });

  document.getElementById("hfsFlaggedCount").textContent = flagged.length;
  const flaggedCard = document.getElementById("flaggedCard");
  const flaggedList = document.getElementById("flaggedList");
  flaggedCard.hidden = flagged.length === 0;
  flaggedList.innerHTML = "";
  flagged.sort((a,b) => Math.abs(b.pct) - Math.abs(a.pct)).forEach(f => {
    const row = document.createElement("div"); row.className = "flag-row";
    row.innerHTML = '<div><div class="name">' + f.facility + '</div><div class="meta">' + fmtMonth(f.quarter) + ' · ours $' + f.our_rate.toFixed(2) + ' vs. HFS $' + f.hfs_rate.toFixed(2) + '</div></div><div class="variance">' + (f.pct>=0?'+':'') + f.pct.toFixed(1) + '%</div>';
    flaggedList.appendChild(row);
  });

  const withData = compareRows.filter(r => r.our_rate !== null);
  document.getElementById("hfsCompared").textContent = withData.length;
  if (withData.length > 0){
    const withinTol = withData.filter(r => Math.abs((r.our_rate - r.hfs_rate) / r.hfs_rate * 100) <= HFS_FLAG_PCT);
    document.getElementById("hfsWithinTol").textContent = withinTol.length + " / " + withData.length;
    document.getElementById("hfsWithinTolFoot").textContent = (100*withinTol.length/withData.length).toFixed(1) + "% of comparisons";
    const pcts = withData.map(r => (r.our_rate - r.hfs_rate) / r.hfs_rate * 100).sort((a,b)=>a-b);
    const n = pcts.length;
    const median = n % 2 ? pcts[(n-1)/2] : (pcts[n/2-1]+pcts[n/2])/2;
    document.getElementById("hfsMedian").textContent = (median>=0?'+':'') + median.toFixed(1) + "%";
  } else {
    document.getElementById("hfsWithinTol").textContent = "–";
    document.getElementById("hfsWithinTolFoot").textContent = "";
    document.getElementById("hfsMedian").textContent = "–";
  }
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
  const facIds = Array.from(matchingFacilityIds());
  const periods = periodsInRange();
  renderDonut(facIds, periods);
  renderStack(facIds, periods);
  renderOccCards();
  renderOccTable();
  renderHfsTable();
}

populateMonthPickers();
refreshAll();
</script>
"""

HTML = HTML.replace("__DATA_JSON__", data_json)
HTML = HTML.replace("__MANAGERS_JSON__", json.dumps(managers))
HTML = HTML.replace("__LANDLORDS_JSON__", json.dumps(landlords))

out_path = SCRATCH / "census.html"
out_path.write_text(HTML)
print("wrote", out_path, len(HTML), "bytes")
