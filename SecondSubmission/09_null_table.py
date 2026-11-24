#!/usr/bin/env python3
"""H3 robustness: express each network's invariants as z-scores against its own
degree-preserving null (directed double-edge swaps, in/out-degrees preserved,
simple graph maintained). Scale-free by construction, so networks of very
different size/density can share a table honestly.

Unweighted invariants only (reciprocity, out-in assortativity, avg distance
among reachable pairs, reachable-pair count): under an arc swap the weight
assignment to the rewired arcs is ambiguous, so weighted z-scores are not
well defined without extra conventions.

Independent chains (one sample per chain, burn-in 10m accepted swaps),
parallelised. Output: null_table.tsv and a printed table.

Usage: python3 09_null_table.py [n_samples=96]
"""
import os
import sys
from collections import deque
from multiprocessing import Pool

import numpy as np
import pandas as pd

NETWORKS = {
    "iati-k": ("graph/arcs_weighted.tsv", None),
    "iati-cty": ("comparison/aid_country.tsv", None),
    "ibank": ("comparison/interbank.tsv", None),
    "trade": ("comparison/trade.tsv", None),
    "air": ("comparison/airline.tsv", None),
    "refugee": ("comparison/refugee.tsv", None),
    "remit": ("comparison/remit.tsv", None),
}


def load(path):
    a = pd.read_csv(path, sep="\t")
    # copy=True: pandas >= 3 returns read-only views and one_sample swaps in place
    return a.s.to_numpy(np.int64, copy=True), a.d.to_numpy(np.int64, copy=True)


def metrics(src, dst, n):
    m = len(src)
    arcset = set(map(tuple, np.stack([src, dst], axis=1)))
    recip = sum((d, s) in arcset for s, d in arcset) / m
    outdeg = np.bincount(src, minlength=n)
    indeg = np.bincount(dst, minlength=n)
    assort = np.corrcoef(outdeg[src], indeg[dst])[0, 1]
    # distances
    order = np.argsort(src, kind="stable")
    d_sorted = dst[order]
    indptr = np.searchsorted(src[order], np.arange(n + 1))
    dist = np.full(n, -1, dtype=np.int32)
    tot, cnt = 0, 0
    for x in np.unique(src):
        dist[x] = 0
        q = deque([x])
        seen = [x]
        while q:
            u = q.popleft()
            du = dist[u] + 1
            for v in d_sorted[indptr[u]:indptr[u + 1]]:
                if dist[v] < 0:
                    dist[v] = du
                    tot += du
                    cnt += 1
                    seen.append(v)
                    q.append(v)
        for v in seen:
            dist[v] = -1
    return recip, assort, tot / cnt, cnt


def one_sample(args):
    path, seed = args
    src, dst = load(path)
    n = int(max(src.max(), dst.max())) + 1
    m = len(src)
    rng = np.random.default_rng(seed)
    arcset = set(map(tuple, np.stack([src, dst], axis=1)))
    done = 0
    while done < 10 * m:
        a, b = rng.integers(0, m, 2)
        if a == b:
            continue
        sa, da, sb, db = src[a], dst[a], src[b], dst[b]
        if sa == db or sb == da:
            continue
        if (sa, db) in arcset or (sb, da) in arcset:
            continue
        arcset.discard((sa, da))
        arcset.discard((sb, db))
        arcset.add((sa, db))
        arcset.add((sb, da))
        dst[a], dst[b] = db, da
        done += 1
    return metrics(src, dst, n)


def main():
    n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 96
    only = set(sys.argv[2:])  # optional subset; other rows kept from existing TSV
    rows = []
    try:
        old = pd.read_csv("null_table.tsv", sep="\t")
    except FileNotFoundError:
        old = None
    for name, (path, _) in NETWORKS.items():
        if only and name not in only:
            if old is not None and (old.network == name).any():
                rows.append(old[old.network == name].iloc[0].to_dict())
            continue
        src, dst = load(path)
        n = int(max(src.max(), dst.max())) + 1
        real = metrics(src, dst, n)
        with Pool(min(os.cpu_count(), 24)) as pool:
            null = np.array(pool.map(one_sample,
                                     [(path, 7000 + i) for i in range(n_samples)]))
        mu, sd = null.mean(axis=0), null.std(axis=0, ddof=1)
        row = {"network": name}
        for i, k in enumerate(["reciprocity", "assortativity", "avg_dist",
                               "reachable_pairs"]):
            row[k] = real[i]
            row[k + "_mu"] = mu[i]
            row[k + "_z"] = (real[i] - mu[i]) / sd[i] if sd[i] > 0 else np.nan
        rows.append(row)
        print(f"{name}: " + "  ".join(
            f"{k} {row[k]:.3f} (null {row[k+'_mu']:.3f}, z {row[k+'_z']:+.1f})"
            for k in ["reciprocity", "assortativity", "avg_dist"]))
    pd.DataFrame(rows).to_csv("null_table.tsv", sep="\t", index=False,
                              float_format="%.4f")
    print("wrote null_table.tsv")


if __name__ == "__main__":
    main()
