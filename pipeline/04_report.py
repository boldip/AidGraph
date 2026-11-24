#!/usr/bin/env python3
"""Steps 5-8: distance distribution, unweighted + weighted invariants, report.

Every invariant is reported in three forms where meaningful:
  unweighted | count-weighted (transactions per arc) | USD-weighted (net value).

Reads graph/{arcs_weighted.tsv,nodes.tsv,nf-exact.txt,nf-hyperball.txt,aid.sccsizes,build_log.txt}
Writes report.md, fig_distance_distribution.png, fig_degree_distributions.png

Usage: python3 04_report.py
"""
import struct
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_nf(path):
    with open(path) as f:
        return [float(x) for x in f.read().split()]


def wpearson(x, y, w):
    """Weighted Pearson correlation."""
    x, y, w = np.asarray(x, float), np.asarray(y, float), np.asarray(w, float)
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    return cov / np.sqrt(np.average((x - mx) ** 2, weights=w)
                         * np.average((y - my) ** 2, weights=w))


def plfit(data, label, lines):
    import powerlaw
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = powerlaw.Fit(data, discrete=True, verbose=False)
        R, p = fit.distribution_compare("power_law", "lognormal",
                                        normalized_ratio=True)
    lines.append(
        f"| {label} | α = {fit.power_law.alpha:.2f} | x_min = {fit.power_law.xmin:.0f} "
        f"| vs lognormal: R = {R:.2f}, p = {p:.3f} "
        f"({'power law NOT favoured' if R < 0 else 'power law favoured' if p < .1 else 'inconclusive'}) |")
    return fit


def main():
    arcs = pd.read_csv("graph/arcs_weighted.tsv", sep="\t")
    nodes = pd.read_csv("graph/nodes.tsv", sep="\t", header=None,
                        names=["id", "ref"], quoting=3)
    n, m = len(nodes), len(arcs)
    total_pairs = n * (n - 1)
    W_cnt = arcs["count"].sum()
    W_usd = arcs.usd.sum()

    nf = read_nf("graph/nf-exact.txt")
    hb = read_nf("graph/nf-hyperball.txt")
    per_dist = [nf[t] - nf[t - 1] for t in range(1, len(nf))]
    reachable = nf[-1] - n
    unreachable = total_pairs - reachable
    assert abs(per_dist[0] - m) < 1e-6

    avg_dist = sum(t * c for t, c in enumerate(per_dist, 1)) / reachable
    target = n + 0.9 * reachable
    eff_diam = next(t for t in range(len(nf)) if nf[t] >= target)
    frac1 = per_dist[0] / reachable
    frac12 = (per_dist[0] + per_dist[1]) / reachable

    # --- degrees and strengths ---
    outdeg = arcs.groupby("s").size()
    indeg = arcs.groupby("d").size()
    out_cnt = arcs.groupby("s")["count"].sum()
    in_cnt = arcs.groupby("d")["count"].sum()
    out_usd = arcs.groupby("s")["usd"].sum()
    in_usd = arcs.groupby("d")["usd"].sum()
    n_src, n_dst = len(outdeg), len(indeg)
    n_both = n_src + n_dst - n  # appear on both sides... careful: n = |union|
    n_both = len(set(arcs.s) & set(arcs.d))

    # --- reciprocity ---
    key = arcs.s * n + arcs.d
    rkey = set(arcs.d * n + arcs.s)
    recip_arcs = key.isin(rkey)
    recip = recip_arcs.mean()
    rev = arcs.set_index(["d", "s"])  # lookup reverse arc weights
    idx = pd.MultiIndex.from_arrays([arcs.s, arcs.d])
    rev_cnt = rev["count"].reindex(idx).fillna(0).to_numpy()
    rev_usd = rev["usd"].reindex(idx).fillna(0).to_numpy()
    # Squartini et al. 2013: r = sum min(w_ij, w_ji) / sum w_ij  (negatives clipped)
    cnt_w = arcs["count"].to_numpy()
    usd_w = np.maximum(arcs.usd.to_numpy(), 0)
    recip_cnt = np.minimum(cnt_w, rev_cnt).sum() / cnt_w.sum()
    recip_usd = np.minimum(usd_w, np.maximum(rev_usd, 0)).sum() / usd_w.sum()

    # --- assortativity (out-degree of source vs in-degree of target, over arcs) ---
    xs = outdeg.reindex(arcs.s).to_numpy()
    ys = indeg.reindex(arcs.d).to_numpy()
    assort = np.corrcoef(xs, ys)[0, 1]
    xs_c = out_cnt.reindex(arcs.s).to_numpy()
    ys_c = in_cnt.reindex(arcs.d).to_numpy()
    assort_cnt = wpearson(xs_c, ys_c, cnt_w)
    pos = arcs.usd > 0
    assort_usd = wpearson(out_usd.reindex(arcs.s[pos]).to_numpy(),
                          in_usd.reindex(arcs.d[pos]).to_numpy(),
                          arcs.usd[pos].to_numpy())

    scc_sizes = []
    try:
        with open("graph/aid.sccsizes", "rb") as f:
            data = f.read()
            scc_sizes = sorted(struct.unpack(f">{len(data)//4}i", data),
                               reverse=True)
    except FileNotFoundError:
        pass

    # --- plots ---
    # undirected (symmetrized) distances, if 03 produced them
    try:
        nfs = read_nf("graph/nf-sym.txt")
        per_und = [(nfs[t] - nfs[t - 1]) / 2 for t in range(1, len(nfs))]
        reach_und = (nfs[-1] - n) / 2
    except FileNotFoundError:
        per_und = None

    if per_und:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=False)
        panes = [(axes[0], per_dist, reachable, "directed (ordered pairs)"),
                 (axes[1], per_und, reach_und, "undirected (unordered pairs)")]
    else:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        panes = [(ax, per_dist, reachable, "directed (ordered pairs)")]
    for ax, pd_, rc, ttl in panes:
        ax.bar(range(1, len(pd_) + 1), [c / rc for c in pd_], color="#2f6fb0")
        ax.set_xlabel("Shortest path length")
        ax.set_ylabel("Proportion of reachable pairs")
        ax.set_title(ttl, fontsize=10)
        ax.set_xticks(range(1, len(pd_) + 1))
    fig.suptitle("Distribution of shortest-path lengths (disbursement graph)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig("fig_distance_distribution.png", dpi=150)

    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    series = [(indeg, "in-degree"), (in_cnt, "in-strength (count)"),
              (in_usd[in_usd > 0], "in-strength (USD)"),
              (outdeg, "out-degree"), (out_cnt, "out-strength (count)"),
              (out_usd[out_usd > 0], "out-strength (USD)")]
    for ax, (deg, lbl) in zip(axes.flat, series):
        v = np.sort(deg.to_numpy())
        ccdf = 1 - np.arange(len(v)) / len(v)
        ax.loglog(v, ccdf, ".", ms=2, color="#2f6fb0")
        ax.set_xlabel(lbl)
        ax.set_ylabel("CCDF")
    fig.suptitle("Degree/strength CCDFs (log-log)")
    fig.tight_layout()
    fig.savefig("fig_degree_distributions.png", dpi=150)

    # --- power-law fits ---
    pl_lines = ["| distribution | exponent | x_min | Clauset LR test vs lognormal |",
                "|---|---|---|---|"]
    plfit(indeg.to_numpy(), "in-degree", pl_lines)
    plfit(outdeg.to_numpy(), "out-degree", pl_lines)
    plfit(in_cnt.to_numpy(), "in-strength (count)", pl_lines)
    plfit(out_cnt.to_numpy(), "out-strength (count)", pl_lines)

    build_log = open("graph/build_log.txt").read().strip()
    L = []
    A = L.append
    A("# The IATI disbursement graph: distances and structural invariants")
    A("")
    A("Directed graph: one node per organisation (IATI ref; provider imputed from "
      "the reporting org when absent, per the IATI standard), one arc per observed "
      "sender→receiver disbursement relation (transaction type 3). "
      "USD weights use fixed indicative FX rates.")
    A("")
    A("## Construction log")
    A("```")
    A(build_log)
    A("```")
    A("")
    A("## Invariants — unweighted / count-weighted / USD-weighted")
    A("")
    A("| invariant | unweighted | count-weighted | USD-weighted |")
    A("|---|---|---|---|")
    A(f"| nodes n | {n:,} | — | — |")
    A(f"| arcs m / total weight W | {m:,} | {W_cnt:,.0f} txns | {W_usd/1e9:,.1f} B USD |")
    A(f"| density m/n(n−1) | {m/total_pairs:.2e} | — | — |")
    A(f"| average degree / strength (out) | {m/n:.3f} | {W_cnt/n:.1f} | {W_usd/n/1e6:.2f} M USD |")
    A(f"| mean weight per arc | — | {W_cnt/m:.1f} | {W_usd/m/1e6:.2f} M USD |")
    A(f"| reciprocity | {recip:.4f} | {recip_cnt:.4f} | {recip_usd:.4f} |")
    A(f"| assortativity (src-out vs dst-in) | {assort:.3f} | {assort_cnt:.3f} | {assort_usd:.3f} |")
    A(f"| nodes ever source / ever target / both | {n_src:,} / {n_dst:,} / {n_both:,} | | |")
    if scc_sizes:
        A(f"| SCCs; largest | {len(scc_sizes):,}; {scc_sizes[0]:,} ({scc_sizes[0]/n:.2%}) | | |")
    A("")
    A("Weighted reciprocity is Squartini et al. (2013): Σ min(w_ij, w_ji) / Σ w_ij "
      "(negative net USD arcs clipped at 0). Assortativity is the Pearson "
      "correlation over arcs between source out-degree(-strength) and target "
      "in-degree(-strength); USD version restricted to positive-weight arcs.")
    A("")
    A("## Degree / strength distributions (Clauset et al. fits)")
    A("")
    L.extend(pl_lines)
    A("")
    A("## Distance distribution (exact, unweighted — hop counts)")
    A("")
    A("| distance | ordered pairs | % of reachable |")
    A("|---:|---:|---:|")
    for t, c in enumerate(per_dist, 1):
        if c:
            A(f"| {t} | {int(round(c)):,} | {c/reachable:.2%} |")
    A(f"| unreachable | {int(round(unreachable)):,} | ({unreachable/total_pairs:.2%} of all pairs) |")
    A("")
    A(f"- reachable ordered pairs: {int(round(reachable)):,} ({reachable/total_pairs:.3%} of all ordered pairs)")
    A(f"- average distance over reachable pairs: {avg_dist:.3f}; effective diameter (90%): {eff_diam}; max distance: {len(per_dist)}")
    A(f"- share of finite distances at 1: {frac1:.1%}; at ≤2: {frac12:.1%}")
    A(f"- HyperBall (log2m=12) cross-check: last NF value {hb[-1]:,.0f} vs exact {nf[-1]:,.0f} (rel. err. {abs(hb[-1]-nf[-1])/nf[-1]:.2%})")
    A("")
    A("### H1 feasibility readout")
    verdict = ("Finite distances are dominated by 1–2: harmonic ≈ d₁ + d₂/2 and the "
               "degree-preserving null would cancel most of it — H1 as advertised is weak "
               "on this graph." if frac12 > 0.9 else
               "A substantial share of finite distances exceeds 2, so harmonic centrality "
               "carries structural information beyond immediate attachment — the "
               "residual/null analysis of H1 is meaningful.")
    A(verdict)
    A("")
    A("## Comparison table skeleton (H3)")
    A("")
    A("Aid-graph row filled; comparison rows to be filled from the literature once "
      "candidate networks with comparable density/size are agreed.")
    A("")
    A("| network | n | m | density | avg deg | reciprocity | assortativity | α_in | α_out | avg dist | eff. diam |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    A(f"| IATI disbursements (unweighted) | {n:,} | {m:,} | {m/total_pairs:.1e} | {m/n:.2f} | {recip:.3f} | {assort:.2f} | see fits | see fits | {avg_dist:.2f} | {eff_diam} |")
    A("| world trade network | | | | | | | | | | |")
    A("| interbank network | | | | | | | | | | |")
    A("| airline network (directed) | | | | | | | | | | |")
    A("")
    A("![distance distribution](fig_distance_distribution.png)")
    A("![degree distributions](fig_degree_distributions.png)")

    with open("report.md", "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
