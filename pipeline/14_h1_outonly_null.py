#!/usr/bin/env python3
"""H1 robustness: out-degree-only null for the outgoing harmonic centrality.

Each funder keeps its number of arcs (out-degree, hence d1, preserved) but
every arc's target is redrawn uniformly at random over all other nodes
(simple graph enforced). Unlike the double-edge-swap null of
08_h1_harmonic.py this destroys the in-degree sequence (receiver
popularity), so a funder gains "surplus" merely by having attached to
popular intermediaries -- the weaker claim mail2 warned about. Comparing
the two z-scores quantifies how much of each funder's surplus is
"funds popular hubs" vs genuine multi-hop wiring.

Everything is unweighted: distances are hop counts, the null rewires
unweighted arcs; money enters H1 only through the scale variable.

Adds columns z_outonly, h_null_mu_outonly, h_null_sigma_outonly to
h1_ranking.tsv. Usage: python3 14_h1_outonly_null.py [n_samples=960]
"""
import importlib.util
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location("h1", "08_h1_harmonic.py")
h1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h1)


def one_chain(args):
    seed, k, src, n, sources = args
    rng = np.random.default_rng(seed)
    m = len(src)
    out = []
    for _ in range(k):
        dst = rng.integers(0, n, m)
        arcset = set()
        for i in range(m):
            while dst[i] == src[i] or (src[i], dst[i]) in arcset:
                dst[i] = rng.integers(0, n)
            arcset.add((src[i], dst[i]))
        out.append(h1.harmonic(src, dst, n, sources)[sources])
    return np.array(out)


def main():
    n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 960
    arcs, n = h1.load_graph()
    src = arcs.s.to_numpy(np.int64)
    sources = np.unique(src)
    workers = min(os.cpu_count(), 24)
    per = -(-n_samples // workers)
    with Pool(workers) as pool:
        chunks = pool.map(one_chain,
                          [(5000 + i, per, src, n, sources)
                           for i in range(workers)])
    samples = np.concatenate(chunks)[:n_samples]
    mu = samples.mean(axis=0)
    sigma = samples.std(axis=0, ddof=1)

    f = pd.read_csv("h1_ranking.tsv", sep="\t")
    add = pd.DataFrame({"id": sources, "h_null_mu_outonly": mu,
                        "h_null_sigma_outonly": sigma})
    f = f.drop(columns=[c for c in f.columns if c.endswith("outonly")],
               errors="ignore").merge(add, on="id", how="left")
    f["z_outonly"] = np.where(f.h_null_sigma_outonly > 0,
                              (f.h - f.h_null_mu_outonly)
                              / f.h_null_sigma_outonly, np.nan)
    f.to_csv("h1_ranking.tsv", sep="\t", index=False, float_format="%.4f")

    g = f[(f.out_degree >= 5) & (f.usd >= 1e6)]
    from scipy import stats
    rho, _ = stats.spearmanr(g.z, g.z_outonly)
    tz = set(g.nlargest(50, "z").ref)
    tz2 = set(g.nlargest(50, "z_outonly").ref)
    print(f"samples: {len(samples)}; filtered funders: {len(g)}")
    print(f"Spearman(z_swap, z_outonly) on filtered set: {rho:.3f}")
    print(f"top-50 overlap between the two nulls: {len(tz & tz2)}")
    print(f"median |z|: swap {g.z.abs().median():.2f}, "
          f"out-only {g.z_outonly.abs().median():.2f}")
    for ref in ["US-EIN-941655673", "US-EIN-300108263", "GB-GOV-1",
                "GB-CHC-228248"]:
        r = f[f.ref == ref]
        if len(r):
            r = r.iloc[0]
            print(f"  {ref}: z_swap={r.z:+.2f}  z_outonly={r.z_outonly:+.2f}")


if __name__ == "__main__":
    main()
