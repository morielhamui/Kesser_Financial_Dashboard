import json, pathlib

SCRATCH = pathlib.Path(__file__).resolve().parent
data = json.loads((SCRATCH / "cms_data.json").read_text())

data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

HTML = r"""<title>CMS Quality &amp; Compliance</title>
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
.wrap{max-width:1320px; margin-inline:auto; display:flex; flex-direction:column; gap:22px;}
.masthead{display:flex; flex-direction:column; gap:4px;}
.eyebrow{font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--accent); font-weight:600;}
h1{font-size:clamp(24px,3.4vw,32px); font-weight:600; color:var(--ink);}
.sub{color:var(--muted); font-size:14px; max-width:78ch; line-height:1.5;}

.stat-row{display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px;}
.stat-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:14px 16px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:4px;}
.stat-label{font-size:11px; letter-spacing:.04em; text-transform:uppercase; color:var(--muted); font-weight:600;}
.stat-value{font-family:"IBM Plex Mono",monospace; font-size:22px; font-weight:600; color:var(--ink);}
.stat-value.warn{color:var(--warn);} .stat-value.bad{color:var(--bad);}
.stat-foot{font-size:11px; color:var(--muted);}

.picker-bar{display:flex; flex-direction:column; gap:10px; background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:14px 18px; box-shadow:var(--shadow);}
.picker-row{display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.chip{
  font-family:inherit; font-size:12.5px; font-weight:500; color:var(--ink-soft);
  background:var(--surface-2); border:1px solid var(--border); border-radius:999px;
  padding:5px 12px; cursor:pointer;
}
.chip:hover{border-color:var(--border-strong);}
.chip.active{background:var(--accent); border-color:var(--accent); color:var(--surface);}
.search-input{
  font-family:inherit; font-size:13px; color:var(--ink);
  background:var(--surface-2); border:1px solid var(--border); border-radius:8px;
  padding:7px 12px; min-width:200px; margin-left:auto;
}
.sort-select{
  font-family:inherit; font-size:12.5px; color:var(--ink);
  background:var(--surface-2); border:1px solid var(--border); border-radius:8px;
  padding:6px 10px;
}
.filter-hint{font-size:11.5px; color:var(--muted); margin:0;}

.table-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); overflow:hidden;}
.table-scroll{overflow-x:auto;}
table{border-collapse:collapse; width:100%; font-size:13px;}
thead th{
  position:sticky; top:0; background:var(--surface-2); color:var(--muted);
  font-weight:600; font-size:10.5px; letter-spacing:.04em; text-transform:uppercase;
  text-align:center; padding:10px 12px; border-bottom:1px solid var(--border); white-space:nowrap;
  font-family:"IBM Plex Mono",monospace;
}
thead th.namecol{text-align:left; font-family:"IBM Plex Sans",sans-serif;}
tbody td{padding:9px 12px; text-align:center; border-bottom:1px solid var(--border); font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--ink-soft);}
tbody td.namecell{text-align:left; font-family:"IBM Plex Sans",sans-serif; color:var(--ink);}
.fac-name{font-weight:600;}
.fac-meta{font-size:11px; color:var(--muted); font-family:"IBM Plex Sans",sans-serif;}
tbody tr{cursor:pointer;}
tbody tr:hover td{background:var(--surface-2);}
tbody tr.uncert td{color:var(--muted); font-style:italic;}

.stars{color:var(--border-strong); letter-spacing:1px;}
.stars.r5{color:var(--good);} .stars.r4{color:var(--good);} .stars.r3{color:var(--warn);} .stars.r2{color:var(--bad);} .stars.r1{color:var(--bad);}
.badge{display:inline-block; font-size:10.5px; font-weight:600; font-family:"IBM Plex Sans",sans-serif; padding:2px 8px; border-radius:999px;}
.badge.bad{background:var(--bad-soft); color:var(--bad);}
.badge.warn{background:var(--warn-soft); color:var(--warn);}
.badge.muted{background:var(--surface-2); color:var(--muted);}
.count-pill{display:inline-block; min-width:20px; padding:1px 6px; border-radius:999px; background:var(--surface-2); font-weight:600;}
.count-pill.hasopen{background:var(--bad-soft); color:var(--bad);}

.tagline{display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-size:12.5px; color:var(--muted); background:var(--surface-2); border:1px solid var(--border); border-radius:10px; padding:8px 14px;}
.tagline strong{color:var(--ink);}
.review-pill{font-family:inherit; font-size:12px; font-weight:600; color:var(--surface); background:var(--warn); border:none; border-radius:999px; padding:4px 12px; cursor:pointer; margin-left:auto;}
.review-pill:hover{filter:brightness(1.08);}

.stat-card.clickable{cursor:pointer;}
.stat-card.clickable:hover{border-color:var(--border-strong); box-shadow:var(--shadow), 0 0 0 1px var(--accent);}

.footnote{font-size:11.5px; color:var(--muted); line-height:1.5; padding:2px 4px;}

.filter-chips{display:flex; flex-wrap:wrap; gap:5px;}
.chip-sm{
  font-family:inherit; font-size:11px; font-weight:500; color:var(--ink-soft);
  background:var(--surface-2); border:1px solid var(--border); border-radius:999px;
  padding:3px 9px; cursor:pointer;
}
.chip-sm.active{background:var(--accent); border-color:var(--accent); color:var(--surface);}
.drill-toolbar{display:flex; flex-direction:column; gap:8px; padding:10px 18px 12px; border-bottom:1px solid var(--border); background:var(--surface-2);}
.drill-toolbar-row{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
.toolbar-label{font-size:10.5px; letter-spacing:.04em; text-transform:uppercase; color:var(--muted); font-weight:600; white-space:nowrap;}
.drill-sort-select{font-family:inherit; font-size:11.5px; color:var(--ink); background:var(--surface); border:1px solid var(--border); border-radius:6px; padding:4px 8px; margin-left:auto;}

.cite-correction{color:var(--muted); font-size:11.5px;}
.badge.new{background:var(--accent-soft); color:var(--accent);}
.badge.changed{background:var(--warn-soft); color:var(--warn);}
.cite-row.flagged{background:var(--accent-soft);}
.change-detail{font-size:11px; color:var(--ink-soft); background:var(--surface); border-radius:6px; padding:4px 8px; margin-top:2px;}

.list-row{display:flex; justify-content:space-between; align-items:center; gap:10px; padding:9px 18px; font-size:13px; border-bottom:1px solid var(--border);}
.list-row:last-child{border-bottom:none;}
.list-row .name{color:var(--ink); font-weight:500;}
.list-row .meta{color:var(--muted); font-size:11.5px;}

.drill-backdrop{position:fixed; inset:0; background:rgba(20,28,26,.45); display:flex; align-items:center; justify-content:center; padding:20px; z-index:50;}
.drill-backdrop[hidden]{display:none!important;}
.drill-card{background:var(--surface); border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); max-width:640px; width:100%; max-height:82vh; display:flex; flex-direction:column; overflow:hidden;}
.drill-head{display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:16px 18px 12px; border-bottom:1px solid var(--border);}
.drill-title{font-family:"Fraunces",serif; font-size:16px; font-weight:600; color:var(--ink);}
.drill-sub{font-size:12px; color:var(--muted); margin-top:2px;}
.drill-close{background:none; border:none; font-size:18px; line-height:1; color:var(--muted); cursor:pointer; padding:2px 4px;}
.drill-close:hover{color:var(--ink);}
.drill-body{overflow-y:auto; padding:6px 0;}
.cite-row{display:flex; flex-direction:column; gap:3px; padding:10px 18px; font-size:12.5px; border-bottom:1px solid var(--border);}
.cite-row:last-child{border-bottom:none;}
.cite-head{display:flex; justify-content:space-between; gap:10px; align-items:baseline;}
.cite-tag{font-family:"IBM Plex Mono",monospace; font-weight:600; color:var(--ink);}
.cite-date{color:var(--muted); font-size:11.5px; white-space:nowrap;}
.cite-desc{color:var(--ink-soft); line-height:1.4;}
.cite-flags{display:flex; gap:6px; flex-wrap:wrap;}
.cite-empty{font-size:12.5px; color:var(--muted); padding:16px 18px;}
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="wrap">
  <div class="masthead">
    <span class="eyebrow">Kesser Financial Dashboard</span>
    <h1>CMS Quality &amp; Compliance</h1>
    <p class="sub">Star ratings, staffing, and deficiency citations for every CMS-certified Petersen SNF facility, from CMS's own monthly Care Compare data (Provider Info + Health Citations). Click any facility to see its full citation history. ALF/independent-living units aren't Medicare/Medicaid-certified and show no CMS data, by design.</p>
  </div>

  <div class="tagline" id="tagline">&nbsp;</div>

  <div class="stat-row" id="statRow"></div>

  <div class="picker-bar">
    <div class="picker-row">
      <span id="brandChips"></span>
      <select class="sort-select" id="sortSelect">
        <option value="name">Sort: Facility name</option>
        <option value="overall_asc">Sort: Overall rating (low first)</option>
        <option value="citations_desc">Sort: Citations (most first)</option>
        <option value="fines_desc">Sort: Total fines $ (most first)</option>
      </select>
      <input class="search-input" id="searchInput" type="text" placeholder="Search facility...">
    </div>
  </div>

  <div class="table-card">
    <div class="table-scroll">
      <table id="cmsTable">
        <thead>
          <tr>
            <th class="namecol">Facility</th>
            <th>Overall</th>
            <th>Health Insp.</th>
            <th>Staffing</th>
            <th>QM</th>
            <th>SFF / Abuse</th>
            <th>Citations</th>
            <th>Fines</th>
            <th>Last Survey</th>
          </tr>
        </thead>
        <tbody id="bodyRows"></tbody>
      </table>
    </div>
  </div>
  <p class="footnote">Star ratings run 1&ndash;5 (5 = best). "SFF" = Special Focus Facility / Candidate status; "Abuse" flags CMS's Abuse Icon &mdash; click either stat tile above to see which facilities. Citations count is each facility's full on-file deficiency history; "not corrected" counts the two CMS statuses that mean work isn't done yet ("has plan of correction" and "has no plan of correction") &mdash; the other four (has date of correction, past non-compliance, waiver granted, no revisit needed) are CMS's own ways of saying the matter is closed. "New/changed" means this citation is new or its status changed since the last CMS file was loaded &mdash; click "Needs review" above for the full list across the portfolio. Fines totals are CMS's own all-time reported figures. Click a row to see the full citation list, with filters for every corrected-status and scope/severity option CMS reports.</p>
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
const FACILITIES = DATA.facilities;
const BRANDS = Array.from(new Set(FACILITIES.map(f => f.manager))).sort();
const CORRECTED_OPTIONS = DATA.corrected_options;
const SCOPE_SEVERITY_OPTIONS = DATA.scope_severity_options;
// CMS's own status text for a citation that is NOT yet actually
// corrected (has a plan, or no plan at all) vs. one that is resolved
// one way or another (corrected, past non-compliance, waiver, no
// revisit needed) -- used only for the portfolio-level "needs review"
// framing, never to hide any status from the filter (the filter always
// offers every option CMS gives, unfiltered).
const NOT_YET_CORRECTED = new Set(["Deficient, Provider has plan of correction", "Deficient, Provider has no plan of correction"]);

let selBrand = "";
let sortMode = "name";
let searchTerm = "";

// per-citation-modal filter/sort state, reset each time a facility is opened
let citeSort = "date_desc";
let citeStatusFilter = new Set(CORRECTED_OPTIONS);
let citeScopeFilter = new Set(SCOPE_SEVERITY_OPTIONS);
let openFacilityId = null;

function stars(n){
  if (n === null || n === undefined) return '<span class="stars">&ndash;</span>';
  const cls = "r" + n;
  return '<span class="stars ' + cls + '">' + "★".repeat(n) + "☆".repeat(5-n) + "</span>";
}
function fmtMoney(v){
  if (!v) return "$0";
  return "$" + Math.round(v).toLocaleString();
}
function fmtDate(d){
  if (!d) return "–";
  return d;
}
function notYetCorrectedCount(citations){
  return citations.filter(c => NOT_YET_CORRECTED.has(c.deficiency_corrected)).length;
}
function flagCount(f){
  return f.citations.reduce((s,c) => s + (c.changes && c.changes.length ? 1 : 0), 0);
}

function buildStats(){
  const certified = FACILITIES.filter(f => f.info);
  const avgOverall = certified.length
    ? (certified.reduce((s,f) => s + (f.info.overall_rating||0), 0) / certified.length).toFixed(1)
    : "–";
  const sffFacilities = certified.filter(f => f.info.special_focus_status);
  const abuseFacilities = certified.filter(f => f.info.abuse_icon === "Y");
  const totalFines = certified.reduce((s,f) => s + (f.info.total_fines_dollars||0), 0);
  const stats = [
    {label:"Facilities tracked", value: certified.length + " / " + FACILITIES.length, foot:"CMS-certified / total"},
    {label:"Avg. overall rating", value: avgOverall + "★", foot:"across certified facilities", cls: avgOverall!=="–" && avgOverall < 3 ? "bad" : ""},
    {label:"SFF / Candidate", value: String(sffFacilities.length), foot:"click to see which", cls: sffFacilities.length>0 ? "warn":"",
      onclick: () => openFacilityList("Special Focus Facilities", "SFF or SFF Candidate status", sffFacilities.map(f => ({name:f.name, meta:f.manager+" · "+f.info.special_focus_status})))},
    {label:"Abuse icon flagged", value: String(abuseFacilities.length), foot:"click to see which", cls: abuseFacilities.length>0?"bad":"",
      onclick: () => openFacilityList("Abuse Icon Flagged", "CMS Abuse Icon = Y", abuseFacilities.map(f => ({name:f.name, meta:f.manager})))},
    {label:"Needs review", value: String(DATA.total_unreviewed), foot:"new or changed since last upload", cls: DATA.total_unreviewed>0?"warn":"",
      onclick: () => openReviewQueue()},
    {label:"Total fines (all-time)", value: fmtMoney(totalFines), foot:"CMS-reported, cumulative", cls: totalFines>0?"bad":""},
  ];
  document.getElementById("statRow").innerHTML = stats.map((s,i) =>
    '<div class="stat-card'+(s.onclick?" clickable":"")+'" data-stat="'+i+'"><span class="stat-label">'+s.label+'</span><span class="stat-value '+(s.cls||"")+'">'+s.value+'</span><span class="stat-foot">'+s.foot+'</span></div>'
  ).join("");
  Array.from(document.getElementById("statRow").children).forEach((el,i) => {
    if (stats[i].onclick) el.onclick = stats[i].onclick;
  });

  const tagline = document.getElementById("tagline");
  tagline.innerHTML = '<span>Data as of <strong>' + (DATA.latest_processing_date || "unknown") + '</strong> (CMS\'s processing date on the latest file loaded) · citation history on file back to <strong>' +
    (certified.reduce((min,f) => {
      const d = f.citations.length ? f.citations[f.citations.length-1].survey_date : null;
      return d && (!min || d < min) ? d : min;
    }, null) || "–") + '</strong></span>' +
    (DATA.total_unreviewed ? '<button class="review-pill" id="taglineReviewBtn" type="button">' + DATA.total_unreviewed + ' to review &rarr;</button>' : '');
  if (DATA.total_unreviewed) document.getElementById("taglineReviewBtn").onclick = openReviewQueue;
}

function buildBrandChips(){
  const el = document.getElementById("brandChips");
  const all = document.createElement("button");
  all.className = "chip" + (selBrand === "" ? " active" : "");
  all.textContent = "All brands"; all.type = "button";
  all.onclick = () => { selBrand = ""; render(); };
  el.innerHTML = ""; el.appendChild(all);
  BRANDS.forEach(b => {
    const btn = document.createElement("button");
    btn.className = "chip" + (selBrand === b ? " active" : "");
    btn.textContent = b; btn.type = "button";
    btn.onclick = () => { selBrand = b; render(); };
    el.appendChild(btn);
  });
}

function sortFacilities(list){
  const copy = list.slice();
  if (sortMode === "overall_asc") {
    copy.sort((a,b) => (a.info?a.info.overall_rating:99) - (b.info?b.info.overall_rating:99) || a.name.localeCompare(b.name));
  } else if (sortMode === "citations_desc") {
    copy.sort((a,b) => b.citations.length - a.citations.length || a.name.localeCompare(b.name));
  } else if (sortMode === "fines_desc") {
    copy.sort((a,b) => (b.info?b.info.total_fines_dollars||0:0) - (a.info?a.info.total_fines_dollars||0:0) || a.name.localeCompare(b.name));
  } else {
    copy.sort((a,b) => a.name.localeCompare(b.name));
  }
  return copy;
}

function render(){
  buildBrandChips();
  buildStats();
  let list = FACILITIES.filter(f => !selBrand || f.manager === selBrand);
  if (searchTerm) list = list.filter(f => f.name.toLowerCase().includes(searchTerm.toLowerCase()));
  list = sortFacilities(list);

  const body = document.getElementById("bodyRows");
  body.innerHTML = list.map(f => {
    if (!f.info){
      return '<tr class="uncert" data-fid="'+f.facility_id+'"><td class="namecell"><span class="fac-name">'+f.name+'</span><br><span class="fac-meta">'+f.manager+' &middot; not CMS-certified</span></td>'+
        '<td colspan="7">No CMS data (ALF / independent living / no Medicare-Medicaid certification)</td></tr>';
    }
    const info = f.info;
    const notYetCt = notYetCorrectedCount(f.citations);
    const totalCt = f.citations.length;
    const flagCt = flagCount(f);
    const sffBadge = info.special_focus_status ? '<span class="badge warn">'+info.special_focus_status+'</span>' : '';
    const abuseBadge = info.abuse_icon === "Y" ? '<span class="badge bad">Abuse</span>' : '';
    const flags = (sffBadge + " " + abuseBadge).trim() || '<span class="badge muted">None</span>';
    const lastSurvey = f.citations.length ? f.citations[0].survey_date : "–";
    return '<tr data-fid="'+f.facility_id+'">'+
      '<td class="namecell"><span class="fac-name">'+f.name+'</span><br><span class="fac-meta">'+f.manager+' &middot; CCN '+f.ccn+'</span></td>'+
      '<td>'+stars(info.overall_rating)+'</td>'+
      '<td>'+stars(info.health_inspection_rating)+'</td>'+
      '<td>'+stars(info.staffing_rating)+'</td>'+
      '<td>'+stars(info.qm_rating)+'</td>'+
      '<td>'+flags+'</td>'+
      '<td><span class="count-pill'+(notYetCt>0?" hasopen":"")+'">'+totalCt+'</span>'+(notYetCt>0?' <span class="fac-meta" style="color:var(--bad)">'+notYetCt+' not corrected</span>':'')+(flagCt?' <span class="badge new">'+flagCt+' new/changed</span>':'')+'</td>'+
      '<td>'+fmtMoney(info.total_fines_dollars)+(info.number_of_fines?' <span class="fac-meta">('+info.number_of_fines+')</span>':'')+'</td>'+
      '<td>'+fmtDate(lastSurvey)+'</td>'+
      '</tr>';
  }).join("");

  Array.from(body.querySelectorAll("tr[data-fid]")).forEach(tr => {
    tr.onclick = () => openCitations(parseInt(tr.dataset.fid, 10));
  });
}

// --- generic facility-list drill (SFF / Abuse tiles) ---
function openFacilityList(title, subtitle, items){
  document.getElementById("drillTitle").textContent = title;
  document.getElementById("drillSub").textContent = subtitle + " · " + items.length + (items.length===1?" facility":" facilities");
  const body = document.getElementById("drillBody");
  body.innerHTML = items.length
    ? items.map(it => '<div class="list-row"><span class="name">'+it.name+'</span><span class="meta">'+it.meta+'</span></div>').join("")
    : '<div class="cite-empty">None.</div>';
  document.getElementById("drillBackdrop").hidden = false;
}

// --- review queue drill (new citations + status changes since last upload) ---
function openReviewQueue(){
  const rows = [];
  FACILITIES.forEach(f => f.citations.forEach(c => {
    (c.changes||[]).forEach(ch => {
      rows.push({facility: f.name, manager: f.manager, tag: (c.deficiency_prefix||"")+(c.deficiency_tag_number||""), survey_date: c.survey_date, ch});
    });
  }));
  rows.sort((a,b) => (b.ch.detected_at||"").localeCompare(a.ch.detected_at||""));
  document.getElementById("drillTitle").textContent = "Needs Review";
  document.getElementById("drillSub").textContent = rows.length + " new or changed citation" + (rows.length===1?"":"s") + " since the last upload";
  const body = document.getElementById("drillBody");
  body.innerHTML = rows.length
    ? rows.map(r => {
        const desc = r.ch.change_type === "new"
          ? '<span class="badge new">New</span> citation first seen in ' + r.ch.source_file
          : '<span class="badge changed">Changed</span> ' + r.ch.field_name + ': "' + (r.ch.old_value||"–") + '" &rarr; "' + (r.ch.new_value||"–") + '"';
        return '<div class="cite-row"><div class="cite-head"><span class="cite-tag">'+r.facility+' &middot; '+r.tag+'</span><span class="cite-date">'+r.survey_date+'</span></div><div class="cite-desc">'+desc+'</div></div>';
      }).join("")
    : '<div class="cite-empty">Nothing flagged — every citation matches last load.</div>';
  document.getElementById("drillBackdrop").hidden = false;
}

// --- per-facility citation drill, with sort + the exact filter options CMS gives ---
function openCitations(facilityId){
  openFacilityId = facilityId;
  citeSort = "date_desc";
  citeStatusFilter = new Set(CORRECTED_OPTIONS);
  citeScopeFilter = new Set(SCOPE_SEVERITY_OPTIONS);
  renderCitationModal();
}

function renderCitationModal(){
  const f = FACILITIES.find(x => x.facility_id === openFacilityId);
  if (!f) return;
  document.getElementById("drillTitle").textContent = f.name;
  document.getElementById("drillSub").textContent = (f.ccn ? "CCN " + f.ccn + " · " : "") + f.citations.length + " citations on file";
  const body = document.getElementById("drillBody");

  const statusChips = CORRECTED_OPTIONS.map(opt =>
    '<button class="chip-sm' + (citeStatusFilter.has(opt)?" active":"") + '" data-status="' + opt.replace(/"/g,"&quot;") + '" type="button">' + opt + '</button>'
  ).join("");
  const scopeChips = SCOPE_SEVERITY_OPTIONS.map(opt =>
    '<button class="chip-sm' + (citeScopeFilter.has(opt)?" active":"") + '" data-scope="' + opt + '" type="button">' + opt + '</button>'
  ).join("");

  let filtered = f.citations.filter(c => citeStatusFilter.has(c.deficiency_corrected) && citeScopeFilter.has(c.scope_severity_code));
  filtered = filtered.slice().sort((a,b) => {
    if (citeSort === "scope_desc") return (b.scope_severity_code||"").localeCompare(a.scope_severity_code||"") || b.survey_date.localeCompare(a.survey_date);
    if (citeSort === "scope_asc") return (a.scope_severity_code||"").localeCompare(b.scope_severity_code||"") || b.survey_date.localeCompare(a.survey_date);
    if (citeSort === "date_asc") return a.survey_date.localeCompare(b.survey_date);
    return b.survey_date.localeCompare(a.survey_date);
  });

  const listHtml = filtered.length
    ? filtered.map(c => {
        const flags = [];
        if (c.standard_deficiency === "Y") flags.push('<span class="badge muted">Standard</span>');
        if (c.complaint_deficiency === "Y") flags.push('<span class="badge warn">Complaint</span>');
        if (c.infection_control_deficiency === "Y") flags.push('<span class="badge bad">Infection Control</span>');
        const changes = c.changes || [];
        const isNew = changes.some(ch => ch.change_type === "new");
        if (isNew) flags.push('<span class="badge new">New</span>');
        else if (changes.length) flags.push('<span class="badge changed">Changed</span>');
        const changeDetail = (!isNew && changes.length)
          ? '<div class="change-detail">' + changes.map(ch => ch.field_name + ': "'+(ch.old_value||"–")+'" &rarr; "'+(ch.new_value||"–")+'"').join("<br>") + '</div>'
          : "";
        return '<div class="cite-row' + (changes.length?" flagged":"") + '">'+
          '<div class="cite-head"><span class="cite-tag">'+(c.deficiency_prefix||"")+(c.deficiency_tag_number||"")+' &middot; Scope/Severity '+(c.scope_severity_code||"–")+'</span><span class="cite-date">'+c.survey_date+'</span></div>'+
          '<div class="cite-desc">'+(c.deficiency_description||"")+'</div>'+
          '<div class="cite-correction">'+(c.deficiency_corrected||"–")+(c.correction_date?' · corrected '+c.correction_date:'')+'</div>'+
          '<div class="cite-flags">'+flags.join(" ")+'</div>'+
          changeDetail+
          '</div>';
      }).join("")
    : '<div class="cite-empty">No citations match the current filters.</div>';

  body.innerHTML =
    '<div class="drill-toolbar">'+
      '<div class="drill-toolbar-row"><span class="toolbar-label">Corrected status</span>'+
        '<select class="drill-sort-select" id="citeSortSelect">'+
          '<option value="date_desc"'+(citeSort==="date_desc"?" selected":"")+'>Sort: Survey date (newest)</option>'+
          '<option value="date_asc"'+(citeSort==="date_asc"?" selected":"")+'>Sort: Survey date (oldest)</option>'+
          '<option value="scope_desc"'+(citeSort==="scope_desc"?" selected":"")+'>Sort: Scope/Severity (highest)</option>'+
          '<option value="scope_asc"'+(citeSort==="scope_asc"?" selected":"")+'>Sort: Scope/Severity (lowest)</option>'+
        '</select></div>'+
      '<div class="filter-chips">'+statusChips+'</div>'+
      '<div class="drill-toolbar-row"><span class="toolbar-label">Scope/Severity</span></div>'+
      '<div class="filter-chips">'+scopeChips+'</div>'+
    '</div>'+
    '<div class="gl-flat" style="padding-top:0;">'+listHtml+'</div>';

  document.getElementById("citeSortSelect").onchange = e => { citeSort = e.target.value; renderCitationModal(); };
  Array.from(body.querySelectorAll("[data-status]")).forEach(btn => {
    btn.onclick = () => {
      const v = btn.dataset.status;
      if (citeStatusFilter.has(v)) citeStatusFilter.delete(v); else citeStatusFilter.add(v);
      renderCitationModal();
    };
  });
  Array.from(body.querySelectorAll("[data-scope]")).forEach(btn => {
    btn.onclick = () => {
      const v = btn.dataset.scope;
      if (citeScopeFilter.has(v)) citeScopeFilter.delete(v); else citeScopeFilter.add(v);
      renderCitationModal();
    };
  });

  document.getElementById("drillBackdrop").hidden = false;
}

function closeDrill(){ document.getElementById("drillBackdrop").hidden = true; openFacilityId = null; }
document.getElementById("drillClose").onclick = closeDrill;
document.getElementById("drillBackdrop").addEventListener("click", e => { if (e.target.id === "drillBackdrop") closeDrill(); });

document.getElementById("sortSelect").onchange = e => { sortMode = e.target.value; render(); };
document.getElementById("searchInput").oninput = e => { searchTerm = e.target.value; render(); };

render();
</script>
"""

HTML = HTML.replace("__DATA_JSON__", data_json)
(SCRATCH / "cms.html").write_text(HTML)
print("Wrote", SCRATCH / "cms.html")
