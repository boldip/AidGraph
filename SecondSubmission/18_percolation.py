#!/usr/bin/env python3
"""Funder-removal percolation on IATI-K.

Remove the top-k funders (nodes with out-degree > 0) ranked by
(a) gross USD scale (funder_scale.tsv, identified + unidentified),
(b) out-degree, (c) outgoing harmonic centrality, and compare with
removing k funders uniformly at random. Connectivity is tracked as
(1) the share of the original nodes in the largest weakly connected
component and (2) the share of the original ordered pairs (x, y)
joined by a directed path.

Outputs: percolation.tsv, fig_percolation.png
"""
import sys
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, breadth_first_order

RNG_TRIALS_WCC = 100
RNG_TRIALS_REACH = 20
KGRID = [0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500]  # + nf (all funders)

arcs = pd.read_csv("graph/arcs_weighted.tsv", sep="\t", dtype={"s": str, "d": str})
nodes = pd.Index(pd.concat([arcs.s, arcs.d]).unique())
n0 = len(nodes)
S = nodes.get_indexer(arcs.s.values)
D = nodes.get_indexer(arcs.d.values)
pairs0 = n0 * (n0 - 1)

out_deg = np.bincount(S, minlength=n0)
funders = np.flatnonzero(out_deg > 0)
nf = len(funders)
print(f"n = {n0:,}  m = {len(S):,}  funders = {nf}")
KGRID = [k for k in KGRID if k < nf] + [nf]

# arcs_weighted stores integer node ids; h1_ranking is keyed by the same ids
fs = pd.read_csv("funder_scale.tsv", sep="\t").set_index("ref")
h1 = pd.read_csv("h1_ranking.tsv", sep="\t").set_index("id")
fid = pd.Series(funders).map(lambda i: int(nodes[i]))
usd = fid.map(h1.ref).map(fs.usd_total).fillna(0.0).values
harm = fid.map(h1.h).fillna(0.0).values
assert harm.max() > 0 and usd.max() > 0, "ordering maps failed to resolve"

orders = {
    "usd": funders[np.argsort(-usd)],
    "degree": funders[np.argsort(-out_deg[funders])],
    "harmonic": funders[np.argsort(-harm)],
}
for name, o in orders.items():
    top = ", ".join(h1.ref.get(int(nodes[i]), str(nodes[i])) for i in o[:5])
    print(f"top-5 by {name}: {top}")

ones = np.ones(len(S), dtype=np.int8)


def giant_share(removed_mask):
    keep = ~(removed_mask[S] | removed_mask[D])
    g = csr_matrix((ones[keep], (S[keep], D[keep])), shape=(n0, n0))
    _, lab = connected_components(g, directed=False)
    sizes = np.bincount(lab)
    # removed nodes are isolated singletons; subtract them from their own
    # components is unnecessary since the giant is far larger than 1
    return sizes.max() / n0


def reach_share(removed_mask):
    keep = ~(removed_mask[S] | removed_mask[D])
    g = csr_matrix((ones[keep], (S[keep], D[keep])), shape=(n0, n0))
    srcs = np.flatnonzero(np.diff(g.indptr) > 0)
    total = 0
    for s in srcs:
        order = breadth_first_order(g, s, directed=True, return_predecessors=False)
        total += len(order) - 1
    return total / pairs0


rows = []
for k in KGRID:
    for name, order in orders.items():
        mask = np.zeros(n0, dtype=bool)
        mask[order[:k]] = True
        rows.append((k, name, giant_share(mask), reach_share(mask), np.nan))
    # random baseline
    gs, rs = [], []
    rng = np.random.default_rng(2026)
    for t in range(RNG_TRIALS_WCC):
        mask = np.zeros(n0, dtype=bool)
        mask[rng.choice(funders, size=k, replace=False)] = True
        gs.append(giant_share(mask))
        if t < RNG_TRIALS_REACH:
            rs.append(reach_share(mask))
    rows.append((k, "random", np.mean(gs), np.mean(rs), np.std(gs)))
    r = rows[-4:]
    print(f"k={k:4d}  giant: usd {r[0][2]:.3f} deg {r[1][2]:.3f} harm {r[2][2]:.3f} "
          f"rnd {r[3][2]:.3f}±{r[3][4]:.3f} | reach: usd {r[0][3]:.4f} deg {r[1][3]:.4f} "
          f"harm {r[2][3]:.4f} rnd {r[3][3]:.4f}", flush=True)

df = pd.DataFrame(rows, columns=["k", "strategy", "giant_wcc_share",
                                 "reachable_pair_share", "giant_sd"])
df.to_csv("percolation.tsv", sep="\t", index=False)

# ---- figure ----
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"usd": "#2a78d6", "degree": "#eb6834", "harmonic": "#7a52c7"}
LAB = {"usd": "top-$k$ by gross USD", "degree": "top-$k$ by out-degree",
       "harmonic": "top-$k$ by harmonic centrality"}
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, col, ttl in zip(
        axes, ["giant_wcc_share", "reachable_pair_share"],
        ["Largest weakly connected component\n(share of original nodes)",
         "Directed reachable ordered pairs\n(share of original pairs)"]):
    rnd = df[df.strategy == "random"].sort_values("k")
    x = rnd.k.replace(0, 0.5)
    if col == "giant_wcc_share":
        ax.fill_between(x, np.clip(rnd[col] - 2 * rnd.giant_sd, 0, 1),
                        np.clip(rnd[col] + 2 * rnd.giant_sd, 0, 1),
                        color="#999999", alpha=0.25, lw=0)
        ax.set_ylim(-0.02, 1.02)
    ax.plot(x, rnd[col], color="#666666", lw=1.8, label="random $k$ funders")
    for s in ["usd", "degree", "harmonic"]:
        d = df[df.strategy == s].sort_values("k")
        ax.plot(d.k.replace(0, 0.5), d[col], color=COL[s], lw=1.8,
                marker="o", ms=3.5, label=LAB[s])
    ax.set_xscale("log")
    ax.set_xticks([1, 3, 10, 30, 100, 300, nf])
    ax.set_xticklabels(["1", "3", "10", "30", "100", "300", str(nf)])
    ax.set_xlabel(f"funders removed, $k$ (of {nf})")
    ax.set_title(ttl, fontsize=10)
    ax.grid(alpha=0.25)
axes[0].set_ylabel("share")
axes[0].legend(fontsize=8, frameon=False)
fig.suptitle("Funder-removal percolation on IATI-K", fontsize=11)
fig.tight_layout()
fig.savefig("fig_percolation.png", dpi=160)
print("wrote percolation.tsv, fig_percolation.png")
