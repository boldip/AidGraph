"""Figures and tables for the round-3 revision of the paper (paper/ folder).

Writes
  paper/Figures/fig_distance_distribution_ggfree.png   Fig. 1 with and without GlobalGiving
  paper/Figures/fig_percolation_ggfree.png              Fig. 2 without GlobalGiving (copy of fig_ggfree_percolation.png)
  paper/Figures/fig_h1_z_scatter_v2.png                 Fig. 3 without the GlobalGiving outlier
  paper/h1_top50_ggfree.tex                             Table 2 recomputed without GlobalGiving
  paper/backbone_summary.tex                            backbone survival / ranking-stability table
  ggfree_distances_undirected.tsv                       undirected hop distribution, with and without GlobalGiving
  r4_numbers.md                                         numbers quoted in the revised text
"""
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path

from common import load, node_id, display_names, BASE
from paper_names import display

GG = "US-EIN-300108263"
arcs, nodes, h1, fs = load()
names = display_names(nodes, h1)
n = len(nodes)
gg = node_id(nodes, GG)
out = []

# ---------------------------------------------------------------- undirected distances
def undirected_hist(a, n_nodes):
    m = csr_matrix((np.ones(len(a)), (a.s.to_numpy(), a.d.to_numpy())), shape=(n_nodes, n_nodes))
    hist = np.zeros(64, dtype=np.int64)
    chunk = 2000
    for i in range(0, n_nodes, chunk):
        D = shortest_path(m, directed=False, unweighted=True, indices=np.arange(i, min(i + chunk, n_nodes)))
        fin = D[np.isfinite(D)].astype(np.int64)
        hist += np.bincount(fin, minlength=64)[:64]
    hist[0] = 0
    return hist // 2  # unordered pairs

ggfree = arcs[(arcs.s != gg) & (arcs.d != gg)].reset_index(drop=True)
keep = np.unique(np.concatenate([ggfree.s.to_numpy(), ggfree.d.to_numpy()]))
remap = {old: new for new, old in enumerate(keep)}
gg2 = pd.DataFrame({"s": ggfree.s.map(remap), "d": ggfree.d.map(remap)})
n2 = len(keep)

hu_full = undirected_hist(arcs, n)
hu_gg = undirected_hist(gg2, n2)
pairs_full = n * (n - 1) // 2
pairs_gg = n2 * (n2 - 1) // 2
und = pd.DataFrame({"distance": np.arange(1, 64), "pairs_full": hu_full[1:], "pairs_ggfree": hu_gg[1:]})
und = und[(und.pairs_full > 0) | (und.pairs_ggfree > 0)]
und["share_full"] = und.pairs_full / und.pairs_full.sum()
und["share_ggfree"] = und.pairs_ggfree / und.pairs_ggfree.sum()
und.to_csv("ggfree_distances_undirected.tsv", sep="\t", index=False)

def und_stats(h, pairs, label):
    reach = h[1:].sum()
    d = np.arange(len(h))
    avg = (h * d).sum() / reach
    out.append(f"- undirected {label}: {reach:,} connected unordered pairs = {reach / pairs:.2%} of {pairs:,}; "
               f"mean distance {avg:.2f}; share at distance 2 = {h[2] / reach:.1%}; at <=5 = {h[1:6].sum() / reach:.1%}")
und_stats(hu_full, pairs_full, "full")
und_stats(hu_gg, pairs_gg, "without GlobalGiving")
out.append(f"- undirected distance-2 pairs: {hu_full[2]:,} -> {hu_gg[2]:,} ({1 - hu_gg[2] / hu_full[2]:.1%} of the distance-2 pairs involve GlobalGiving)")

# ---------------------------------------------------------------- Fig. 1 counterpart
dd = pd.read_csv("ggfree_distances.tsv", sep="\t")
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#333331", "#6f6e69"
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, df, ttl in [(axes[0], dd, "directed (ordered pairs)"), (axes[1], und, "undirected (unordered pairs)")]:
    x = df.distance.to_numpy()
    ax.bar(x - 0.2, df.share_full, width=0.4, color=BLUE, label=f"IATI-K ({int(df.pairs_full.sum()):,} pairs)")
    ax.bar(x + 0.2, df.share_ggfree, width=0.4, color=ORANGE, label=f"without GlobalGiving ({int(df.pairs_ggfree.sum()):,} pairs)")
    ax.set_xlabel("Shortest path length")
    ax.set_ylabel("Proportion of reachable pairs")
    ax.set_title(ttl, fontsize=10)
    ax.set_xticks(x)
    ax.legend(fontsize=8, frameon=False)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
fig.tight_layout()
fig.savefig("paper/Figures/fig_distance_distribution_ggfree.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Fig. 2 counterpart
shutil.copy("fig_ggfree_percolation.png", "paper/Figures/fig_percolation_ggfree.png")

# ---------------------------------------------------------------- Fig. 3 without the outlier
g = h1.drop(columns=["usd"]).merge(fs[["ref", "usd_total"]].rename(columns={"usd_total": "usd"}), on="ref", how="left")
g = g[(g.out_degree >= 5) & (g.usd.fillna(0) >= 1e6)].dropna(subset=["z"]).copy()
g["rank_z"] = g.z.rank(ascending=False, method="first").astype(int)
assert len(g) > 200, len(g)  # 285 on the submitted graph, 282 on the rebuilt one
gz = g[g.ref != GG].copy()
gg_z = float(g.loc[g.ref == GG, "z"].iloc[0])
lx = np.log10(gz.usd)
b1, b0, r, p, _ = stats.linregress(lx, gz.z)
out.append(f"- Fig. 3 without GlobalGiving: n = {len(gz)}, OLS slope {b1:+.3f} per decade, R^2 = {r * r:.3f}, p = {p:.2f}")
lx_all = np.log10(g.usd)
b1a, b0a, ra, pa, _ = stats.linregress(lx_all, g.z)
out.append(f"- Fig. 3 with GlobalGiving (published): n = {len(g)}, slope {b1a:+.3f}, R^2 = {ra * ra:.3f}")

fig, ax = plt.subplots(figsize=(8.4, 5.2), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
ax.axhline(0, color="#d4d2cb", lw=1, zorder=1)
ax.scatter(gz.usd, gz.z, s=16, c=BLUE, alpha=0.6, linewidths=0, zorder=2)
xs = np.logspace(np.log10(gz.usd.min()), np.log10(gz.usd.max()), 50)
ax.plot(xs, b0 + b1 * np.log10(xs), color=MUTED, lw=2, zorder=1)
hi = gz.nlargest(6, "z")
ax.scatter(hi.usd, hi.z, s=52, c=ORANGE, edgecolors="#fcfcfb", linewidths=2, zorder=3)
SHORT = {"The William and Flora Hewlett Foundation": "Hewlett Foundation",
         "Aga Khan Foundation (United Kingdom)": "Aga Khan Foundation UK",
         "Mott MacDonald Limited": "Mott MacDonald"}
OFF = {"ODI Global": (-54, -3), "Gates Foundation": (8, -12), "Mott MacDonald": (8, 4),
       "Hewlett Foundation": (8, 4), "Aga Khan Foundation UK": (-96, -12), "CARE International UK": (8, -12)}
for _, rr in hi.iterrows():
    label = rr["name"] if isinstance(rr["name"], str) else rr.ref
    label = SHORT.get(label, label)[:32]
    ax.annotate(label, (rr.usd, rr.z), textcoords="offset points",
                xytext=OFF.get(label, (8, 2)), fontsize=7, color=INK)
for ref, lbl, off in [("GB-GOV-1", "FCDO", (8, -2)), ("XM-DAC-3-1", "Danida", (6, 6)), ("US-GOV-1", "USAID", (8, -10))]:
    rr = gz[gz.ref == ref].iloc[0]
    ax.scatter([rr.usd], [rr.z], s=40, c=MUTED, edgecolors="#fcfcfb", linewidths=2, zorder=3)
    ax.annotate(f"{lbl} (z = {rr.z:.2f})", (rr.usd, rr.z), textcoords="offset points", xytext=off, fontsize=7, color=MUTED)
ax.set_xscale("log")
ax.set_xlabel("Gross USD disbursed (scale, identified + unidentified)", color=INK)
ax.set_ylabel("z (degree-preserving null)", color=INK)
ax.set_title(f"Null-model z vs financial scale, GlobalGiving (z = −{abs(gg_z):.1f}) omitted "
             f"(OLS slope {b1:+.3f} per decade, R² = {r * r:.3f})", color=INK, fontsize=10)
ax.grid(True, which="major", color="#e8e7e2", lw=0.8, zorder=0)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
for s_ in ("left", "bottom"):
    ax.spines[s_].set_color("#d4d2cb")
ax.tick_params(colors=MUTED, which="both")
fig.tight_layout()
fig.savefig("paper/Figures/fig_h1_z_scatter_v2.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Table 2 without GlobalGiving
def tex(s):
    return str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")

old_rank = g.set_index("ref")["rank_z"].astype(int).to_dict()
t = pd.read_csv("ggfree_h1_ranking.tsv", sep="\t")
top = pd.read_csv("ggfree_h1_top50.tsv", sep="\t")
rows = ["\\begin{tabular}{rlrrrrr}", "\\toprule",
        "\\# & funder & out-deg & USD (M) & $h$ & $z$ & rank in full network\\\\", "\\midrule"]
for rr in top.itertuples():
    nm = rr.name if isinstance(rr.name, str) else rr.ref
    rows.append(f"{rr.rank_z} & {display(nm, rr.ref)} & {int(rr.out_degree)} & {rr.usd / 1e6:,.1f} & {rr.h:,.0f} & {rr.z:.2f} & {old_rank.get(rr.ref, '--')}\\\\")
rows += ["\\midrule"]
full = pd.read_csv("ggfree_h1_ranking.tsv", sep="\t")
full = full.merge(g[["ref", "usd"]], on="ref", how="inner")
full = full[(full.out_degree >= 5) & (full.usd >= 1e6)].sort_values("z", ascending=False).reset_index(drop=True)
full["rank_z"] = np.arange(1, len(full) + 1)
assert len(full) > 200, len(full)  # 284 on the submitted graph, 281 on the rebuilt one
for ref in ["US-GOV-1"]:
    rr = full[full.ref == ref].iloc[0]
    rows.append(f"{int(rr.rank_z)} & {display(rr['name'], ref)} & {int(rr.out_degree)} & {rr.usd / 1e6:,.1f} & {rr.h:,.0f} & {rr.z:.2f} & {old_rank.get(ref, '--')}\\\\")
rr = full.iloc[-1]
rows.append(f"{int(rr.rank_z)} & {display(rr['name'], rr.ref)} & {int(rr.out_degree)} & {rr.usd / 1e6:,.1f} & {rr.h:,.0f} & {rr.z:.2f} & {old_rank.get(rr.ref, '--')}\\\\")
rows += ["\\bottomrule", "\\end{tabular}"]
open("paper/h1_top50_ggfree.tex", "w").write("\n".join(rows) + "\n")
out.append(f"- GG-free lowest-scoring funder: {rr['name']} z {rr.z:.2f} (rank {int(rr.rank_z)} of {len(full)})")

# ---------------------------------------------------------------- backbone table
bs = pd.read_csv("backbone_summary.tsv", sep="\t").set_index("backbone")
# null-model columns for the two primary backbones, parsed from r2's backbone_results.md
import re as _re
zcorr = {}
for _m in _re.finditer(r"## Null-model z on (\S+)\n\n(\d+) funders pass.*?Spearman rho\(z\) = ([\d.]+).*?top-50 overlap with the published top 50: (\d+)", open("backbone_results.md").read(), _re.S):
    zcorr[_m.group(1)] = (f"{float(_m.group(3)):.2f}", _m.group(2), _m.group(4))
assert set(zcorr) == {"disparity_usd_a0.05", "noisecorr_usd_d1.64"}, zcorr
label = {"full": ("full network", "--", "--"),
         "disparity_usd_a0.05": ("disparity filter", "US\\$", "$\\alpha=0.05$"),
         "disparity_usd_a0.1": ("disparity filter", "US\\$", "$\\alpha=0.10$"),
         "disparity_usd_a0.2": ("disparity filter", "US\\$", "$\\alpha=0.20$"),
         "disparity_count_a0.05": ("disparity filter", "count", "$\\alpha=0.05$"),
         "disparity_count_a0.1": ("disparity filter", "count", "$\\alpha=0.10$"),
         "disparity_count_a0.2": ("disparity filter", "count", "$\\alpha=0.20$"),
         "noisecorr_usd_d1.28": ("noise-corrected", "US\\$", "$\\delta=1.28$"),
         "noisecorr_usd_d1.64": ("noise-corrected", "US\\$", "$\\delta=1.64$"),
         "noisecorr_usd_d2.33": ("noise-corrected", "US\\$", "$\\delta=2.33$"),
         "noisecorr_count_d1.28": ("noise-corrected", "count", "$\\delta=1.28$"),
         "noisecorr_count_d1.64": ("noise-corrected", "count", "$\\delta=1.64$"),
         "noisecorr_count_d2.33": ("noise-corrected", "count", "$\\delta=2.33$")}
rows = ["\\begin{tabular}{lllrrrrrrrrr}", "\\toprule",
        "backbone & weight & threshold & links kept & US\\$ kept & organisations & giant component & funders in H1 filter & $\\rho(h)$ & top-50 overlap & $\\rho(z)$ & top-50 overlap ($z$)\\\\",
        "\\midrule"]
for key, (meth, w, par) in label.items():
    r_ = bs.loc[key]
    rz, nz, oz = zcorr.get(key, ("--", "", "--"))
    rz_txt = rz if key == "full" else (f"{rz} ($n={nz}$)" if nz else rz)
    if key == "full":
        rz_txt, oz = "1.00", "50"
    rows.append(f"{meth} & {w} & {par} & {r_.arc_share:.1%} & {r_.usd_share:.1%} & {int(r_.n):,} & {r_.giant_wcc_share:.1%} & "
                f"{int(r_.funders_filtered_kept)} & {r_.rho_h_vs_full:.2f} & {int(r_.top50_h_overlap)} & {rz_txt} & {oz}\\\\".replace("%", "\\%"))
    if key in ("full", "disparity_usd_a0.2", "disparity_count_a0.2", "noisecorr_usd_d2.33"):
        rows.append("\\midrule")
rows += ["\\bottomrule", "\\end{tabular}"]
open("paper/backbone_summary.tex", "w").write("\n".join(rows) + "\n")

open("r4_numbers.md", "w").write("# Numbers for the revised text\n\n" + "\n".join(out) + "\n")
print("\n".join(out))
print("done r4")
