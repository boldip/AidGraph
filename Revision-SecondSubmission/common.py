"""Shared helpers for the round-2 revision experiments.

All inputs are read from ../SecondSubmission (graph/arcs_weighted.tsv,
graph/nodes.tsv, h1_ranking.tsv, funder_scale.tsv). The exact-BFS harmonic
centrality and the degree-preserving swap chain are imported from
08_h1_harmonic.py so the null model is identical to the paper's.
"""
import importlib.util
import os
import sys
import multiprocessing as mp

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order, connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, "..", "SecondSubmission"))

_spec = importlib.util.spec_from_file_location(
    "h1mod", os.path.join(BASE, "08_h1_harmonic.py"))
h1mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h1mod)
sys.modules["h1mod"] = h1mod  # so Pool workers can unpickle swap_chain by reference
harmonic = h1mod.harmonic
swap_chain = h1mod.swap_chain

GLOBALGIVING = "US-EIN-300108263"


def load():
    arcs = pd.read_csv(f"{BASE}/graph/arcs_weighted.tsv", sep="\t")
    nodes = pd.read_csv(f"{BASE}/graph/nodes.tsv", sep="\t", header=None,
                        names=["id", "ref"], quoting=3)
    nodes["ref"] = nodes.ref.astype(str).str.strip('"').str.strip()
    h1 = pd.read_csv(f"{BASE}/h1_ranking.tsv", sep="\t")
    fs = pd.read_csv(f"{BASE}/funder_scale.tsv", sep="\t")
    return arcs, nodes, h1, fs


def node_id(nodes, ref):
    return int(nodes[nodes.ref == ref].id.iloc[0])


def display_names(nodes, h1):
    """ref -> name: registry title (h1_ranking.name), then ref_names.tsv."""
    names = h1.dropna(subset=["name"]).set_index("ref")["name"].to_dict()
    try:
        rn = pd.read_csv(f"{BASE}/ref_names.tsv", sep="\t")
        for r, n in zip(rn.ref, rn.name):
            names.setdefault(r, n)
    except FileNotFoundError:
        pass
    return names


def csr(arcs, n):
    return csr_matrix((np.ones(len(arcs), dtype=np.int8),
                       (arcs.s.to_numpy(), arcs.d.to_numpy())), shape=(n, n))


def distance_distribution(arcs, n):
    """Exact hop-count distribution over all reachable ordered pairs
    (BFS from every source). Returns a Series indexed by distance."""
    g = csr(arcs, n)
    srcs = np.unique(arcs.s.to_numpy())
    hist = np.zeros(64, dtype=np.int64)
    indptr, indices = g.indptr, g.indices
    dist = np.full(n, -1, dtype=np.int32)
    for s in srcs:
        dist[s] = 0
        frontier = [s]
        seen = [s]
        d = 0
        while frontier:
            d += 1
            nxt = []
            for u in frontier:
                for v in indices[indptr[u]:indptr[u + 1]]:
                    if dist[v] < 0:
                        dist[v] = d
                        nxt.append(v)
                        seen.append(v)
            hist[d] += len(nxt)
            frontier = nxt
        for v in seen:
            dist[v] = -1
    h = pd.Series(hist[1:], index=np.arange(1, 64))
    return h[h > 0]


def invariants(arcs, label=""):
    """Structural invariants of an arc table (node ids arbitrary ints)."""
    nodes = pd.Index(pd.concat([arcs.s, arcs.d]).unique())
    n = len(nodes)
    S = nodes.get_indexer(arcs.s); D = nodes.get_indexer(arcs.d)
    a = pd.DataFrame({"s": S, "d": D})
    g = csr(a, n)
    _, lab = connected_components(g, directed=False)
    wcc = np.bincount(lab).max()
    _, slab = connected_components(g, directed=True, connection="strong")
    scc_sizes = np.bincount(slab)
    scc = scc_sizes.max()
    cyc_arcs = (scc_sizes[slab[S]] > 1) & (slab[S] == slab[D])
    arcset = set(zip(S.tolist(), D.tolist()))
    recip = sum((d, s) in arcset for s, d in arcset) / len(arcset)
    indeg = np.bincount(D, minlength=n); outdeg = np.bincount(S, minlength=n)
    receivers = indeg > 0; funders = outdeg > 0
    dd = distance_distribution(a, n)
    reach = int(dd.sum()); pairs = n * (n - 1)
    cum = dd.cumsum() / reach
    out = {
        "network": label, "n": n, "m": len(a),
        "funders": int(funders.sum()), "receivers": int(receivers.sum()),
        "in_degree_1_share": float((indeg[receivers] == 1).mean()),
        "giant_wcc": int(wcc), "giant_wcc_share": wcc / n,
        "largest_scc": int(scc), "cyclic_arc_share": float(cyc_arcs.mean()),
        "reciprocity": recip,
        "reachable_pairs": reach, "reachable_pair_share": reach / pairs,
        "avg_distance": float((dd.index.to_numpy() * dd.to_numpy()).sum() / reach),
        "eff_diameter_90": int(cum.index[np.searchsorted(cum.to_numpy(), 0.9)]),
        "max_distance": int(dd.index.max()),
        "share_dist_le2": float(dd.loc[:2].sum() / reach),
        "share_dist_5to7": float(dd.loc[5:7].sum() / reach),
    }
    return out, dd


def null_z(arcs, n, n_samples, seed_base=1000):
    """Degree-preserving null (identical to 08_h1_harmonic.py): returns a
    DataFrame id, out_degree, h, h_null_mu, h_null_sigma, z for all funders."""
    src = arcs.s.to_numpy(np.int64); dst = arcs.d.to_numpy(np.int64)
    m = len(src); sources = np.unique(src)
    h_real = harmonic(src, dst, n, sources)
    workers = min(os.cpu_count(), 24)
    per = -(-n_samples // workers)
    jobs = [(seed_base + i, per, src, dst, n, sources, 10 * m, 2 * m)
            for i in range(workers)]
    with mp.get_context("fork").Pool(workers) as pool:
        chunks = pool.map(swap_chain, jobs)
    samples = np.concatenate(chunks)[:n_samples]
    mu = samples.mean(axis=0); sigma = samples.std(axis=0, ddof=1)
    f = pd.DataFrame({"id": sources,
                      "out_degree": np.bincount(src, minlength=n)[sources],
                      "h": h_real[sources], "h_null_mu": mu,
                      "h_null_sigma": sigma})
    f["z"] = np.where(f.h_null_sigma > 0, (f.h - f.h_null_mu) / f.h_null_sigma, np.nan)
    return f


def percolation(arcs, n, orders, kgrid, rng_wcc=100, rng_reach=20, seed=2026):
    """Funder-removal percolation (as 18_percolation.py). `orders` maps a
    strategy name to an array of node ids in removal order; the 'random'
    baseline draws from all funders."""
    S = arcs.s.to_numpy(); D = arcs.d.to_numpy()
    n0 = n; pairs0 = n0 * (n0 - 1)
    funders = np.unique(S)
    ones = np.ones(len(S), dtype=np.int8)

    def giant_share(mask):
        keep = ~(mask[S] | mask[D])
        g = csr_matrix((ones[keep], (S[keep], D[keep])), shape=(n0, n0))
        _, lab = connected_components(g, directed=False)
        return np.bincount(lab).max() / n0

    def reach_share(mask):
        keep = ~(mask[S] | mask[D])
        g = csr_matrix((ones[keep], (S[keep], D[keep])), shape=(n0, n0))
        srcs = np.flatnonzero(np.diff(g.indptr) > 0)
        total = 0
        for s in srcs:
            total += len(breadth_first_order(g, s, directed=True,
                                             return_predecessors=False)) - 1
        return total / pairs0

    rows = []
    rng = np.random.default_rng(seed)
    for k in kgrid:
        for name, order in orders.items():
            mask = np.zeros(n0, dtype=bool); mask[order[:k]] = True
            rows.append((k, name, giant_share(mask), reach_share(mask), np.nan))
        gs, rs = [], []
        for t in range(rng_wcc):
            mask = np.zeros(n0, dtype=bool)
            mask[rng.choice(funders, size=min(k, len(funders)), replace=False)] = True
            gs.append(giant_share(mask))
            if t < rng_reach:
                rs.append(reach_share(mask))
        rows.append((k, "random", np.mean(gs), np.mean(rs), np.std(gs)))
        print(f"  k={k:4d} " + " ".join(f"{r[1]}:{r[2]:.3f}/{r[3]:.4f}" for r in rows[-4:]), flush=True)
    return pd.DataFrame(rows, columns=["k", "strategy", "giant_wcc_share",
                                       "reachable_pair_share", "giant_sd"])


def plot_percolation(df, nf, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    COL = {"usd": "#2a78d6", "degree": "#eb6834", "harmonic": "#7a52c7"}
    LAB = {"usd": "top-$k$ by gross USD", "degree": "top-$k$ by out-degree",
           "harmonic": "top-$k$ by harmonic centrality"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, col, ttl in zip(axes, ["giant_wcc_share", "reachable_pair_share"],
                            ["Largest weakly connected component\n(share of original nodes)",
                             "Directed reachable ordered pairs\n(share of original pairs)"]):
        rnd = df[df.strategy == "random"].sort_values("k"); x = rnd.k.replace(0, 0.5)
        if col == "giant_wcc_share":
            ax.fill_between(x, np.clip(rnd[col] - 2 * rnd.giant_sd, 0, 1),
                            np.clip(rnd[col] + 2 * rnd.giant_sd, 0, 1), color="#999999", alpha=0.25, lw=0)
            ax.set_ylim(-0.02, 1.02)
        ax.plot(x, rnd[col], color="#666666", lw=1.8, label="random $k$ funders")
        for s in ["usd", "degree", "harmonic"]:
            d = df[df.strategy == s].sort_values("k")
            ax.plot(d.k.replace(0, 0.5), d[col], color=COL[s], lw=1.8, marker="o", ms=3.5, label=LAB[s])
        ax.set_xscale("log")
        ticks = [1, 3, 10, 30, 100, 300, nf]
        ax.set_xticks(ticks); ax.set_xticklabels([str(t) for t in ticks])
        ax.set_xlabel(f"funders removed, $k$ (of {nf})"); ax.set_title(ttl, fontsize=10); ax.grid(alpha=0.25)
    axes[0].set_ylabel("share"); axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle(title, fontsize=11); fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def h1_table(f, nodes, fs, names, min_deg=5, min_usd=1e6, top=50,
             refrows=("US-GOV-1", "GB-GOV-1", "XM-DAC-3-1", GLOBALGIVING)):
    """Filtered H1 ranking table (as 10_h1_report.py): gross USD from
    funder_scale, activity filter, top-k by z plus reference rows."""
    f = f.merge(nodes, on="id", how="left")
    f = f.merge(fs[["ref", "usd_total"]], on="ref", how="left")
    f["usd"] = f.usd_total
    f["name"] = f.ref.map(names).fillna(f.ref)
    g = f[(f.out_degree >= min_deg) & (f.usd.fillna(0) >= min_usd)].copy()
    g["rank_z"] = g.z.rank(ascending=False, method="first").astype(int)
    g["rank_usd"] = g.usd.rank(ascending=False, method="first").astype(int)
    g = g.sort_values("rank_z")
    cols = ["rank_z", "ref", "name", "out_degree", "usd", "h", "h_null_mu", "z", "rank_usd"]
    return g[cols], len(g)
