#!/usr/bin/env python3
"""Generic analyzer: same invariants + exact distance distribution as the aid
graph, for any directed weighted edge list. Used to fill the H3 comparison
table with networks from the literature.

Input : TSV with header "s\td\tw" (integer node ids 0..n-1, w = arc weight;
        pass the aid graph's arcs_weighted.tsv to cross-validate: its
        'count' or 'usd' column is selected with --weight-col).
Output: one markdown/JSON row of invariants, printed to stdout.

Distances are computed by exact BFS from every source (pure Python; all
comparison graphs here are small). Cross-validated against the WebGraph
exact NeighbourhoodFunction on the aid graph.

Usage: python3 05_compare.py comparison/airline.tsv --name "airline"
"""
import argparse
import json
import sys
import warnings
from collections import deque

import numpy as np
import pandas as pd


def wpearson(x, y, w):
    x, y, w = np.asarray(x, float), np.asarray(y, float), np.asarray(w, float)
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    return cov / np.sqrt(np.average((x - mx) ** 2, weights=w)
                         * np.average((y - my) ** 2, weights=w))


def distance_distribution(n, succ):
    """Exact BFS from every node; returns dict distance -> #ordered pairs."""
    counts = {}
    dist = np.empty(n, dtype=np.int32)
    for src in range(n):
        if src not in succ:
            continue
        dist.fill(-1)
        dist[src] = 0
        q = deque([src])
        while q:
            u = q.popleft()
            du = int(dist[u]) + 1
            for v in succ.get(u, ()):
                if dist[v] < 0:
                    dist[v] = du
                    counts[du] = counts.get(du, 0) + 1
                    q.append(v)
    return counts


def plfit(data):
    import powerlaw
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = powerlaw.Fit(data, discrete=True, verbose=False)
        R, p = fit.distribution_compare("power_law", "lognormal",
                                        normalized_ratio=True)
    return {"alpha": round(fit.power_law.alpha, 2),
            "xmin": int(fit.power_law.xmin), "R": round(R, 2), "p": round(p, 3)}


def analyze(arcs, name):
    n = int(max(arcs.s.max(), arcs.d.max())) + 1
    m = len(arcs)
    w = arcs.w.to_numpy(float)
    total_pairs = n * (n - 1)

    outdeg = arcs.groupby("s").size()
    indeg = arcs.groupby("d").size()
    out_str = arcs.groupby("s").w.sum()
    in_str = arcs.groupby("d").w.sum()

    key = set(zip(arcs.s, arcs.d))
    recip = sum((d, s) in key for s, d in key) / m
    rev = arcs.set_index(["d", "s"]).w
    idx = pd.MultiIndex.from_arrays([arcs.s, arcs.d])
    rev_w = rev.reindex(idx).fillna(0).to_numpy()
    wpos = np.maximum(w, 0)
    recip_w = np.minimum(wpos, np.maximum(rev_w, 0)).sum() / wpos.sum()

    assort = np.corrcoef(outdeg.reindex(arcs.s), indeg.reindex(arcs.d))[0, 1]
    pos = w > 0
    assort_w = wpearson(out_str.reindex(arcs.s[pos]),
                        in_str.reindex(arcs.d[pos]), w[pos])

    succ = {s: g.d.to_numpy() for s, g in arcs.groupby("s")}
    dd = distance_distribution(n, succ)
    reachable = sum(dd.values())
    avg_dist = sum(t * c for t, c in dd.items()) / reachable
    cum, eff_diam = 0, max(dd)
    for t in sorted(dd):
        cum += dd[t]
        if cum >= 0.9 * reachable:
            eff_diam = t
            break
    frac12 = (dd.get(1, 0) + dd.get(2, 0)) / reachable
    assert dd[1] == m

    return {
        "name": name, "n": n, "m": m,
        "density": m / total_pairs, "avg_deg": m / n,
        "reciprocity": round(recip, 4), "reciprocity_w": round(recip_w, 4),
        "assortativity": round(float(assort), 3),
        "assortativity_w": round(float(assort_w), 3),
        "avg_dist": round(avg_dist, 3), "eff_diam": eff_diam,
        "max_dist": max(dd), "reachable_frac": reachable / total_pairs,
        "frac_le2": round(frac12, 3),
        "distance_distribution": {int(t): int(c) for t, c in sorted(dd.items())},
        "plfit_in": plfit(indeg.to_numpy()),
        "plfit_out": plfit(outdeg.to_numpy()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edges")
    ap.add_argument("--name", default=None)
    ap.add_argument("--weight-col", default="w")
    args = ap.parse_args()
    arcs = pd.read_csv(args.edges, sep="\t")
    arcs = arcs.rename(columns={args.weight_col: "w"})[["s", "d", "w"]]
    res = analyze(arcs, args.name or args.edges)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
