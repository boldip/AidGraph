#!/usr/bin/env python3
"""Reviewer 1, point 1.4: robustness to backboning.

Backbones of IATI-K (directed, weighted by net USD or by transaction count):
  * disparity filter (Serrano, Boguna & Vespignani, PNAS 2009), directed
    version: an arc survives if it is significant at level alpha with
    respect to EITHER its source's out-strength distribution OR its
    target's in-strength distribution. For an endpoint of degree 1 the test
    is undefined (p = 1, (1-p)^(k-1) = 1 > alpha), so such arcs survive
    only through the other endpoint.
  * noise-corrected backbone (Coscia & Neffke, ICDE 2017), their
    beta-binomial formulation; an arc survives if score > delta * sdev.
Arcs with non-positive net USD (186 corrections) cannot be weighted and are
excluded from the USD backbones.

For each backbone: invariants, harmonic centrality of funders and its rank
correlation with the full-graph ranking. For the two primary backbones
(disparity USD alpha=0.05, noise-corrected USD delta=1.64) also the full
null-model z ranking, compared with the published one.

Outputs: backbone_summary.tsv, backbone_results.md, backbone_<name>_arcs.tsv,
backbone_<name>_h1_ranking.tsv for the primary two.
Usage: python3 r2_backbone.py [n_null_samples=960]
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau
import common as C

n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 960
arcs, nodes, h1, fs = C.load()
n = int(max(arcs.s.max(), arcs.d.max())) + 1
names = C.display_names(nodes, h1)
ref_of = nodes.set_index("id").ref


def disparity(df, w, alpha):
    df = df[df[w] > 0]
    keep = np.zeros(len(df), bool)
    for side in ("s", "d"):
        g = df.groupby(side)[w]
        k = g.transform("size").to_numpy(); p = (df[w] / g.transform("sum")).to_numpy()
        keep |= ((1 - p) ** (k - 1) < alpha) & (k > 1)
    return df[keep]


def noise_corrected(df, w, delta):
    t = df[df[w] > 0].copy()
    t["nij"] = t[w].astype(float)
    t["ni."] = t.groupby("s").nij.transform("sum"); t["n.j"] = t.groupby("d").nij.transform("sum")
    N = t.nij.sum(); t["n.."] = N
    t["mean_prior"] = (t["ni."] * t["n.j"]) / N ** 2
    t["kappa"] = N / (t["ni."] * t["n.j"])
    t["score"] = (t.kappa * t.nij - 1) / (t.kappa * t.nij + 1)
    t["var_prior"] = (1 / N ** 2) * (t["ni."] * t["n.j"] * (N - t["ni."]) * (N - t["n.j"])) / (N ** 2 * (N - 1))
    t["alpha_prior"] = ((t.mean_prior ** 2) / t.var_prior) * (1 - t.mean_prior) - t.mean_prior
    t["beta_prior"] = (t.mean_prior / t.var_prior) * (1 - t.mean_prior ** 2) - (1 - t.mean_prior)
    t["alpha_post"] = t.alpha_prior + t.nij; t["beta_post"] = N - t.nij + t.beta_prior
    t["expected_pij"] = t.alpha_post / (t.alpha_post + t.beta_post)
    t["variance_nij"] = t.expected_pij * (1 - t.expected_pij) * N
    t["dterm"] = (1.0 / (t["ni."] * t["n.j"])) - (N * ((t["ni."] + t["n.j"]) / ((t["ni."] * t["n.j"]) ** 2)))
    t["variance_cij"] = t.variance_nij * (((2 * (t.kappa + (t.nij * t.dterm))) / ((t.kappa * t.nij + 1) ** 2)) ** 2)
    t["sdev_cij"] = np.sqrt(t.variance_cij.clip(lower=0))
    return t[t.score > delta * t.sdev_cij][df.columns]


backbones = {}
for w in ("usd", "count"):
    for a in (0.05, 0.1, 0.2):
        backbones[f"disparity_{w}_a{a}"] = disparity(arcs, w, a)
    for d in (1.28, 1.64, 2.33):
        backbones[f"noisecorr_{w}_d{d}"] = noise_corrected(arcs, w, d)
PRIMARY = ["disparity_usd_a0.05", "noisecorr_usd_d1.64"]

# full-graph harmonic for comparison
src = arcs.s.to_numpy(np.int64); dst = arcs.d.to_numpy(np.int64)
funders_full = np.unique(src); h_full = C.harmonic(src, dst, n, funders_full)
old = h1.merge(fs[["ref", "usd_total"]], on="ref", how="left")
filt_refs = set(old[(old.out_degree >= 5) & (old.usd_total.fillna(0) >= 1e6)].ref)
filt_ids = set(nodes[nodes.ref.isin(filt_refs)].id)
gg = C.node_id(nodes, C.GLOBALGIVING)

rows, md = [], ["# Backboning robustness (IATI-K)", "", f"Full graph: n = {n:,} nodes with arcs = {len(pd.concat([arcs.s, arcs.d]).unique()):,}, m = {len(arcs):,}.", ""]
inv_full, _ = C.invariants(arcs, "full"); rows.append({**inv_full, "backbone": "full", "arc_share": 1.0, "usd_share": 1.0,
                                                    "gg_arcs_kept": int((arcs.s == gg).sum()), "rho_h_vs_full": 1.0, "tau_h_vs_full": 1.0,
                                                    "funders_filtered_kept": len(filt_ids), "top50_h_overlap": 50})
for name, b in backbones.items():
    print(name, len(b), flush=True)
    inv, _ = C.invariants(b, name)
    bs = b.s.to_numpy(np.int64); bd = b.d.to_numpy(np.int64)
    fb = np.unique(bs); hb = C.harmonic(bs, bd, n, fb)
    common_f = np.array(sorted(set(fb) & filt_ids))
    rho = spearmanr(hb[common_f], h_full[common_f]).correlation if len(common_f) > 2 else np.nan
    tau = kendalltau(hb[common_f], h_full[common_f]).correlation if len(common_f) > 2 else np.nan
    top_full = set(common_f[np.argsort(-h_full[common_f])][:50]); top_b = set(common_f[np.argsort(-hb[common_f])][:50])
    rows.append({**inv, "backbone": name, "arc_share": len(b) / len(arcs), "usd_share": b.usd.clip(lower=0).sum() / arcs.usd.clip(lower=0).sum(),
                 "gg_arcs_kept": int((b.s == gg).sum()), "rho_h_vs_full": rho, "tau_h_vs_full": tau,
                 "funders_filtered_kept": len(common_f), "top50_h_overlap": len(top_full & top_b)})
    if name in PRIMARY:
        b.to_csv(f"backbone_{name}_arcs.tsv", sep="\t", index=False)
summ = pd.DataFrame(rows).drop(columns=["network"])
cols = ["backbone", "n", "m", "arc_share", "usd_share", "funders", "receivers", "in_degree_1_share", "giant_wcc_share", "largest_scc",
        "cyclic_arc_share", "reciprocity", "reachable_pairs", "reachable_pair_share", "avg_distance", "eff_diameter_90", "max_distance",
        "gg_arcs_kept", "funders_filtered_kept", "rho_h_vs_full", "tau_h_vs_full", "top50_h_overlap"]
summ = summ[cols]; summ.to_csv("backbone_summary.tsv", sep="\t", index=False, float_format="%.4f")
md += ["## What survives each backbone", "", summ[["backbone", "n", "m", "arc_share", "usd_share", "giant_wcc_share", "reachable_pairs", "avg_distance",
        "in_degree_1_share", "gg_arcs_kept", "funders_filtered_kept", "rho_h_vs_full", "top50_h_overlap"]].to_markdown(index=False, floatfmt=".3f"), "",
       "rho/tau: Spearman/Kendall between harmonic centrality on the backbone and on the full graph, over the activity-filtered funders present in the backbone; "
       "top50 overlap: of the top 50 by harmonic centrality among those funders.", ""]
print("\n".join(md), flush=True)

# --- null-model z on the two primary backbones ---
for name in PRIMARY:
    b = backbones[name].reset_index(drop=True)
    print(f"null model on {name}: {n_samples} samples", flush=True)
    f = C.null_z(b, n, n_samples)
    f = f.merge(nodes, on="id", how="left"); f["name"] = f.ref.map(names)
    f.sort_values("z", ascending=False).to_csv(f"backbone_{name}_h1_ranking.tsv", sep="\t", index=False, float_format="%.4f")
    tab, nfilt = C.h1_table(f.drop(columns=["ref", "name"]), nodes, fs, names)
    tab.head(50).to_csv(f"backbone_{name}_h1_top50.tsv", sep="\t", index=False, float_format="%.2f")
    o = old[old.ref.isin(filt_refs)].copy(); o["rank_old"] = o.z.rank(ascending=False, method="first").astype(int)
    cmp = tab.merge(o[["ref", "z", "rank_old"]], on="ref", suffixes=("", "_old"))
    rho = spearmanr(cmp.z, cmp.z_old).correlation; tau = kendalltau(cmp.z, cmp.z_old).correlation
    top_new = set(tab.head(50).ref); top_old = set(o.nsmallest(50, "rank_old").ref)
    md += [f"## Null-model z on {name}", "",
           f"{nfilt} funders pass the activity filter on this backbone ({len(filt_refs)} on the full graph); over the {len(cmp)} in common: Spearman rho(z) = {rho:.3f}, "
           f"Kendall tau = {tau:.3f}; top-50 overlap with the published top 50: {len(top_new & top_old)}.", "", "Top 15 (backbone rank, published rank):", ""]
    for r in cmp.sort_values("rank_z").head(15).itertuples():
        md.append(f"- {r.rank_z} ({r.rank_old}) {r.name}: z {r.z:.2f} (was {r.z_old:.2f}), out-degree {int(r.out_degree)}")
    md.append(f"- published top 10 now at: " + ", ".join(f"{names.get(x.ref, x.ref)} {int(cmp[cmp.ref==x.ref].rank_z.iloc[0]) if (cmp.ref==x.ref).any() else 'dropped'}" for x in o.nsmallest(10, "rank_old").itertuples()))
    md.append("")
open("backbone_results.md", "w").write("\n".join(md)); print("done r2")
