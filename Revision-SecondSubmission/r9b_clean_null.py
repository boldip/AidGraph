#!/usr/bin/env python3
"""Second stage of the clean rebuild (run in a lean process: vm.overcommit=2
forbids forking the 50 GB process that built the graph): H1 null model on
graph_clean/, comparison with the published ranking, and assembly of
clean_results.md from the pieces r9_clean_rebuild.py left on disk."""
import os, re, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr, kendalltau
import common as C
n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 960
arcs, nodes, h1, fs = C.load(); names = C.display_names(nodes, h1)
clean = pd.read_csv("graph_clean/arcs_weighted.tsv", sep="\t")
cnodes = pd.read_csv("graph_clean/nodes.tsv", sep="\t", header=None, names=["id", "ref"], quoting=3); cnodes["ref"] = cnodes.ref.astype(str).str.strip()
n = int(cnodes.id.max()) + 1
log = open("graph_clean/build_log.txt").read().strip().splitlines()
log += [l for l in open("r9.log").read().splitlines() if l.startswith(("audit sample", "remaining sample"))]
md = ["# IATI-K rebuilt without generic category codes and placeholder references", "", "Build log:", ""] + [f"- {m}" for m in log] + [""]
inv = pd.read_csv("clean_invariants.tsv", sep="\t"); dd = pd.read_csv("clean_distances.tsv", sep="\t")
md += ["## Invariants", "", inv.set_index("network").T.to_markdown(), "", "## Distance distribution (share of reachable pairs)", "", dd.to_markdown(index=False), ""]
perc = pd.read_csv("clean_percolation.tsv", sep="\t"); p = perc.set_index(["k", "strategy"])
src = clean.s.to_numpy(np.int64); dst = clean.d.to_numpy(np.int64); funders = np.unique(src)
md += ["## Funder removal (clean graph)", "", "| k | by USD | by out-degree | by harmonic | random |", "|---|---|---|---|---|"]
for k in [1, 3, 10, 50]:
    md.append(f"| {k} | " + " | ".join(f"{p.loc[(k,s),'giant_wcc_share']:.3f} / {p.loc[(k,s),'reachable_pair_share']/p.loc[(0,s),'reachable_pair_share']:.0%}" for s in ["usd","degree","harmonic","random"]) + " |")
md += ["", "Cells: giant-component share / share of reachable pairs still open.", ""]
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
open("clean_results.md", "w").write("\n".join(md)); print("\n".join(md[-45:])); print("done r9b")
