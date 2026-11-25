#!/usr/bin/env python3
"""Build audit_page/name_audit.html: one card per (name, ref) pair of
name_check_audit.tsv, with verdict buttons. Verdicts are stored in the
artifact's db (collection 'verdicts', doc p<idx>) when published as a
claude.ai artifact; otherwise in localStorage."""
import json, html, os, pandas as pd, numpy as np

os.makedirs("audit_page", exist_ok=True)
d = pd.read_csv("name_check_audit.tsv", sep="\t")
def s(v): return "" if (v is None or (isinstance(v, float) and np.isnan(v))) else str(v)
rows = []
for i, r in d.iterrows():
    rows.append({"i": int(i), "stratum": "top" if r.stratum.startswith("top") else "random", "rand": bool(r.in_random_sample),
        "name": s(r.raw_example), "norm": s(r["name"]), "ref": s(r.ref), "title": s(r.registry_title_of_ref), "crs": s(r.crs_channel_name),
        "source": s(r.source), "support": int(r.cooc_support_rows), "dom": None if np.isnan(r.cooc_dominance) else round(float(r.cooc_dominance), 3),
        "rows": int(r.rows), "reporters": int(r.reporters), "reporter": s(r.reporter_example), "reporterTitle": s(r.reporter_example_title),
        "selfloop": bool(r.ref_also_reporter_of_row), "others": s(r.other_names_seen_with_ref), "url": s(r.lookup_url).split("  (")[0],
        "hint": s(r.auto_hint), "sugg": s(r.suggested_verdict)})
DATA = json.dumps(rows, ensure_ascii=False)
page = r'''<title>Name Resolution Audit</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one column of index-card-like records, sticky progress header, filter chips. */
:root{
  --bg:#f6f4ef; --card:#fffdf8; --fg:#1f1d1a; --muted:#6b665d; --line:#dcd6c8; --accent:#2d5f8a;
  --ok:#2e7d4f; --ok-bg:#e3f2e8; --bad:#b4332e; --bad-bg:#f9e4e2; --uns:#a66a00; --uns-bg:#fbefd6; --chip:#ece8de;
  --sans:"IBM Plex Sans",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#15171a; --card:#1e2126; --fg:#ebe7df; --muted:#9a958a; --line:#343941; --accent:#7fb2dc;
  --ok:#6cc48f; --ok-bg:#1d3326; --bad:#f08a84; --bad-bg:#3b2220; --uns:#e2b25c; --uns-bg:#3a2e14; --chip:#2b2f36; color-scheme:dark } }
:root[data-theme="dark"]{
  --bg:#15171a; --card:#1e2126; --fg:#ebe7df; --muted:#9a958a; --line:#343941; --accent:#7fb2dc;
  --ok:#6cc48f; --ok-bg:#1d3326; --bad:#f08a84; --bad-bg:#3b2220; --uns:#e2b25c; --uns-bg:#3a2e14; --chip:#2b2f36; color-scheme:dark }
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:15px/1.45 var(--sans);margin:0;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0 48px}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
header{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding:14px 0 10px;border-bottom:1px solid var(--line);
  display:flex;flex-direction:column;gap:8px;max-width:860px;margin:0 auto}
h1{font-size:18px;font-weight:600;margin:0;text-wrap:balance}
.bar{height:8px;background:var(--chip);border-radius:4px;overflow:hidden;display:flex}
.bar span{display:block;height:100%}
.bar .ok{background:var(--ok)} .bar .bad{background:var(--bad)} .bar .uns{background:var(--uns)}
.status{display:flex;justify-content:space-between;gap:12px;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;flex-wrap:wrap}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{border:1px solid var(--line);background:var(--chip);color:var(--fg);border-radius:999px;padding:3px 10px;font-size:13px;cursor:pointer;font-family:inherit}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
main{max-width:860px;margin:0 auto;display:flex;flex-direction:column;gap:14px;padding-top:14px}
.card{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:6px;padding:14px 16px;display:grid;gap:10px;min-width:0}
.card:focus-within,.card.cur{outline:2px solid var(--accent);outline-offset:1px}
.card[data-v="correct"]{border-left-color:var(--ok)} .card[data-v="wrong"]{border-left-color:var(--bad)} .card[data-v="unsure"]{border-left-color:var(--uns)}
.top{display:flex;justify-content:space-between;gap:10px;align-items:baseline;flex-wrap:wrap}
.idx{font-family:var(--mono);font-size:12px;color:var(--muted)}
.tag{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);border:1px solid var(--line);border-radius:3px;padding:1px 6px}
.name{font-size:19px;font-weight:600;line-height:1.25;overflow-wrap:anywhere}
.arrow{color:var(--muted);font-weight:400;margin:0 8px}
.ref{font-family:var(--mono);font-size:16px;color:var(--accent);overflow-wrap:anywhere}
.ev{display:grid;grid-template-columns:150px 1fr;gap:4px 12px;font-size:14px}
.ev dt{color:var(--muted)} .ev dd{margin:0;min-width:0;overflow-wrap:anywhere}
.ev dd.mono{font-family:var(--mono);font-size:13px}
.hint{font-size:13px;color:var(--muted);border-top:1px dashed var(--line);padding-top:8px}
.hint b{color:var(--fg);font-weight:500}
.act{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.act button{font-family:inherit;font-size:14px;font-weight:500;border:1px solid var(--line);background:var(--chip);color:var(--fg);border-radius:6px;padding:7px 14px;cursor:pointer}
.act button.on.c{background:var(--ok-bg);border-color:var(--ok);color:var(--ok)}
.act button.on.w{background:var(--bad-bg);border-color:var(--bad);color:var(--bad)}
.act button.on.u{background:var(--uns-bg);border-color:var(--uns);color:var(--uns)}
.act button:focus-visible,.chip:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.note{flex:1 1 220px;min-width:0;font:14px var(--sans);padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
.sugg{font-size:12px;color:var(--muted)}
a{color:var(--accent)}
.banner{max-width:860px;margin:12px auto 0;padding:10px 14px;border-radius:6px;background:var(--uns-bg);color:var(--fg);font-size:14px}
.empty{color:var(--muted);text-align:center;padding:40px 0}
@media (max-width:560px){.ev{grid-template-columns:1fr}.ev dt{margin-top:6px}}
@media (prefers-reduced-motion:no-preference){.card{transition:border-color .15s}}
</style>
<header>
  <h1>Name resolution audit: 128 name-to-reference pairs</h1>
  <div class="bar" id="bar"></div>
  <div class="status"><span id="count">Loading saved verdicts</span><span>Keys: <kbd>j</kbd>/<kbd>k</kbd> or arrows move between cards</span></div>
  <div class="chips" id="filters" role="group" aria-label="Filter">
    <button class="chip" data-f="all" aria-pressed="true">All</button>
    <button class="chip" data-f="todo" aria-pressed="false">Not yet judged</button>
    <button class="chip" data-f="correct" aria-pressed="false">Correct</button>
    <button class="chip" data-f="wrong" aria-pressed="false">Wrong</button>
    <button class="chip" data-f="unsure" aria-pressed="false">Unsure</button>
    <button class="chip" data-f="top" aria-pressed="false">Top 30 by rows</button>
    <button class="chip" data-f="random" aria-pressed="false">Random 100</button>
  </div>
</header>
<div class="banner" id="banner" hidden></div>
<main id="main"></main>
<script>
const DATA = __DATA__;
const state = {}; // i -> {verdict, note}
let filter = "all", db = null, local = false, cur = -1;
const fmt = n => n.toLocaleString("en-GB");
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function card(r){
  const v = state[r.i]?.verdict || "", note = state[r.i]?.note || "";
  const others = r.others ? r.others.split("; ").map(esc).join("<br>") : '<span class="sugg">no other row gives both this reference and a name</span>';
  return `<article class="card" data-i="${r.i}" data-v="${v}" tabindex="0" id="card-${r.i}">
  <div class="top"><span class="idx">#${r.i+1}</span><span class="tag">${r.stratum==="top"?"top 30 by rows":"random 100"}${r.stratum==="top"&&r.rand?" + random":""}</span>
    <span class="idx">${fmt(r.rows)} rows from ${r.reporters} reporter${r.reporters>1?"s":""}</span></div>
  <div class="name">${esc(r.name)}<span class="arrow">&rarr;</span><span class="ref">${esc(r.ref)}</span></div>
  <dl class="ev">
    <dt>Registry title of ref</dt><dd>${r.title?esc(r.title):'<span class="sugg">not an IATI publisher</span>'}</dd>
    ${r.crs?`<dt>CRS channel name</dt><dd>${esc(r.crs)}</dd>`:""}
    <dt>Other names seen with ref</dt><dd>${others}</dd>
    <dt>Dictionary source</dt><dd>${esc(r.source)}${r.dom!==null?`, ${r.support} supporting rows, dominance ${r.dom}`:""}${r.selfloop?", target equals the reporter (self-loop, dropped later)":""}</dd>
    <dt>Example reporter</dt><dd class="mono">${esc(r.reporter)}${r.reporterTitle?` <span style="font-family:var(--sans)">(${esc(r.reporterTitle)})</span>`:""}</dd>
    <dt>Look up</dt><dd><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.url.replace(/^https?:\/\//,"").slice(0,70))}</a></dd>
  </dl>
  <div class="hint"><b>Hint</b> (${esc(r.sugg)}): ${esc(r.hint)}</div>
  <div class="act">
    <button class="c ${v==="correct"?"on":""}" data-set="correct">Correct</button>
    <button class="w ${v==="wrong"?"on":""}" data-set="wrong">Wrong</button>
    <button class="u ${v==="unsure"?"on":""}" data-set="unsure">Unsure</button>
    <input class="note" id="note-${r.i}" placeholder="note (e.g. should be XM-DAC-41103)" value="${esc(note)}">
  </div></article>`;
}
function visible(r){
  const v = state[r.i]?.verdict || "";
  if (filter==="all") return true; if (filter==="todo") return !v;
  if (filter==="top"||filter==="random") return r.stratum===filter || (filter==="random" && r.rand);
  return v===filter;
}
function render(){
  const main = document.getElementById("main");
  const list = DATA.filter(visible);
  main.innerHTML = list.length ? list.map(card).join("") : '<p class="empty">No card matches this filter.</p>';
  progress();
}
function progress(){
  const n = {correct:0, wrong:0, unsure:0}; let done = 0;
  for (const r of DATA){ const v = state[r.i]?.verdict; if (v){ n[v]++; done++; } }
  document.getElementById("bar").innerHTML = ["ok","bad","uns"].map((c,k)=>`<span class="${c}" style="width:${100*n[["correct","wrong","unsure"][k]]/DATA.length}%"></span>`).join("");
  document.getElementById("count").textContent = `${done} of ${DATA.length} judged: ${n.correct} correct, ${n.wrong} wrong, ${n.unsure} unsure` + (local ? " (saved only in this browser)" : "");
}
function patch(i){
  const el = document.getElementById("card-"+i); if (!el) return;
  const v = state[i]?.verdict || ""; el.dataset.v = v;
  el.querySelectorAll("[data-set]").forEach(b => b.classList.toggle("on", b.dataset.set===v));
  const inp = el.querySelector(".note"); if (inp && document.activeElement!==inp) inp.value = state[i]?.note || "";
  progress();
}
const timers = {};
async function save(i){
  const body = {verdict: state[i]?.verdict || "", note: state[i]?.note || "", updatedAt: new Date().toISOString()};
  if (db){
    try { await db.collection("verdicts").doc("p"+i).set(body); }
    catch (e) { showBanner("Could not save card #"+(i+1)+" ("+(e.code||"error")+"). Your other verdicts are kept; try again later."); }
  } else { try { localStorage.setItem("verdicts", JSON.stringify(state)); } catch (e) {} }
}
function setVerdict(i, v){
  state[i] = Object.assign({}, state[i], {verdict: v}); patch(i); save(i);
}
function showBanner(t){ const b = document.getElementById("banner"); b.textContent = t; b.hidden = false; }

document.getElementById("main").addEventListener("click", e => {
  const b = e.target.closest("[data-set]"); if (!b) return;
  const i = +b.closest(".card").dataset.i; setVerdict(i, b.dataset.set);
});
document.getElementById("main").addEventListener("input", e => {
  if (!e.target.classList.contains("note")) return;
  const i = +e.target.closest(".card").dataset.i;
  state[i] = Object.assign({}, state[i], {note: e.target.value});
  clearTimeout(timers[i]); timers[i] = setTimeout(() => save(i), 700);
});
document.getElementById("main").addEventListener("focusin", e => { const c = e.target.closest(".card"); if (c) setCur(+c.dataset.i, false); });
document.getElementById("filters").addEventListener("click", e => {
  const b = e.target.closest(".chip"); if (!b) return;
  filter = b.dataset.f; document.querySelectorAll("#filters .chip").forEach(x => x.setAttribute("aria-pressed", x===b));
  render();
});
function setCur(i, scroll){
  document.querySelectorAll(".card.cur").forEach(c => c.classList.remove("cur"));
  cur = i; const el = document.getElementById("card-"+i); if (!el) return; el.classList.add("cur");
  if (scroll){ el.focus({preventScroll:true}); el.scrollIntoView({block:"center", behavior:"smooth"}); }
}
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.target.tagName==="INPUT"){ if (e.key==="Escape") e.target.blur(); return; }
  const cards = [...document.querySelectorAll(".card")].map(c => +c.dataset.i); if (!cards.length) return;
  let k = cards.indexOf(cur);
  if (e.key==="j" || e.key==="ArrowDown"){ e.preventDefault(); setCur(cards[Math.min(k+1, cards.length-1)], true); }
  else if (e.key==="k" || e.key==="ArrowUp"){ e.preventDefault(); setCur(cards[Math.max(k-1, 0)], true); }
});

render();
(async () => {
  db = window.claude?.use ? await window.claude.use("db") : null;
  if (!db){
    local = true; showBanner("Not connected to the shared store: verdicts are saved only in this browser and will not reach Claude. Open the page from its claude.ai link while signed in.");
    try { Object.assign(state, JSON.parse(localStorage.getItem("verdicts") || "{}")); } catch (e) {}
    render(); return;
  }
  let timer = setTimeout(() => showBanner("Saved verdicts cannot be reached yet; verdicts you set now will be saved when the connection returns."), 10000);
  db.collection("verdicts").onSnapshot(snap => {
    for (const ch of snap.docChanges()){
      const i = +ch.doc.id.slice(1);
      if (ch.type==="removed") delete state[i]; else state[i] = ch.doc.data();
      patch(i);
    }
    if (!snap.metadata.fromCache){ clearTimeout(timer); document.getElementById("banner").hidden = true; }
    if (filter!=="all") render();
  }, err => { clearTimeout(timer); showBanner("The shared store returned an error ("+err.code+"); reload the page to reconnect."); });
})();
</script>
'''.replace("__DATA__", DATA)
open("audit_page/name_audit.html", "w").write(page)
print(len(page), "bytes;", len(rows), "cards")
