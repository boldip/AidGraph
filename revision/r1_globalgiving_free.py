#!/usr/bin/env python3
"""Reviewer 2, point 1: repeat the structural analysis without GlobalGiving.

Outputs (all prefixed ggfree_):
  ggfree_invariants.tsv        full vs GlobalGiving-free invariants
  ggfree_distances.tsv         exact hop-count distribution, both graphs
  fig_ggfree_distances.png     Fig. 1 counterpart
  ggfree_percolation.tsv       funder-removal curves on the GG-free graph
  fig_ggfree_percolation.png   Fig. 2 counterpart
  ggfree_h1_ranking.tsv        H1 null-model z on the GG-free graph (all funders)
  ggfree_h1_top50.tsv          filtered top-50 + reference rows
  ggfree_results.md            summary with the numbers for the response letter
Usage: python3 r1_globalgiving_free.py [n_null_samples=960]
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau
import common as C

n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 960
arcs, nodes, h1, fs = C.load()
n = int(max(arcs.s.max(), arcs.d.max())) + 1
gg = C.node_id(nodes, C.GLOBALGIVING)
names = C.display_names(nodes, h1)
md = []

ggfree = arcs[(arcs.s != gg) & (arcs.d != gg)].reset_index(drop=True)
gg_out = int((arcs.s == gg).sum()); gg_in = int((arcs.d == gg).sum())
gg_only = int(gg_out - len(set(arcs[arcs.s == gg].d) & set(ggfree.d)))
inv_full, dd_full = C.invariants(arcs, "IATI-K")
inv_gg, dd_gg = C.invariants(ggfree, "IATI-K without GlobalGiving")
inv = pd.DataFrame([inv_full, inv_gg]); inv.to_csv("ggfree_invariants.tsv", sep="\t", index=False)
dd = pd.DataFrame({"distance": dd_full.index, "pairs_full": dd_full.values}).merge(
    pd.DataFrame({"distance": dd_gg.index, "pairs_ggfree": dd_gg.values}), how="outer").fillna(0)
dd["share_full"] = dd.pairs_full / dd.pairs_full.sum(); dd["share_ggfree"] = dd.pairs_ggfree / dd.pairs_ggfree.sum()
dd.to_csv("ggfree_distances.tsv", sep="\t", index=False)
lost = dd_full.sum() - dd_gg.sum()
d2_lost = dd_full.get(2, 0) - dd_gg.get(2, 0)
md += ["# IATI-K without GlobalGiving", "",
       f"GlobalGiving ({C.GLOBALGIVING}): out-degree {gg_out:,} = {gg_out/inv_full['n']:.1%} of the {inv_full['n']:,} organisations; "
       f"in-degree {gg_in}; {gg_only:,} of its recipients ({gg_only/gg_out:.1%}) have no other identified funder.", "",
       f"Reachable ordered pairs: {inv_full['reachable_pairs']:,} -> {inv_gg['reachable_pairs']:,} "
       f"({lost:,} = {lost/inv_full['reachable_pairs']:.1%} of reachable pairs involve GlobalGiving as source, target or intermediary).",
       f"Distance-2 pairs: {dd_full.get(2,0):,} -> {dd_gg.get(2,0):,} ({d2_lost/dd_full.get(2,0):.1%} of the distance-2 peak is GlobalGiving).", "",
       "## Invariants", "", inv.set_index("network").T.to_markdown(), ""]
print("\n".join(md), flush=True)

# --- Fig. 1 counterpart ---
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(7.5, 4.2))
w = 0.4
ax.bar(dd.distance - w/2, dd.share_full, w, color="#2a78d6", label=f"IATI-K ({inv_full['reachable_pairs']:,} reachable pairs)")
ax.bar(dd.distance + w/2, dd.share_ggfree, w, color="#eb6834", label=f"without GlobalGiving ({inv_gg['reachable_pairs']:,})")
ax.set_xlabel("shortest-path length (hops)"); ax.set_ylabel("share of reachable ordered pairs")
ax.set_xticks(dd.distance.astype(int)); ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=0.25)
ax.set_title("Distance distribution with and without GlobalGiving", fontsize=11)
fig.tight_layout(); fig.savefig("fig_ggfree_distances.png", dpi=160); plt.close(fig)

# --- Fig. 2 counterpart: percolation on the GG-free graph ---
src = ggfree.s.to_numpy(np.int64); dst = ggfree.d.to_numpy(np.int64)
funders = np.unique(src); nf = len(funders)
h_gg = C.harmonic(src, dst, n, funders)
ref_of = nodes.set_index("id").ref
usd_total = fs.set_index("ref").usd_total
usd = pd.Series(funders).map(ref_of).map(usd_total).fillna(0).to_numpy()
outdeg = np.bincount(src, minlength=n)[funders]
orders = {"usd": funders[np.argsort(-usd)], "degree": funders[np.argsort(-outdeg)],
          "harmonic": funders[np.argsort(-h_gg[funders])]}
for k_, o in orders.items():
    print("top-5 by", k_, [ref_of[i] for i in o[:5]])
KGRID = [0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, nf]
print("percolation on GG-free graph", flush=True)
perc = C.percolation(ggfree, n, orders, KGRID)
# shares relative to the GG-free graph's own node/pair counts
n_gg = inv_gg["n"]; perc["giant_wcc_share"] *= n / n_gg
perc["reachable_pair_share"] *= (n * (n - 1)) / (n_gg * (n_gg - 1))
perc["giant_sd"] *= n / n_gg
perc.to_csv("ggfree_percolation.tsv", sep="\t", index=False)
C.plot_percolation(perc, nf, "Funder-removal percolation on IATI-K without GlobalGiving", "fig_ggfree_percolation.png")
p = perc.set_index(["k", "strategy"])
md += [f"## Funder removal (GG-free graph, shares relative to its own {n_gg:,} nodes)", "",
       "| k | by USD | by out-degree | by harmonic | random |", "|---|---|---|---|---|"]
for k in [1, 3, 10, 50]:
    md.append(f"| {k} | " + " | ".join(f"{p.loc[(k,s),'giant_wcc_share']:.3f} / {p.loc[(k,s),'reachable_pair_share']/p.loc[(0,s),'reachable_pair_share']:.0%}" for s in ["usd","degree","harmonic","random"]) + " |")
md += ["", "Cells: giant-component share / share of the graph's own reachable pairs still open.", ""]
for s in ["usd", "degree", "harmonic"]:
    md.append(f"- first removed by {s}: {names.get(ref_of[orders[s][0]], ref_of[orders[s][0]])}, then {names.get(ref_of[orders[s][1]], ref_of[orders[s][1]])}, {names.get(ref_of[orders[s][2]], ref_of[orders[s][2]])}")
md.append("")

# --- H1 null on the GG-free graph ---
print(f"H1 null model on GG-free graph, {n_samples} samples", flush=True)
f = C.null_z(ggfree, n, n_samples)
f = f.merge(nodes, on="id", how="left")
f["name"] = f.ref.map(names)
f.sort_values("z", ascending=False).to_csv("ggfree_h1_ranking.tsv", sep="\t", index=False, float_format="%.4f")
tab, nfilt = C.h1_table(f.drop(columns=["ref", "name"]), nodes, fs, names)
tab.head(50).to_csv("ggfree_h1_top50.tsv", sep="\t", index=False, float_format="%.2f")
# compare with the published ranking
old = h1.merge(fs[["ref", "usd_total"]], on="ref", how="left")
old = old[(old.out_degree >= 5) & (old.usd_total.fillna(0) >= 1e6)].copy()
old["rank_old"] = old.z.rank(ascending=False, method="first").astype(int)
cmp = tab.merge(old[["ref", "z", "rank_old"]], on="ref", suffixes=("", "_old"))
rho = spearmanr(cmp.z, cmp.z_old).correlation; tau = kendalltau(cmp.z, cmp.z_old).correlation
top_new = set(tab.head(50).ref); top_old = set(old.nsmallest(50, "rank_old").ref)
md += ["## H1 ranking on the GG-free graph", "",
       f"{nfilt} funders pass the activity filter ({len(old)} before; GlobalGiving itself is gone). Over the {len(cmp)} common funders, "
       f"Spearman rho(z_new, z_old) = {rho:.3f}, Kendall tau = {tau:.3f}; top-50 overlap {len(top_new & top_old)}/50.", "",
       "Top 20 (new rank, old rank):", ""]
for r in cmp.sort_values("rank_z").head(20).itertuples():
    md.append(f"- {r.rank_z} ({r.rank_old}) {r.name}: z {r.z:.2f} (was {r.z_old:.2f}), out-degree {int(r.out_degree)}, US${r.usd/1e6:,.1f}m")
for ref in ["US-GOV-1", "GB-GOV-1", "XM-DAC-3-1"]:
    r = cmp[cmp.ref == ref]
    if len(r):
        r = r.iloc[0]; md.append(f"- reference: {r["name"]}: rank {r.rank_z} (was {r.rank_old}), z {r.z:.2f} (was {r.z_old:.2f})")
md.append("")
open("ggfree_results.md", "w").write("\n".join(md))
print("\n".join(md[-30:])); print("done r1")
