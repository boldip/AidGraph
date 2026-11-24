#!/usr/bin/env python3
r"""Rebuild the IATI-K graph treating generic CRS channel category codes and
placeholder strings as missing references (the defect found by the name
audit), then repeat the structural analyses on the clean graph.

Changes with respect to SecondSubmission/02_build_graph.py, and nothing else:
  * a receiver or provider ref matching ^(XM-DAC-)?\d{2}000$ (OECD CRS channel
    *category* codes: 10000 public sector, 21000 international NGO, 22000
    donor-country NGO, 61000 private sector in provider country, ...) or one of
    NOT AVAILABLE / NO IDENTIFIER / NOT REGISTERED / NOT APPLICABLE /
    UNSPECIFIED / OTHER is treated like the existing placeholders, unless an
    organisation publishes to IATI under that very string (44000 = The World
    Bank, XM-DAC-43000 = IMF), in which case it is that organisation's identifier;
  * receiver names that are category labels rather than organisations
    ('Correction', 'International NGO', 'NGO - International Other',
    'Enterprise - Non United States Redacted', ...) are added to the junk list,
    so they can neither enter the name dictionary nor be resolved by it.

Outputs (graph_clean/ and clean_*):
  graph_clean/{nodes.tsv,arcs_weighted.tsv,arclist.txt,build_log.txt}
  clean_invariants.tsv, clean_distances.tsv, fig_clean_distances.png
  clean_percolation.tsv, fig_clean_percolation.png
  clean_h1_ranking.tsv, clean_h1_top50.tsv, clean_audit_sample.tsv
  clean_results.md
Usage: python3 r9_clean_rebuild.py [n_null_samples=960]
"""
import importlib.util, json, os, re, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr, kendalltau
import common as C

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = C.BASE
spec = importlib.util.spec_from_file_location("b", f"{BASE}/02_build_graph.py"); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 960

GENERIC_REF = re.compile(r"^((XM-DAC-)?\d{2}000|NOT AVAILABLE|NO IDENTIFIER|NOT REGISTERED|NOT APPLICABLE|UNSPECIFIED|OTHER)$")
EXTRA_JUNK = re.compile(r"^correction$|^(international|local|national) ngo$|^(ngo|enterprise|government|individual|university|other|public sector|foundation|multilateral)\b.*\b(other|redacted)$"
                        r"|^(donor|developing|recipient) country.based ngo$|^private sector in\b|^ngos? based in\b", re.I)
# codes under which an organisation actually publishes to IATI (e.g. 44000 = The World Bank,
# XM-DAC-43000 = IMF) are that organisation's own identifier and are kept
PUBLISHER_IDS = {k.upper() for k in json.load(open(f"{BASE}/comparison_data/publisher_names.json"))}
GENERIC_KEPT = sorted(k for k in PUBLISHER_IDS if GENERIC_REF.match(k))
def is_placeholder(s): return s.isin(B.PLACEHOLDER) | (s.str.match(GENERIC_REF, na=False) & ~s.isin(PUBLISHER_IDS))
def is_junk(n): return n.str.contains(B.JUNK_NAME, na=False) | n.str.match(EXTRA_JUNK, na=False)

log = []
def say(m): print(m, flush=True); log.append(m)

# ---------------------------------------------------------------- A. build
os.chdir(BASE)
df = pd.read_parquet("Data")
say(f"total rows: {len(df):,}")
t3 = df[df.transaction_transaction_type_code == B.TYPE3].drop_duplicates()
sec = t3.reporting_org_ref.map(B.unwrap).str.upper().isin(B.SECONDARY_REPORTERS); t3 = t3[~sec]
say(f"disbursement rows after dedup and secondary-reporter removal: {len(t3):,}")
del df
prov = t3.transaction_provider_org_ref.map(B.unwrap); imputed = prov.isna()
prov = prov.fillna(t3.reporting_org_ref.map(B.unwrap)).str.upper()
recv = t3.transaction_receiver_org_ref.map(B.unwrap).str.upper()
gen_recv = recv.str.match(GENERIC_REF, na=False) & ~recv.isin(PUBLISHER_IDS); gen_prov = prov.str.match(GENERIC_REF, na=False) & ~prov.isin(PUBLISHER_IDS)
say(f"category-like codes kept because an organisation publishes under them: {GENERIC_KEPT}")
say(f"rows whose receiver ref is a generic category code or placeholder string: {gen_recv.sum():,} (provider: {gen_prov.sum():,}); "
    f"distinct such receiver refs: {recv[gen_recv].nunique()}")
prov = prov.where(~is_placeholder(prov)); recv = recv.where(~is_placeholder(recv))
tmap = B.typo_alias_map(prov, recv, t3.reporting_org_ref.map(B.unwrap).str.upper())
prov = prov.map(lambda r: tmap.get(r, r)); recv = recv.map(lambda r: tmap.get(r, r))
rname = t3.transaction_receiver_org_narrative.map(B.unwrap).map(B.norm_name)
junk_extra = rname.notna() & ~rname.str.contains(B.JUNK_NAME, na=False) & rname.str.match(EXTRA_JUNK, na=False)
say(f"receiver names newly blacklisted as category labels: {junk_extra.sum():,} rows, e.g. {rname[junk_extra].value_counts().head(8).to_dict()}")
rname = rname.where(rname.notna() & ~is_junk(rname))
os.chdir(BASE)  # publisher_names.json is read relatively
d = B.name_dictionary(recv, rname)
say(f"name->ref dictionary entries: {len(d):,} (published build: 13,875)")
fill = recv.isna() & rname.notna()
resolved = rname[fill].map(d)
say(f"ref-less receivers resolved by name dictionary: {resolved.notna().sum():,} rows (published build: 269,090)")
pairs = pd.DataFrame({"name": rname[fill][resolved.notna()], "ref": resolved.dropna()}).groupby(["name", "ref"]).size().reset_index(name="rows")
say(f"distinct (name, ref) pairs used: {len(pairs):,}; resolving onto generic codes: {pairs.ref.str.match(GENERIC_REF).sum()}")
recv = recv.where(recv.notna(), resolved)
cmap = B.canonical_map(pd.concat([prov, recv]).dropna().unique())
prov = prov.map(lambda r: cmap.get(r, r)); recv = recv.map(lambda r: cmap.get(r, r))
val = t3.transaction_value.map(B.unwrap).astype(float)
cur = t3.transaction_value_currency.map(B.unwrap).fillna(t3.default_currency.map(B.unwrap))
w = pd.DataFrame({"prov": prov, "recv": recv, "val": val, "cur": cur})
w = w[w.recv.notna() & w.prov.notna()]
say(f"rows with both endpoints: {len(w):,} (published: 1,330,963)")
loops = w.prov == w.recv; w = w[~loops].copy()
say(f"self-loop rows dropped: {loops.sum():,}; rows used for arcs: {len(w):,} (published: 1,051,065)")
w["usd"] = (w.val * w.cur.map(B.FX)).fillna(0.0)
say(f"total net disbursement value: {w.usd.sum()/1e9:,.2f} B USD (published: 1,030.38)")
orgs = pd.concat([w.prov, w.recv]).unique(); ids = {r: i for i, r in enumerate(sorted(orgs))}
w["s"] = w.prov.map(ids); w["d"] = w.recv.map(ids)
agg = w.groupby(["s", "d"]).agg(count=("val", "size"), usd=("usd", "sum")).reset_index().sort_values(["s", "d"])
say(f"n = {len(ids):,} nodes (published 22,773); m = {len(agg):,} arcs (published 28,708)")
os.chdir(HERE); os.makedirs("graph_clean", exist_ok=True)
agg[["s", "d"]].to_csv("graph_clean/arclist.txt", sep="\t", index=False, header=False)
agg.to_csv("graph_clean/arcs_weighted.tsv", sep="\t", index=False, float_format="%.2f")
with open("graph_clean/nodes.tsv", "w") as f:
    for r, i in sorted(ids.items(), key=lambda kv: kv[1]): f.write(f"{i}\t{r}\n")
open("graph_clean/build_log.txt", "w").write("\n".join(log) + "\n")

# audit sample under the new dictionary
aud = pd.read_csv("name_check_audit.tsv", sep="\t"); J = json.load(open("name_check_verdicts.json"))
aud["verdict"] = [J[f"p{i}"]["verdict"] for i in aud.index]
aud["still_resolved"] = [d.get(nm) == rf for nm, rf in zip(aud["name"], aud.ref)]
aud["new_target"] = aud["name"].map(d)
aud[["stratum", "raw_example", "name", "ref", "rows", "verdict", "still_resolved", "new_target"]].to_csv("clean_audit_sample.tsv", sep="\t", index=False)
gone = aud[~aud.still_resolved]
say(f"audit sample: {len(gone)} of {len(aud)} pairs no longer produced by the dictionary: "
    f"{(gone.verdict=='wrong').sum()} wrong, {(gone.verdict=='unsure').sum()} unsure, {(gone.verdict=='correct').sum()} correct "
    f"({gone[gone.verdict=='wrong'].rows.sum():,} of the {aud[aud.verdict=='wrong'].rows.sum():,} rows judged wrong)")
rem = aud[aud.still_resolved]
say(f"remaining sample: random {int((rem.in_random_sample if 'in_random_sample' in rem else rem.stratum.str.startswith('random')).sum())} pairs: "
    f"{((rem.stratum.str.startswith('random'))&(rem.verdict=='correct')).sum()} correct, {((rem.stratum.str.startswith('random'))&(rem.verdict=='wrong')).sum()} wrong, {((rem.stratum.str.startswith('random'))&(rem.verdict=='unsure')).sum()} unsure; "
    f"top-30: {((rem.stratum.str.startswith('top'))&(rem.verdict=='correct')).sum()} / {((rem.stratum.str.startswith('top'))&(rem.verdict=='wrong')).sum()} / {((rem.stratum.str.startswith('top'))&(rem.verdict=='unsure')).sum()}")
del t3, w, prov, recv, rname

# ---------------------------------------------------------------- B. analyses
arcs, nodes, h1, fs = C.load()
clean = agg.rename(columns={"s": "s", "d": "d"}).reset_index(drop=True)
cnodes = pd.DataFrame({"id": list(ids.values()), "ref": list(ids.keys())})
names = C.display_names(nodes, h1)
n_full = int(max(arcs.s.max(), arcs.d.max())) + 1; n = len(ids)
md = ["# IATI-K rebuilt without generic category codes and placeholder references", "", "Build log:", ""] + [f"- {m}" for m in log] + [""]
inv_full, dd_full = C.invariants(arcs, "IATI-K (published)")
inv_cl, dd_cl = C.invariants(clean, "IATI-K clean")
inv = pd.DataFrame([inv_full, inv_cl]); inv.to_csv("clean_invariants.tsv", sep="\t", index=False)
dd = pd.DataFrame({"distance": dd_full.index, "pairs_full": dd_full.values}).merge(pd.DataFrame({"distance": dd_cl.index, "pairs_clean": dd_cl.values}), how="outer").fillna(0)
dd["share_full"] = dd.pairs_full / dd.pairs_full.sum(); dd["share_clean"] = dd.pairs_clean / dd.pairs_clean.sum()
dd.to_csv("clean_distances.tsv", sep="\t", index=False)
md += ["## Invariants", "", inv.set_index("network").T.to_markdown(), "", "## Distance distribution (share of reachable pairs)", "", dd.to_markdown(index=False), ""]
print("\n".join(md[-40:]), flush=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(7.5, 4.2)); wd = 0.4
ax.bar(dd.distance - wd/2, dd.share_full, wd, color="#2a78d6", label=f"IATI-K as published ({inv_full['reachable_pairs']:,} reachable pairs)")
ax.bar(dd.distance + wd/2, dd.share_clean, wd, color="#5aa469", label=f"without generic-code nodes ({inv_cl['reachable_pairs']:,})")
ax.set_xlabel("shortest-path length (hops)"); ax.set_ylabel("share of reachable ordered pairs"); ax.set_xticks(dd.distance.astype(int))
ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=0.25); fig.tight_layout(); fig.savefig("fig_clean_distances.png", dpi=160); plt.close(fig)

# percolation
src = clean.s.to_numpy(np.int64); dst = clean.d.to_numpy(np.int64); funders = np.unique(src); nf = len(funders)
h_cl = C.harmonic(src, dst, n, funders)
ref_of = cnodes.set_index("id").ref; usd_total = fs.set_index("ref").usd_total
usd = pd.Series(funders).map(ref_of).map(usd_total).fillna(0).to_numpy(); outdeg = np.bincount(src, minlength=n)[funders]
orders = {"usd": funders[np.argsort(-usd)], "degree": funders[np.argsort(-outdeg)], "harmonic": funders[np.argsort(-h_cl[funders])]}
KGRID = [0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, nf]
print("percolation on clean graph", flush=True)
perc = C.percolation(clean, n, orders, KGRID); perc.to_csv("clean_percolation.tsv", sep="\t", index=False)
C.plot_percolation(perc, nf, "Funder-removal percolation on IATI-K without generic-code nodes", "fig_clean_percolation.png")
p = perc.set_index(["k", "strategy"])
md += ["## Funder removal (clean graph)", "", "| k | by USD | by out-degree | by harmonic | random |", "|---|---|---|---|---|"]
for k in [1, 3, 10, 50]:
    md.append(f"| {k} | " + " | ".join(f"{p.loc[(k,s),'giant_wcc_share']:.3f} / {p.loc[(k,s),'reachable_pair_share']/p.loc[(0,s),'reachable_pair_share']:.0%}" for s in ["usd","degree","harmonic","random"]) + " |")
md += ["", "Cells: giant-component share / share of reachable pairs still open.", ""]
for s in ["usd", "degree", "harmonic"]:
    md.append(f"- first removed by {s}: " + ", ".join(names.get(ref_of[i], ref_of[i]) for i in orders[s][:3]))
md.append("")

# H1 null
print(f"H1 null model on clean graph, {n_samples} samples", flush=True)
f = C.null_z(clean, n, n_samples).merge(cnodes, on="id", how="left"); f["name"] = f.ref.map(names)
f.sort_values("z", ascending=False).to_csv("clean_h1_ranking.tsv", sep="\t", index=False, float_format="%.4f")
tab, nfilt = C.h1_table(f.drop(columns=["ref", "name"]), cnodes, fs, names)
tab.head(50).to_csv("clean_h1_top50.tsv", sep="\t", index=False, float_format="%.2f")
old = h1.merge(fs[["ref", "usd_total"]], on="ref", how="left"); old = old[(old.out_degree >= 5) & (old.usd_total.fillna(0) >= 1e6)].copy()
old["rank_old"] = old.z.rank(ascending=False, method="first").astype(int)
cmp = tab.merge(old[["ref", "z", "rank_old"]], on="ref", suffixes=("", "_old"))
rho = spearmanr(cmp.z, cmp.z_old).correlation; tau = kendalltau(cmp.z, cmp.z_old).correlation
top_new = set(tab.head(50).ref); top_old = set(old.nsmallest(50, "rank_old").ref)
md += ["## H1 ranking on the clean graph", "",
       f"{nfilt} funders pass the activity filter (285 published). Over the {len(cmp)} common funders, Spearman rho(z_new, z_old) = {rho:.3f}, Kendall tau = {tau:.3f}; top-50 overlap {len(top_new & top_old)}/50.", "",
       "Top 20 (new rank, old rank):", ""]
for r in cmp.sort_values("rank_z").head(20).itertuples():
    md.append(f"- {r.rank_z} ({r.rank_old}) {r.name}: z {r.z:.2f} (was {r.z_old:.2f}), out-degree {int(r.out_degree)}, US${r.usd/1e6:,.1f}m")
cmp["dr"] = cmp.rank_old - cmp.rank_z
md += ["", "Largest rank changes (|new - old| >= 20):", ""]
for r in cmp[cmp.dr.abs() >= 20].sort_values("dr", ascending=False).itertuples():
    md.append(f"- {r.name}: {r.rank_old} -> {r.rank_z} (z {r.z_old:.2f} -> {r.z:.2f})")
for ref in ["US-GOV-1", "GB-GOV-1", "US-GOV-11", "SE-0", "XM-DAC-3-1", C.GLOBALGIVING]:
    r = cmp[cmp.ref == ref]
    if len(r): r = r.iloc[0]; md.append(f"- reference: {r['name']}: rank {r.rank_z} (was {r.rank_old}), z {r.z:.2f} (was {r.z_old:.2f})")
md.append("")
open("clean_results.md", "w").write("\n".join(md)); print("\n".join(md[-45:])); print("done r9")
