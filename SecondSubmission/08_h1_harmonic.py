#!/usr/bin/env python3
"""H1: outgoing harmonic centrality of funders vs financial scale.

- h_out(x) = sum over y reachable from x of 1/d(x,y), exact BFS (hop counts,
  unweighted, per the mail2 definition). Outgoing paths rank funders.
- Scale = gross USD disbursed (sum of positive arc values); transaction count
  kept as robustness column.
- Null model: degree-preserving randomisation (directed double-edge swaps,
  simple graph maintained, in- and out-degrees preserved exactly), so the
  d1 term of h is cancelled exactly and z-scores isolate multi-hop surplus.
  Parallel independent chains; burn-in 10m accepted swaps, thinning 2m.
- Outputs: h1_ranking.tsv (all funders), fig_h1_scatter.png, and a printed
  top-50 summary. z = (h - mu_null)/sigma_null; resid = OLS residual of
  h on log10(scale).

Usage: python3 08_h1_harmonic.py [n_samples=960]
"""
import json
import os
import sys
from collections import deque
from multiprocessing import Pool

import numpy as np
import pandas as pd


def load_graph():
    arcs = pd.read_csv("graph/arcs_weighted.tsv", sep="\t")
    n = int(max(arcs.s.max(), arcs.d.max())) + 1
    return arcs, n


def harmonic(src, dst, n, sources):
    """Exact outgoing harmonic centrality for the given source nodes."""
    order = np.argsort(src, kind="stable")
    s_sorted, d_sorted = src[order], dst[order]
    indptr = np.searchsorted(s_sorted, np.arange(n + 1))
    h = np.zeros(n)
    dist = np.full(n, -1, dtype=np.int32)
    for x in sources:
        dist[x] = 0
        q = deque([x])
        seen = [x]
        acc = 0.0
        while q:
            u = q.popleft()
            du = dist[u] + 1
            inv = 1.0 / du
            for v in d_sorted[indptr[u]:indptr[u + 1]]:
                if dist[v] < 0:
                    dist[v] = du
                    acc += inv
                    seen.append(v)
                    q.append(v)
        h[x] = acc
        for v in seen:
            dist[v] = -1
    return h


def swap_chain(args):
    """One independent MCMC chain: burn-in, then k samples of h_null."""
    seed, k, src0, dst0, n, sources, m_burn, m_thin = args
    rng = np.random.default_rng(seed)
    src, dst = src0.copy(), dst0.copy()
    arcset = set(map(tuple, np.stack([src, dst], axis=1)))
    m = len(src)

    def do_swaps(target):
        done = 0
        while done < target:
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

    do_swaps(m_burn)
    out = []
    for _ in range(k):
        do_swaps(m_thin)
        out.append(harmonic(src, dst, n, sources)[sources])
    return np.array(out)


def main():
    n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 960
    arcs, n = load_graph()
    src = arcs.s.to_numpy(np.int64)
    dst = arcs.d.to_numpy(np.int64)
    m = len(src)
    sources = np.unique(src)
    print(f"n={n}, m={m}, funders={len(sources)}, null samples={n_samples}")

    h_real = harmonic(src, dst, n, sources)

    workers = min(os.cpu_count(), 24)
    per = -(-n_samples // workers)
    jobs = [(1000 + i, per, src, dst, n, sources, 10 * m, 2 * m)
            for i in range(workers)]
    with Pool(workers) as pool:
        chunks = pool.map(swap_chain, jobs)
    samples = np.concatenate(chunks)[:n_samples]      # (n_samples, len(sources))
    mu = samples.mean(axis=0)
    sigma = samples.std(axis=0, ddof=1)
    print(f"collected {len(samples)} samples; median sigma {np.median(sigma):.3f}")

    scale_usd = arcs.assign(pos=arcs.usd.clip(lower=0)).groupby("s").pos.sum()
    scale_cnt = arcs.groupby("s")["count"].sum()
    outdeg = arcs.groupby("s").size()

    f = pd.DataFrame({
        "id": sources,
        "out_degree": outdeg.reindex(sources).to_numpy(),
        "txns": scale_cnt.reindex(sources).to_numpy(),
        "usd": scale_usd.reindex(sources).to_numpy(),
        "h": h_real[sources],
        "h_null_mu": mu,
        "h_null_sigma": sigma,
    })
    f["z"] = np.where(f.h_null_sigma > 0, (f.h - f.h_null_mu) / f.h_null_sigma,
                      np.nan)

    # OLS of h on log10(usd), funders with usd > 0
    fit = f[f.usd > 0]
    X = np.stack([np.ones(len(fit)), np.log10(fit.usd)], axis=1)
    beta, *_ = np.linalg.lstsq(X, fit.h.to_numpy(), rcond=None)
    f["resid"] = f.h - (beta[0] + beta[1] * np.log10(f.usd.where(f.usd > 0)))
    r2 = 1 - np.nansum(f.resid[f.usd > 0] ** 2) / np.sum(
        (fit.h - fit.h.mean()) ** 2)
    print(f"OLS h ~ log10(usd): slope {beta[1]:.2f}, R^2 {r2:.3f}")

    nodes = pd.read_csv("graph/nodes.tsv", sep="\t", header=None,
                        names=["id", "ref"], quoting=3)
    f = f.merge(nodes, on="id")
    try:
        names = {k.upper(): v for k, v in json.load(
            open("comparison_data/publisher_names.json")).items()}
        f["name"] = f.ref.map(names)
    except FileNotFoundError:
        f["name"] = None

    f["rank_z"] = f.z.rank(ascending=False)
    f["rank_usd"] = f.usd.rank(ascending=False)
    f["rank_resid"] = f.resid.rank(ascending=False)
    f.sort_values("z", ascending=False).to_csv("h1_ranking.tsv", sep="\t",
                                               index=False,
                                               float_format="%.4f")

    top_z = set(f.nlargest(50, "z").ref)
    top_usd = set(f.nlargest(50, "usd").ref)
    top_res = set(f.nlargest(50, "resid").ref)
    print(f"top-50 by z inside top-50 by USD scale: {len(top_z & top_usd)}")
    print(f"top-50 by z inside top-50 by OLS residual: {len(top_z & top_res)}")

    print("\n== top 20 by z ==")
    cols = ["ref", "name", "out_degree", "usd", "h", "h_null_mu", "z",
            "rank_usd"]
    print(f.nlargest(20, "z")[cols].to_string(index=False))

    # --- figure: h vs scale, top-10 z highlighted ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#333331", "#6f6e69"
    fig, ax = plt.subplots(figsize=(8.4, 5.2), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    pos = f[f.usd > 0]
    ax.scatter(pos.usd, pos.h, s=14, c=BLUE, alpha=0.55, linewidths=0,
               zorder=2)
    xs = np.logspace(np.log10(pos.usd.min()), np.log10(pos.usd.max()), 50)
    ax.plot(xs, beta[0] + beta[1] * np.log10(xs), color=MUTED, lw=2,
            zorder=1, label=None)
    hi = f.nlargest(10, "z")
    ax.scatter(hi.usd.clip(lower=pos.usd.min()), hi.h, s=46, c=ORANGE,
               edgecolors="#fcfcfb", linewidths=2, zorder=3)
    for _, r in hi.iterrows():
        label = r["name"] if isinstance(r["name"], str) else r.ref
        ax.annotate(label[:28],
                    (max(r.usd, pos.usd.min()), r.h),
                    textcoords="offset points", xytext=(7, 4), fontsize=7,
                    color=INK)
    ax.set_xscale("log")
    ax.set_xlabel("Gross USD disbursed (scale)", color=INK)
    ax.set_ylabel("Outgoing harmonic centrality", color=INK)
    ax.set_title("Structural importance vs financial scale "
                 "(orange: top 10 by null-model z)", color=INK, fontsize=11)
    ax.grid(True, which="major", color="#e8e7e2", lw=0.8, zorder=0)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    for s_ in ("left", "bottom"):
        ax.spines[s_].set_color("#d4d2cb")
    ax.tick_params(colors=MUTED)
    fig.tight_layout()
    fig.savefig("fig_h1_scatter.png", dpi=150)
    print("\nwrote h1_ranking.tsv, fig_h1_scatter.png")


if __name__ == "__main__":
    main()
