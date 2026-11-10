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

.footnote{font-size:11.5px; color:var(--muted); line-height:1.5; padding:2px 4px;}

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

  <div class="stat-row" id="statRow"></div>

  <div class="picker-bar">
    <div class="picker-row">
      <span id="brandChips"></span>
      <select class="sort-select" id="sortSelect">
        <option value="name">Sort: Facility name</option>
        <option value="overall_asc">Sort: Overall rating (low first)</option>
        <option value="citations_desc">Sort: Open citations (most first)</option>
        <option value="fines_desc">Sort: Total fines $ (most first)</option>
      </select>
      <input class="search-input" id="searchInput" type="text" placeholder="Search facility...">
    </div>
    <p class="filter-hint" id="snapshotNote">&nbsp;</p>
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
            <th>Citations<br><span style="font-weight:400;">(open)</span></th>
            <th>Fines</th>
            <th>Last Survey</th>
          </tr>
        </thead>
        <tbody id="bodyRows"></tbody>
      </table>
    </div>
  </div>
  <p class="footnote">Star ratings run 1&ndash;5 (5 = best). "SFF" = Special Focus Facility / Candidate status; "Abuse" flags CMS's Abuse Icon. Citations count is each facility's full on-file deficiency history; "(open)" counts citations without a recorded correction date. Fines totals are CMS's own all-time reported figures. Click a row to see the full citation list.</p>
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

let selBrand = "";
let sortMode = "name";
let searchTerm = "";

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
function openCitationsCount(citations){
  return citations.filter(c => !c.correction_date).length;
}

function buildStats(){
  const certified = FACILITIES.filter(f => f.info);
  const avgOverall = certified.length
    ? (certified.reduce((s,f) => s + (f.info.overall_rating||0), 0) / certified.length).toFixed(1)
    : "–";
  const sffCount = certified.filter(f => f.info.special_focus_status).length;
  const abuseCount = certified.filter(f => f.info.abuse_icon === "Y").length;
  const totalFines = certified.reduce((s,f) => s + (f.info.total_fines_dollars||0), 0);
  const openCitations = certified.reduce((s,f) => s + openCitationsCount(f.citations), 0);
  const stats = [
    {label:"Facilities tracked", value: certified.length + " / " + FACILITIES.length, foot:"CMS-certified / total", cls:""},
    {label:"Avg. overall rating", value: avgOverall + "★", foot:"across certified facilities", cls: avgOverall!=="–" && avgOverall < 3 ? "bad" : ""},
    {label:"SFF / Candidate", value: String(sffCount), foot:"Special Focus status", cls: sffCount>0 ? "warn":""},
    {label:"Abuse icon flagged", value: String(abuseCount), foot:"CMS Abuse Icon = Y", cls: abuseCount>0?"bad":""},
    {label:"Open citations", value: String(openCitations), foot:"no recorded correction date", cls: openCitations>0?"warn":""},
    {label:"Total fines (all-time)", value: fmtMoney(totalFines), foot:"CMS-reported, cumulative", cls: totalFines>0?"bad":""},
  ];
  document.getElementById("statRow").innerHTML = stats.map(s =>
    '<div class="stat-card"><span class="stat-label">'+s.label+'</span><span class="stat-value '+s.cls+'">'+s.value+'</span><span class="stat-foot">'+s.foot+'</span></div>'
  ).join("");

  const dates = certified.map(f => f.info.processing_date).filter(Boolean).sort();
  document.getElementById("snapshotNote").textContent = dates.length
    ? "CMS snapshot as of " + dates[dates.length-1] + " · citation history on file back to " +
      (certified.reduce((min,f) => {
        const d = f.citations.length ? f.citations[f.citations.length-1].survey_date : null;
        return d && (!min || d < min) ? d : min;
      }, null) || "–")
    : "No CMS snapshot loaded.";
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
    copy.sort((a,b) => openCitationsCount(b.citations) - openCitationsCount(a.citations) || a.name.localeCompare(b.name));
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
    const openCt = openCitationsCount(f.citations);
    const totalCt = f.citations.length;
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
      '<td><span class="count-pill'+(openCt>0?" hasopen":"")+'">'+totalCt+'</span>'+(openCt>0?' <span class="fac-meta" style="color:var(--bad)">'+openCt+' open</span>':'')+'</td>'+
      '<td>'+fmtMoney(info.total_fines_dollars)+(info.number_of_fines?' <span class="fac-meta">('+info.number_of_fines+')</span>':'')+'</td>'+
      '<td>'+fmtDate(lastSurvey)+'</td>'+
      '</tr>';
  }).join("");

  Array.from(body.querySelectorAll("tr[data-fid]")).forEach(tr => {
    tr.onclick = () => openCitations(parseInt(tr.dataset.fid, 10));
  });
}

function openCitations(facilityId){
  const f = FACILITIES.find(x => x.facility_id === facilityId);
  if (!f) return;
  document.getElementById("drillTitle").textContent = f.name;
  document.getElementById("drillSub").textContent = (f.ccn ? "CCN " + f.ccn + " · " : "") + f.citations.length + " citations on file";
  const body = document.getElementById("drillBody");
  if (!f.citations.length){
    body.innerHTML = '<div class="cite-empty">No citations on file for this facility.</div>';
  } else {
    body.innerHTML = f.citations.map(c => {
      const flags = [];
      if (c.standard_deficiency === "Y") flags.push('<span class="badge muted">Standard</span>');
      if (c.complaint_deficiency === "Y") flags.push('<span class="badge warn">Complaint</span>');
      if (c.infection_control_deficiency === "Y") flags.push('<span class="badge bad">Infection Control</span>');
      if (!c.correction_date) flags.push('<span class="badge bad">Open</span>');
      return '<div class="cite-row">'+
        '<div class="cite-head"><span class="cite-tag">'+(c.deficiency_prefix||"")+(c.deficiency_tag_number||"")+' &middot; Scope/Severity '+(c.scope_severity_code||"–")+'</span><span class="cite-date">'+c.survey_date+'</span></div>'+
        '<div class="cite-desc">'+(c.deficiency_description||"")+'</div>'+
        '<div class="cite-flags">'+flags.join(" ")+'</div>'+
        '</div>';
    }).join("");
  }
  document.getElementById("drillBackdrop").hidden = false;
}
function closeDrill(){ document.getElementById("drillBackdrop").hidden = true; }
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
