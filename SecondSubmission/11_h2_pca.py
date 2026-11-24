#!/usr/bin/env python3
"""H2: PCA of value-aware structural features; humanitarian axis validation.

Features per organisation (from graph/arcs_weighted.tsv, i.e. the same
disbursement graph as H1/H3) are purely structural/financial -- no sector
information enters the PCA, so the humanitarian dimension is a genuine
external validation, not a circularity:
  log10(1+x) of: in-degree, out-degree, in-txns, out-txns, in-USD, out-USD,
  mean in-txn size, mean out-txn size; funder ratio out/(in+out) by txns;
  HHI partner concentration on each side (0 for an inactive side).
PCA set: organisations with >= 10 transactions in total.

External validation: per-org humanitarian share from DAC sector codes
72/73/74 (share of an org's sector-coded transactions that are
humanitarian; hum_rows.parquet from 11a_humanitarian_flags.py, the same arc
rows); orgs with >= 5 coded transactions form the validation set.
Spearman correlation of each PC with the humanitarian share + Mann-Whitney
between humanitarian-dominant (share >= 0.5) and development-dominant
(share <= 0.1) organisations.

Outputs: h2_scores.tsv, h2_loadings.tex, fig_h2_pca.png.
"""
import numpy as np
import pandas as pd
from scipy import stats


arcs = pd.read_csv("graph/arcs_weighted.tsv", sep="\t")
nodes = pd.read_csv("graph/nodes.tsv", sep="\t", header=None,
                    names=["id", "ref"], quoting=3)
n = len(nodes)

g_in = arcs.groupby("d")
g_out = arcs.groupby("s")
F = pd.DataFrame(index=nodes.id)
F["in_deg"] = g_in.size()
F["out_deg"] = g_out.size()
F["in_txn"] = g_in["count"].sum()
F["out_txn"] = g_out["count"].sum()
F["in_usd"] = g_in.usd.apply(lambda s: s.clip(lower=0).sum())
F["out_usd"] = g_out.usd.apply(lambda s: s.clip(lower=0).sum())
F = F.fillna(0.0)
F["in_size"] = np.where(F.in_txn > 0, F.in_usd / F.in_txn, 0)
F["out_size"] = np.where(F.out_txn > 0, F.out_usd / F.out_txn, 0)
F["funder_ratio"] = F.out_txn / (F.in_txn + F.out_txn)


def hhi(group_col, w_col):
    w = arcs[[group_col, w_col]].rename(columns={group_col: "k", w_col: "w"})
    tot = w.groupby("k").w.sum()
    sq = w.assign(w2=w.w ** 2).groupby("k").w2.sum()
    return sq / tot ** 2


F["hhi_in"] = hhi("d", "count")
F["hhi_out"] = hhi("s", "count")
F = F.fillna(0.0)

LOGS = ["in_deg", "out_deg", "in_txn", "out_txn", "in_usd", "out_usd",
        "in_size", "out_size"]
for c in LOGS:
    F[c] = np.log10(1 + F[c])

sel = F[(F.in_txn.pow(0) * 0 + arcs.groupby("d")["count"].sum()
         .reindex(F.index).fillna(0)
         + arcs.groupby("s")["count"].sum().reindex(F.index).fillna(0)) >= 10]
sel = F.loc[sel.index]
print(f"orgs in PCA (>=10 txns): {len(sel):,} of {n:,}")

X = (sel - sel.mean()) / sel.std(ddof=0)
U, S, Vt = np.linalg.svd(X.to_numpy(), full_matrices=False)
var = S ** 2 / (S ** 2).sum()
scores = U * S
# orient PCs deterministically: largest-|loading| feature positive
for k in range(Vt.shape[0]):
    j = np.argmax(np.abs(Vt[k]))
    if Vt[k, j] < 0:
        Vt[k] *= -1
        scores[:, k] *= -1
print("explained variance:", np.round(var[:5], 3))
load = pd.DataFrame(Vt[:4].T, index=sel.columns,
                    columns=["PC1", "PC2", "PC3", "PC4"])
print(load.round(2).to_string())

# --- humanitarian share ---
hr = pd.read_parquet("hum_rows.parquet")  # from 11a_humanitarian_flags.py
ids = dict(zip(nodes.ref, nodes.id))
long = pd.concat([
    pd.DataFrame({"id": hr.prov.map(ids), "hum": hr.hum}),
    pd.DataFrame({"id": hr.recv.map(ids), "hum": hr.hum}),
]).dropna()
agg = long.groupby("id").hum.agg(["mean", "size"])
val = agg[agg["size"] >= 5]["mean"]
print(f"orgs with humanitarian share (>=5 coded txns): {len(val):,}")

sc = pd.DataFrame(scores[:, :4], index=sel.index,
                  columns=["PC1", "PC2", "PC3", "PC4"])
sc["hum_share"] = val
sc["ref"] = nodes.set_index("id").ref
sc.to_csv("h2_scores.tsv", sep="\t", float_format="%.4f")

v = sc.dropna(subset=["hum_share"])
print(f"validation orgs inside PCA set: {len(v):,}")
lines = []
for pc in ["PC1", "PC2", "PC3", "PC4"]:
    rho, p = stats.spearmanr(v[pc], v.hum_share)
    hum_d = v[v.hum_share >= 0.5][pc]
    dev_d = v[v.hum_share <= 0.1][pc]
    mw = stats.mannwhitneyu(hum_d, dev_d)
    auc = mw.statistic / (len(hum_d) * len(dev_d))
    lines.append((pc, rho, p, len(hum_d), len(dev_d), auc, mw.pvalue))
    print(f"{pc}: spearman rho={rho:+.3f} (p={p:.2e}); "
          f"hum(n={len(hum_d)}) vs dev(n={len(dev_d)}): AUC={auc:.3f} "
          f"(MW p={mw.pvalue:.2e})")

with open("h2_loadings.tex", "w") as f:
    f.write("\\begin{tabular}{lrrrr}\n\\toprule\nfeature & PC1 & PC2 & PC3 & PC4\\\\\n\\midrule\n")
    pretty = {"in_deg": "in-degree", "out_deg": "out-degree",
              "in_txn": "in-transactions", "out_txn": "out-transactions",
              "in_usd": "USD received", "out_usd": "USD disbursed",
              "in_size": "mean incoming txn size", "out_size": "mean outgoing txn size",
              "funder_ratio": "funder ratio", "hhi_in": "HHI (in)", "hhi_out": "HHI (out)"}
    for feat in sel.columns:
        r = load.loc[feat]
        f.write(f"{pretty[feat]} & {r.PC1:.2f} & {r.PC2:.2f} & {r.PC3:.2f} & {r.PC4:.2f}\\\\\n")
    f.write("\\midrule\nexplained variance & "
            + " & ".join(f"{x:.0%}".replace("%", "\\%") for x in var[:4])
            + "\\\\\n\\bottomrule\n\\end{tabular}\n")

# --- figure ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
INK, MUTED = "#333331", "#6f6e69"
cmap = LinearSegmentedColormap.from_list(
    "seqblue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab"])
fig, ax = plt.subplots(figsize=(8.6, 5.6), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
rest = sc[sc.hum_share.isna()]
ax.scatter(rest.PC1, rest.PC2, s=8, c="#d4d2cb", alpha=0.5, linewidths=0,
           zorder=1)
pts = ax.scatter(v.PC1, v.PC2, s=18, c=v.hum_share, cmap=cmap, vmin=0,
                 vmax=1, linewidths=0, alpha=0.9, zorder=2)
cb = fig.colorbar(pts, ax=ax, shrink=0.8, pad=0.02)
cb.set_label("humanitarian share (DAC 72/73/74)", color=INK)
cb.ax.tick_params(colors=MUTED)
ax.set_xlabel(f"PC1 ({var[0]:.0%} var):  implementer  ←→  funder",
              color=INK)
ax.set_ylabel(f"PC2 ({var[1]:.0%} var): scale of inflows", color=INK)
ax.set_title("PCA of value-aware structural features "
             "(grey: orgs without sector-coded transactions)",
             color=INK, fontsize=10)
ax.grid(True, color="#e8e7e2", lw=0.8, zorder=0)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
for s_ in ("left", "bottom"):
    ax.spines[s_].set_color("#d4d2cb")
ax.tick_params(colors=MUTED)
fig.tight_layout()
fig.savefig("fig_h2_pca.png", dpi=150)
print("wrote h2_scores.tsv, h2_loadings.tex, fig_h2_pca.png")
